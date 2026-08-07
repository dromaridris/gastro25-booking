"""Patient document upload and listing."""

import os
import uuid

from flask import current_app
from werkzeug.utils import secure_filename

from app.core.exceptions import NotFoundError, ValidationError
from app.engines import audit_engine, permission_engine
from app.extensions import db
from app.modules.patient_documents.models import PatientDocument
from app.modules.patients.models import Patient
from app.storage.local_backend import get_storage_backend

ALLOWED_TYPES = {"application/pdf", "image/jpeg", "image/png", "text/plain"}


def _require(user, code: str, target_id=None):
    permission_engine.require(user, code, audit_context={"target_type": "PatientDocument", "target_id": target_id})


def list_for_patient(acting_user, patient_id: int) -> list[PatientDocument]:
    _require(acting_user, "patient_document:view", patient_id)
    return (
        PatientDocument.query.filter_by(patient_id=patient_id, is_archived=False)
        .order_by(PatientDocument.created_at.desc())
        .all()
    )


def get_document(acting_user, doc_id: int) -> PatientDocument:
    _require(acting_user, "patient_document:view", doc_id)
    doc = PatientDocument.query.get(doc_id)
    if doc is None or doc.is_archived:
        raise NotFoundError(f"No document with id {doc_id}")
    return doc


def upload(acting_user, *, patient_id: int, title: str, file_obj, filename: str,
           content_type: str | None = None, category: str = "general",
           encounter_id: int | None = None, notes: str | None = None) -> PatientDocument:
    _require(acting_user, "patient_document:upload")
    patient = Patient.query.get(patient_id)
    if patient is None or patient.is_archived:
        raise NotFoundError(f"No patient with id {patient_id}")
    if not filename:
        raise ValidationError("File is required.")
    ct = content_type or "application/octet-stream"
    if ct not in ALLOWED_TYPES:
        raise ValidationError("Unsupported file type. Use PDF, JPEG, PNG, or plain text.")
    safe = secure_filename(filename)
    ext = os.path.splitext(safe)[1] or ""
    key = f"patient_docs/{patient_id}/{uuid.uuid4().hex}{ext}"
    storage = get_storage_backend(current_app.config)
    storage.save(key, file_obj)
    size = file_obj.tell() if hasattr(file_obj, "tell") else None
    doc = PatientDocument(
        patient_id=patient_id,
        encounter_id=encounter_id,
        title=title.strip() or safe,
        category=category,
        storage_key=key,
        content_type=ct,
        file_name=safe,
        file_size=size,
        notes=notes,
        created_by_id=acting_user.id,
    )
    db.session.add(doc)
    db.session.commit()
    audit_engine.log("patient_document.upload", user=acting_user, target_type="patient_document", target_id=doc.id)
    return doc
