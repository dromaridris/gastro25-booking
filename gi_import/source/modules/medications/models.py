"""Medications — formulary and encounter medication entries (Sprint 4B-MED)."""

from app.core.base_model import BaseModel, utcnow
from app.extensions import db

ENTRY_TYPE_HOME = "home_medication"
ENTRY_TYPE_PRESCRIPTION = "new_prescription"
ENTRY_TYPE_DISCONTINUED = "discontinued"

ALL_ENTRY_TYPES = (ENTRY_TYPE_HOME, ENTRY_TYPE_PRESCRIPTION, ENTRY_TYPE_DISCONTINUED)

STATUS_DRAFT = "draft"
STATUS_ACTIVE = "active"
STATUS_STOPPED = "stopped"
STATUS_REVIEWED = "reviewed"

TERMINAL_STATUSES = (STATUS_STOPPED, STATUS_REVIEWED)


class MedicationCatalogueItem(BaseModel):
    __tablename__ = "medication_catalogue_items"

    code = db.Column(db.String(50), nullable=False, unique=True, index=True)
    name = db.Column(db.String(150), nullable=False)
    generic_name = db.Column(db.String(150), nullable=True)
    category = db.Column(db.String(50), nullable=False, index=True)
    default_route = db.Column(db.String(30), nullable=True)
    default_form = db.Column(db.String(50), nullable=True)
    sort_order = db.Column(db.Integer, nullable=False, default=0)


class MedicationEntry(BaseModel):
    __tablename__ = "medication_entries"

    encounter_id = db.Column(db.Integer, db.ForeignKey("clinical_encounters.id"), nullable=False, index=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False, index=True)
    catalogue_item_id = db.Column(
        db.Integer, db.ForeignKey("medication_catalogue_items.id"), nullable=False, index=True
    )
    drug_code = db.Column(db.String(50), nullable=False, index=True)
    entry_type = db.Column(db.String(30), nullable=False, default=ENTRY_TYPE_HOME)
    status = db.Column(db.String(20), nullable=False, default=STATUS_DRAFT, index=True)
    dose_text = db.Column(db.String(100), nullable=True)
    route = db.Column(db.String(30), nullable=True)
    frequency_text = db.Column(db.String(100), nullable=True)
    indication = db.Column(db.Text, nullable=True)
    started_on = db.Column(db.Date, nullable=True)
    stopped_on = db.Column(db.Date, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    documented_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    documented_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    reviewed_at = db.Column(db.DateTime(timezone=True), nullable=True)
    reviewed_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    encounter = db.relationship("ClinicalEncounter", foreign_keys=[encounter_id])
    patient = db.relationship("Patient", foreign_keys=[patient_id])
    catalogue_item = db.relationship("MedicationCatalogueItem")
    documented_by = db.relationship("User", foreign_keys=[documented_by_id])
    reviewed_by = db.relationship("User", foreign_keys=[reviewed_by_id])
