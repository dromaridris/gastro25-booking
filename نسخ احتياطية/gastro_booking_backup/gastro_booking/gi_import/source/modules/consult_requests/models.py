"""Consult request workflow."""

from app.core.base_model import BaseModel, utcnow
from app.extensions import db

STATUS_PENDING = "pending"
STATUS_ACCEPTED = "accepted"
STATUS_COMPLETED = "completed"
STATUS_REJECTED = "rejected"
STATUS_CANCELLED = "cancelled"


class ConsultRequest(BaseModel):
    __tablename__ = "consult_requests"

    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False, index=True)
    encounter_id = db.Column(db.Integer, db.ForeignKey("clinical_encounters.id"), nullable=True, index=True)
    requesting_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    specialty = db.Column(db.String(80), nullable=False, index=True)
    urgency = db.Column(db.String(20), nullable=False, default="routine", index=True)
    clinical_question = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), nullable=False, default=STATUS_PENDING, index=True)
    assigned_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    response_notes = db.Column(db.Text, nullable=True)
    responded_at = db.Column(db.DateTime(timezone=True), nullable=True)

    patient = db.relationship("Patient", foreign_keys=[patient_id])
    encounter = db.relationship("ClinicalEncounter", foreign_keys=[encounter_id])
    requesting_user = db.relationship("User", foreign_keys=[requesting_user_id])
    assigned_user = db.relationship("User", foreign_keys=[assigned_user_id])
