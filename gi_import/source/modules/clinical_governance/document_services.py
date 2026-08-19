"""Controlled document management — Sprint 7D."""

from __future__ import annotations

from datetime import date

from app.core.base_model import utcnow
from app.core.exceptions import NotFoundError, ValidationError
from app.extensions import db
from app.engines import audit_engine, permission_engine
from app.modules.clinical_governance.constants import ALL_DOCUMENT_STATUSES, ALL_DOCUMENT_TYPES, DOC_ACTIVE, DOC_DRAFT
from app.modules.clinical_governance.models import ControlledDocument, DocumentAcknowledgement


def _require(user, permission: str) -> None:
    permission_engine.require(user, permission)


def list_documents(acting_user, *, status: str | None = None) -> list[ControlledDocument]:
    _require(acting_user, "governance:view")
    query = ControlledDocument.query.filter_by(is_archived=False)
    if status:
        query = query.filter_by(status=status)
    return query.order_by(ControlledDocument.title.asc()).all()


def create_document(
    acting_user,
    *,
    title: str,
    document_type: str,
    version: str = "1.0",
    content_summary: str | None = None,
    expiry_date: date | None = None,
) -> ControlledDocument:
    _require(acting_user, "governance:document_manage")
    if document_type not in ALL_DOCUMENT_TYPES:
        raise ValidationError(f"Invalid document type '{document_type}'.")
    doc = ControlledDocument(
        title=title.strip(),
        document_type=document_type,
        version=version,
        status=DOC_DRAFT,
        content_summary=content_summary,
        expiry_date=expiry_date,
        department_id=getattr(acting_user, "department_id", 1) or 1,
        created_by_id=acting_user.id,
    )
    db.session.add(doc)
    db.session.commit()
    return doc


def approve_document(acting_user, doc: ControlledDocument, approval_date: date | None = None) -> ControlledDocument:
    _require(acting_user, "governance:document_manage")
    doc.status = DOC_ACTIVE
    doc.approved_by_id = acting_user.id
    doc.approval_date = approval_date or date.today()
    audit_engine.log("governance.document_approved", user=acting_user, target_type="controlled_document", target_id=doc.id)
    db.session.commit()
    return doc


def create_new_version(acting_user, doc: ControlledDocument, *, version: str, content_summary: str | None = None) -> ControlledDocument:
    _require(acting_user, "governance:document_manage")
    doc.status = "superseded"
    new_doc = ControlledDocument(
        title=doc.title,
        document_type=doc.document_type,
        version=version,
        status=DOC_DRAFT,
        content_summary=content_summary or doc.content_summary,
        expiry_date=doc.expiry_date,
        supersedes_id=doc.id,
        department_id=doc.department_id,
        created_by_id=acting_user.id,
    )
    db.session.add(new_doc)
    db.session.commit()
    return new_doc


def acknowledge_document(acting_user, document_id: int) -> DocumentAcknowledgement:
    _require(acting_user, "governance:view")
    existing = DocumentAcknowledgement.query.filter_by(document_id=document_id, user_id=acting_user.id).first()
    if existing:
        return existing
    ack = DocumentAcknowledgement(
        document_id=document_id,
        user_id=acting_user.id,
        acknowledged_at=utcnow(),
        department_id=getattr(acting_user, "department_id", 1) or 1,
        created_by_id=acting_user.id,
    )
    db.session.add(ack)
    db.session.commit()
    return ack


def get_document(acting_user, doc_id: int) -> ControlledDocument:
    _require(acting_user, "governance:view")
    doc = ControlledDocument.query.filter_by(id=doc_id, is_archived=False).first()
    if doc is None:
        raise NotFoundError("Document not found.")
    return doc
