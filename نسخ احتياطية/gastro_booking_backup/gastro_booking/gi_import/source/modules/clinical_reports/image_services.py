"""Clinical report image upload, compression, and payload sync."""

import uuid

from flask import current_app, has_request_context

from app.core.exceptions import NotFoundError, ValidationError
from app.engines import audit_engine
from app.extensions import db
from app.modules.clinical_reports.fields.payload import StructuredPayload
from app.modules.clinical_reports.image_config import ALLOWED_IMAGE_CONTENT_TYPES, max_images_for_template
from app.modules.clinical_reports.image_processing import compress_image
from app.modules.clinical_reports.models import ClinicalReportAttachment, ClinicalReportDocument
from app.modules.reports.models import Report
from app.storage.local_backend import get_storage_backend


def _active_attachments(document: ClinicalReportDocument) -> list[ClinicalReportAttachment]:
    return (
        ClinicalReportAttachment.query.filter_by(document_id=document.id, is_archived=False)
        .order_by(ClinicalReportAttachment.sequence_order.asc(), ClinicalReportAttachment.id.asc())
        .all()
    )


def _sync_images_payload(document: ClinicalReportDocument) -> None:
    sp = StructuredPayload(document.get_payload(), template_key=document.template_key)
    components = sp.components
    components["images"] = [
        {
            "attachment_id": attachment.id,
            "caption": "",
            "sequence_order": index,
            "printable": True,
            "internal_only": False,
        }
        for index, attachment in enumerate(_active_attachments(document))
    ]
    document.set_payload(sp.data)


def _file_url(backend, storage_key: str) -> str:
    if has_request_context():
        return backend.url_for(storage_key)
    return f"/files/{storage_key}"


def list_report_images(document: ClinicalReportDocument) -> list[dict]:
    backend = get_storage_backend(current_app.config)
    images = []
    for attachment in _active_attachments(document):
        images.append(
            {
                "id": attachment.id,
                "url": _file_url(backend, attachment.storage_key),
                "original_filename": attachment.original_filename or f"Image {attachment.sequence_order + 1}",
                "file_size_bytes": attachment.file_size_bytes,
                "sequence_order": attachment.sequence_order,
            }
        )
    return images


def upload_report_images(
    acting_user,
    report: Report,
    document: ClinicalReportDocument,
    files,
) -> list[ClinicalReportAttachment]:
    if not report.is_editable:
        raise ValidationError("Report is not editable.")

    if not files:
        raise ValidationError("No image file selected.")

    max_images = max_images_for_template(document.template_key)
    existing = _active_attachments(document)
    remaining = max_images - len(existing)
    if remaining <= 0:
        raise ValidationError(f"Maximum of {max_images} images reached for this report.")

    backend = get_storage_backend(current_app.config)
    saved: list[ClinicalReportAttachment] = []
    next_order = len(existing)

    for upload in files:
        if not upload or not getattr(upload, "filename", None):
            continue
        if len(saved) >= remaining:
            break

        content_type = (upload.content_type or "").split(";")[0].strip().lower()
        if content_type not in ALLOWED_IMAGE_CONTENT_TYPES:
            raise ValidationError(
                f"Unsupported image type for '{upload.filename}'. Use JPEG, PNG, or WebP."
            )

        raw_bytes = upload.read()
        if not raw_bytes:
            raise ValidationError(f"Empty file: {upload.filename}")

        compressed, normalized_type = compress_image(raw_bytes, content_type)
        compressed_bytes = compressed.read()
        storage_key = (
            f"clinical_reports/{document.id}/{uuid.uuid4().hex}.jpg"
        )
        compressed.seek(0)
        backend.save(storage_key, compressed)

        attachment = ClinicalReportAttachment(
            document_id=document.id,
            storage_key=storage_key,
            content_type=normalized_type,
            original_filename=upload.filename,
            file_size_bytes=len(compressed_bytes),
            sequence_order=next_order,
            department_id=document.department_id,
            created_by_id=getattr(acting_user, "id", None),
        )
        db.session.add(attachment)
        db.session.flush()
        saved.append(attachment)
        next_order += 1

    if not saved:
        raise ValidationError("No valid image files were uploaded.")

    _sync_images_payload(document)
    report.last_modified_by_id = getattr(acting_user, "id", None)
    db.session.commit()

    for attachment in saved:
        audit_engine.log(
            action="clinical_report.image_uploaded",
            user=acting_user,
            target_type="ClinicalReportAttachment",
            target_id=attachment.id,
            details={
                "report_id": report.id,
                "document_id": document.id,
                "storage_key": attachment.storage_key,
                "file_size_bytes": attachment.file_size_bytes,
            },
        )

    return saved


def delete_report_image(
    acting_user,
    report: Report,
    document: ClinicalReportDocument,
    attachment_id: int,
) -> None:
    if not report.is_editable:
        raise ValidationError("Report is not editable.")

    attachment = ClinicalReportAttachment.query.filter_by(
        id=attachment_id,
        document_id=document.id,
        is_archived=False,
    ).first()
    if attachment is None:
        raise NotFoundError("Image not found on this report.")

    backend = get_storage_backend(current_app.config)
    if backend.exists(attachment.storage_key):
        backend.delete(attachment.storage_key)

    attachment.archive(getattr(acting_user, "id", None), reason="user_deleted_report_image")
    db.session.flush()

    for index, row in enumerate(_active_attachments(document)):
        row.sequence_order = index

    _sync_images_payload(document)
    report.last_modified_by_id = getattr(acting_user, "id", None)
    db.session.commit()

    audit_engine.log(
        action="clinical_report.image_deleted",
        user=acting_user,
        target_type="ClinicalReportAttachment",
        target_id=attachment_id,
        details={"report_id": report.id, "document_id": document.id},
    )
