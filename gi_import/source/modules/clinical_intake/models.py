"""Clinical Intake domain models — chief complaint library and intake records."""

from __future__ import annotations

import json
import re

from app.core.base_model import BaseModel
from app.extensions import db

TERM_TYPE_SYNONYM = "synonym"
TERM_TYPE_ALIAS = "alias"
TERM_TYPE_ABBREVIATION = "abbreviation"

ALL_TERM_TYPES = (TERM_TYPE_SYNONYM, TERM_TYPE_ALIAS, TERM_TYPE_ABBREVIATION)

INTAKE_STATUS_DRAFT = "draft"
INTAKE_STATUS_CONFIRMED = "confirmed"
INTAKE_STATUS_MODIFIED = "modified"

ALL_INTAKE_STATUSES = (INTAKE_STATUS_DRAFT, INTAKE_STATUS_CONFIRMED, INTAKE_STATUS_MODIFIED)

PRIORITY_ROUTINE = "routine"
PRIORITY_URGENT = "urgent"
PRIORITY_EMERGENCY = "emergency"

ALL_PRIORITIES = (PRIORITY_ROUTINE, PRIORITY_URGENT, PRIORITY_EMERGENCY)


def normalize_text(value: str) -> str:
    text = (value or "").strip().lower()
    text = re.sub(r"\s+", " ", text)
    return text


class ChiefComplaintCategory(BaseModel):
    """Configurable complaint category with optional parent hierarchy."""

    __tablename__ = "chief_complaint_categories"

    code = db.Column(db.String(64), nullable=False, unique=True, index=True)
    name = db.Column(db.String(150), nullable=False)
    specialty_code = db.Column(db.String(64), nullable=True, index=True)
    parent_category_id = db.Column(
        db.Integer, db.ForeignKey("chief_complaint_categories.id"), nullable=True, index=True
    )
    sort_order = db.Column(db.Integer, nullable=False, default=0)

    parent = db.relationship("ChiefComplaintCategory", remote_side="ChiefComplaintCategory.id")


class ChiefComplaintEntry(BaseModel):
    """Normalized chief complaint entry in the library."""

    __tablename__ = "chief_complaint_entries"

    code = db.Column(db.String(80), nullable=False, unique=True, index=True)
    display_name = db.Column(db.String(200), nullable=False)
    normalized_name = db.Column(db.String(200), nullable=False, index=True)
    category_id = db.Column(db.Integer, db.ForeignKey("chief_complaint_categories.id"), nullable=False, index=True)
    parent_entry_id = db.Column(
        db.Integer, db.ForeignKey("chief_complaint_entries.id"), nullable=True, index=True
    )
    specialty_code = db.Column(db.String(64), nullable=True, index=True)
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    category = db.relationship("ChiefComplaintCategory", foreign_keys=[category_id])
    parent = db.relationship("ChiefComplaintEntry", remote_side="ChiefComplaintEntry.id")
    terms = db.relationship("ChiefComplaintTerm", back_populates="complaint", lazy="dynamic")


class ChiefComplaintTerm(BaseModel):
    """Synonym, alias, or abbreviation mapped to a normalized complaint."""

    __tablename__ = "chief_complaint_terms"

    complaint_id = db.Column(db.Integer, db.ForeignKey("chief_complaint_entries.id"), nullable=False, index=True)
    term_type = db.Column(db.String(20), nullable=False, default=TERM_TYPE_SYNONYM, index=True)
    term_text = db.Column(db.String(200), nullable=False, index=True)
    normalized_term = db.Column(db.String(200), nullable=False, index=True)

    complaint = db.relationship("ChiefComplaintEntry", back_populates="terms")


class ClinicalIntakeRecord(BaseModel):
    """Structured clinical intake for the start of an encounter."""

    __tablename__ = "clinical_intake_records"

    encounter_id = db.Column(db.Integer, db.ForeignKey("clinical_encounters.id"), nullable=False, index=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False, index=True)
    complaint_entry_id = db.Column(db.Integer, db.ForeignKey("chief_complaint_entries.id"), nullable=True, index=True)

    chief_complaint = db.Column(db.String(255), nullable=False)
    normalized_complaint = db.Column(db.String(255), nullable=False, index=True)
    complaint_category = db.Column(db.String(150), nullable=True)
    symptom_onset = db.Column(db.String(100), nullable=True)
    priority = db.Column(db.String(20), nullable=False, default=PRIORITY_ROUTINE)
    status = db.Column(db.String(20), nullable=False, default=INTAKE_STATUS_DRAFT, index=True)
    is_unknown_complaint = db.Column(db.Boolean, nullable=False, default=False)
    extension_payload_json = db.Column(db.Text, nullable=True)

    encounter = db.relationship("ClinicalEncounter", foreign_keys=[encounter_id])
    patient = db.relationship("Patient", foreign_keys=[patient_id])
    complaint_entry = db.relationship("ChiefComplaintEntry", foreign_keys=[complaint_entry_id])

    __table_args__ = (
        db.UniqueConstraint("encounter_id", name="uq_clinical_intake_encounter"),
    )

    @property
    def extension_payload(self) -> dict:
        if not self.extension_payload_json:
            return {}
        return json.loads(self.extension_payload_json)

    @extension_payload.setter
    def extension_payload(self, value: dict) -> None:
        self.extension_payload_json = json.dumps(value or {})
