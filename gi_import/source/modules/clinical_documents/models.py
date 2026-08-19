"""Consent templates, signed records, and clinical document metadata."""

from app.core.base_model import BaseModel, utcnow
from app.extensions import db

CONSENT_DRAFT = "draft"
CONSENT_SIGNED = "signed"
CONSENT_VOID = "void"


class ConsentTemplate(BaseModel):
    __tablename__ = "consent_templates"

    code = db.Column(db.String(50), nullable=False, unique=True, index=True)
    title = db.Column(db.String(200), nullable=False)
    procedure_type = db.Column(db.String(50), nullable=True, index=True)
    body_html = db.Column(db.Text, nullable=False)
    version = db.Column(db.Integer, nullable=False, default=1)
    is_active = db.Column(db.Boolean, nullable=False, default=True, index=True)


class ConsentRecord(BaseModel):
    __tablename__ = "consent_records"

    template_id = db.Column(db.Integer, db.ForeignKey("consent_templates.id"), nullable=False, index=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False, index=True)
    encounter_id = db.Column(db.Integer, db.ForeignKey("clinical_encounters.id"), nullable=True, index=True)
    procedure_id = db.Column(db.Integer, db.ForeignKey("procedures.id"), nullable=True, index=True)
    status = db.Column(db.String(20), nullable=False, default=CONSENT_DRAFT, index=True)
    signed_at = db.Column(db.DateTime(timezone=True), nullable=True)
    signed_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    witness_name = db.Column(db.String(120), nullable=True)
    rendered_html = db.Column(db.Text, nullable=True)

    template = db.relationship("ConsentTemplate", foreign_keys=[template_id])
    patient = db.relationship("Patient", foreign_keys=[patient_id])
    encounter = db.relationship("ClinicalEncounter", foreign_keys=[encounter_id])
    procedure = db.relationship("Procedure", foreign_keys=[procedure_id])
    signed_by = db.relationship("User", foreign_keys=[signed_by_user_id])
