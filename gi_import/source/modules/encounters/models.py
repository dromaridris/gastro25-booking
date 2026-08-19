"""Clinical Encounter — minimal stub (Sprint 4A-LAB)."""

from app.core.base_model import BaseModel, utcnow
from app.extensions import db

ENCOUNTER_TYPE_OPD = "opd"
ENCOUNTER_TYPE_ADMISSION = "admission"
ENCOUNTER_TYPE_EMERGENCY = "emergency"
ENCOUNTER_TYPE_FOLLOW_UP = "follow_up"

ALL_ENCOUNTER_TYPES = (
    ENCOUNTER_TYPE_OPD,
    ENCOUNTER_TYPE_ADMISSION,
    ENCOUNTER_TYPE_EMERGENCY,
    ENCOUNTER_TYPE_FOLLOW_UP,
)

ENCOUNTER_STATUS_OPEN = "open"
ENCOUNTER_STATUS_CLOSED = "closed"

ALL_ENCOUNTER_STATUSES = (ENCOUNTER_STATUS_OPEN, ENCOUNTER_STATUS_CLOSED)


class ClinicalEncounter(BaseModel):
    __tablename__ = "clinical_encounters"

    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False, index=True)
    appointment_id = db.Column(db.Integer, db.ForeignKey("appointments.id"), nullable=True, index=True)
    encounter_type = db.Column(db.String(30), nullable=False, default=ENCOUNTER_TYPE_OPD)
    status = db.Column(db.String(20), nullable=False, default=ENCOUNTER_STATUS_OPEN, index=True)
    started_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    closed_at = db.Column(db.DateTime(timezone=True), nullable=True)
    summary = db.Column(db.String(255), nullable=True)

    patient = db.relationship("Patient", foreign_keys=[patient_id])
    appointment = db.relationship("Appointment", foreign_keys=[appointment_id])

    @property
    def is_open(self) -> bool:
        return self.status == ENCOUNTER_STATUS_OPEN and not self.is_archived
