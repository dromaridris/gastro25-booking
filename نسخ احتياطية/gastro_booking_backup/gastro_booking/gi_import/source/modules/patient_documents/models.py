"""Patient-attached documents (uploads)."""

from app.core.base_model import BaseModel
from app.extensions import db


class PatientDocument(BaseModel):
    __tablename__ = "patient_documents"

    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False, index=True)
    encounter_id = db.Column(db.Integer, db.ForeignKey("clinical_encounters.id"), nullable=True, index=True)
    title = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(50), nullable=False, default="general", index=True)
    storage_key = db.Column(db.String(255), nullable=False)
    content_type = db.Column(db.String(80), nullable=True)
    file_name = db.Column(db.String(255), nullable=True)
    file_size = db.Column(db.Integer, nullable=True)
    notes = db.Column(db.Text, nullable=True)

    patient = db.relationship("Patient", foreign_keys=[patient_id])
    encounter = db.relationship("ClinicalEncounter", foreign_keys=[encounter_id])
