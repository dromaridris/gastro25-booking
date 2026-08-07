"""Investigations — laboratory, imaging, orders (Sprint 4A-LAB)."""

from decimal import Decimal

from app.core.base_model import BaseModel, utcnow
from app.extensions import db

# Catalogue
ITEM_TYPE_LAB = "lab_test"
ITEM_TYPE_IMAGING = "imaging_modality"

# Order
ORDER_KIND_LABORATORY = "laboratory"
ORDER_KIND_IMAGING = "imaging"

ORDER_STATUS_REQUESTED = "requested"
ORDER_STATUS_COLLECTED = "collected"
ORDER_STATUS_AVAILABLE = "available"
ORDER_STATUS_REVIEWED = "reviewed"
ORDER_STATUS_CANCELLED = "cancelled"

TERMINAL_ORDER_STATUSES = (ORDER_STATUS_REVIEWED, ORDER_STATUS_CANCELLED)

# Results
RESULT_STATUS_DRAFT = "draft"
RESULT_STATUS_AVAILABLE = "available"
RESULT_STATUS_REVIEWED = "reviewed"

VALUE_TYPE_NUMERIC = "numeric"
VALUE_TYPE_TEXT = "text"
VALUE_TYPE_CODED = "coded"

SOURCE_MANUAL = "manual"


class InvestigationCatalogueItem(BaseModel):
    __tablename__ = "investigation_catalogue_items"

    item_type = db.Column(db.String(30), nullable=False, index=True)
    code = db.Column(db.String(50), nullable=False, unique=True, index=True)
    name = db.Column(db.String(150), nullable=False)
    category = db.Column(db.String(50), nullable=False, index=True)
    default_unit = db.Column(db.String(30), nullable=True)
    reference_range_low = db.Column(db.Numeric(12, 4), nullable=True)
    reference_range_high = db.Column(db.Numeric(12, 4), nullable=True)
    reference_range_text = db.Column(db.String(100), nullable=True)
    value_type = db.Column(db.String(20), nullable=False, default=VALUE_TYPE_NUMERIC)
    sort_order = db.Column(db.Integer, nullable=False, default=0)


class InvestigationPanel(BaseModel):
    __tablename__ = "investigation_panels"

    code = db.Column(db.String(50), nullable=False, unique=True, index=True)
    name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)

    members = db.relationship(
        "InvestigationPanelMember",
        back_populates="panel",
        order_by="InvestigationPanelMember.sort_order",
    )


class InvestigationPanelMember(BaseModel):
    __tablename__ = "investigation_panel_members"

    panel_id = db.Column(db.Integer, db.ForeignKey("investigation_panels.id"), nullable=False, index=True)
    catalogue_item_id = db.Column(
        db.Integer, db.ForeignKey("investigation_catalogue_items.id"), nullable=False, index=True
    )
    sort_order = db.Column(db.Integer, nullable=False, default=0)

    panel = db.relationship("InvestigationPanel", back_populates="members")
    catalogue_item = db.relationship("InvestigationCatalogueItem")

    __table_args__ = (
        db.UniqueConstraint("panel_id", "catalogue_item_id", name="uq_panel_catalogue_item"),
    )


class InvestigationOrder(BaseModel):
    __tablename__ = "investigation_orders"

    encounter_id = db.Column(db.Integer, db.ForeignKey("clinical_encounters.id"), nullable=False, index=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False, index=True)
    order_kind = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(20), nullable=False, default=ORDER_STATUS_REQUESTED, index=True)
    panel_id = db.Column(db.Integer, db.ForeignKey("investigation_panels.id"), nullable=True, index=True)
    clinical_indication = db.Column(db.Text, nullable=True)
    priority = db.Column(db.String(20), nullable=False, default="routine")
    ordered_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    ordered_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    collected_at = db.Column(db.DateTime(timezone=True), nullable=True)
    reviewed_at = db.Column(db.DateTime(timezone=True), nullable=True)
    reviewed_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    encounter = db.relationship("ClinicalEncounter", foreign_keys=[encounter_id])
    patient = db.relationship("Patient", foreign_keys=[patient_id])
    panel = db.relationship("InvestigationPanel", foreign_keys=[panel_id])
    ordered_by = db.relationship("User", foreign_keys=[ordered_by_id])
    reviewed_by = db.relationship("User", foreign_keys=[reviewed_by_id])
    items = db.relationship("InvestigationOrderItem", back_populates="order")


class InvestigationOrderItem(BaseModel):
    __tablename__ = "investigation_order_items"

    order_id = db.Column(db.Integer, db.ForeignKey("investigation_orders.id"), nullable=False, index=True)
    catalogue_item_id = db.Column(
        db.Integer, db.ForeignKey("investigation_catalogue_items.id"), nullable=False, index=True
    )

    order = db.relationship("InvestigationOrder", back_populates="items")
    catalogue_item = db.relationship("InvestigationCatalogueItem")


class LabResultSet(BaseModel):
    __tablename__ = "lab_result_sets"

    encounter_id = db.Column(db.Integer, db.ForeignKey("clinical_encounters.id"), nullable=False, index=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False, index=True)
    order_id = db.Column(db.Integer, db.ForeignKey("investigation_orders.id"), nullable=True, index=True)
    status = db.Column(db.String(20), nullable=False, default=RESULT_STATUS_DRAFT, index=True)
    collected_at = db.Column(db.DateTime(timezone=True), nullable=True)
    resulted_at = db.Column(db.DateTime(timezone=True), nullable=True)
    source = db.Column(db.String(20), nullable=False, default=SOURCE_MANUAL)
    notes = db.Column(db.Text, nullable=True)
    reviewed_at = db.Column(db.DateTime(timezone=True), nullable=True)
    reviewed_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    encounter = db.relationship("ClinicalEncounter", foreign_keys=[encounter_id])
    patient = db.relationship("Patient", foreign_keys=[patient_id])
    order = db.relationship("InvestigationOrder", foreign_keys=[order_id])
    values = db.relationship("LabResultValue", back_populates="result_set", cascade="all, delete-orphan")


class LabResultValue(BaseModel):
    __tablename__ = "lab_result_values"

    result_set_id = db.Column(db.Integer, db.ForeignKey("lab_result_sets.id"), nullable=False, index=True)
    catalogue_item_id = db.Column(
        db.Integer, db.ForeignKey("investigation_catalogue_items.id"), nullable=False, index=True
    )
    test_code = db.Column(db.String(50), nullable=False, index=True)
    numeric_value = db.Column(db.Numeric(14, 4), nullable=True)
    text_value = db.Column(db.String(255), nullable=True)
    unit = db.Column(db.String(30), nullable=True)
    reference_low = db.Column(db.Numeric(12, 4), nullable=True)
    reference_high = db.Column(db.Numeric(12, 4), nullable=True)
    reference_text = db.Column(db.String(100), nullable=True)
    abnormal_flag = db.Column(db.String(20), nullable=False, default="unknown")

    result_set = db.relationship("LabResultSet", back_populates="values")
    catalogue_item = db.relationship("InvestigationCatalogueItem")

    __table_args__ = (
        db.UniqueConstraint("result_set_id", "catalogue_item_id", name="uq_lab_result_set_item"),
    )


class ImagingStudy(BaseModel):
    __tablename__ = "imaging_studies"

    encounter_id = db.Column(db.Integer, db.ForeignKey("clinical_encounters.id"), nullable=False, index=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False, index=True)
    order_id = db.Column(db.Integer, db.ForeignKey("investigation_orders.id"), nullable=True, index=True)
    catalogue_item_id = db.Column(
        db.Integer, db.ForeignKey("investigation_catalogue_items.id"), nullable=False, index=True
    )
    study_date = db.Column(db.Date, nullable=False)
    body_region = db.Column(db.String(100), nullable=True)
    findings_summary = db.Column(db.Text, nullable=True)
    impression = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), nullable=False, default=RESULT_STATUS_DRAFT, index=True)
    storage_key = db.Column(db.String(255), nullable=True)
    content_type = db.Column(db.String(80), nullable=True)
    file_name = db.Column(db.String(255), nullable=True)
    reviewed_at = db.Column(db.DateTime(timezone=True), nullable=True)
    reviewed_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    encounter = db.relationship("ClinicalEncounter", foreign_keys=[encounter_id])
    patient = db.relationship("Patient", foreign_keys=[patient_id])
    order = db.relationship("InvestigationOrder", foreign_keys=[order_id])
    catalogue_item = db.relationship("InvestigationCatalogueItem")
    reviewed_by = db.relationship("User", foreign_keys=[reviewed_by_id])


def compute_abnormal_flag(
    numeric_value: Decimal | None,
    reference_low: Decimal | None,
    reference_high: Decimal | None,
) -> str:
    if numeric_value is None:
        return "unknown"
    if reference_low is not None and numeric_value < reference_low:
        return "low"
    if reference_high is not None and numeric_value > reference_high:
        return "high"
    if reference_low is not None or reference_high is not None:
        return "normal"
    return "unknown"
