"""Workforce & Training Platform models — Sprint 7A."""

import json

from app.core.base_model import BaseModel, utcnow
from app.extensions import db
from app.modules.workforce.constants import ADJUST_TEACHING, VERIFY_DRAFT


class PortfolioEntry(BaseModel):
    """
    Auto-generated portfolio logbook entry referencing clinical activity by ID.
    Never stores duplicate clinical content — resolves details at read time.
    """

    __tablename__ = "portfolio_entries"

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    activity_type = db.Column(db.String(40), nullable=False, index=True)
    activity_subtype = db.Column(db.String(40), nullable=True, index=True)
    participation_role = db.Column(db.String(40), nullable=True, index=True)
    competency_category = db.Column(db.String(40), nullable=True, index=True)

    source_module = db.Column(db.String(40), nullable=False, index=True)
    source_type = db.Column(db.String(40), nullable=False)
    source_id = db.Column(db.Integer, nullable=False, index=True)

    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=True, index=True)
    activity_at = db.Column(db.DateTime(timezone=True), nullable=False, index=True)
    title = db.Column(db.String(255), nullable=False)
    context_json = db.Column(db.Text, nullable=True)

    verification_status = db.Column(db.String(30), nullable=False, default=VERIFY_DRAFT, index=True)
    supervisor_verified_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    supervisor_verified_at = db.Column(db.DateTime(timezone=True), nullable=True)
    department_verified_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    department_verified_at = db.Column(db.DateTime(timezone=True), nullable=True)
    locked_at = db.Column(db.DateTime(timezone=True), nullable=True)
    skill_code = db.Column(db.String(80), nullable=False, default="", index=True)

    user = db.relationship("User", foreign_keys=[user_id])
    patient = db.relationship("Patient", foreign_keys=[patient_id])
    supervisor_verified_by = db.relationship("User", foreign_keys=[supervisor_verified_by_id])
    department_verified_by = db.relationship("User", foreign_keys=[department_verified_by_id])

    __table_args__ = (
        db.UniqueConstraint(
            "user_id",
            "source_module",
            "source_type",
            "source_id",
            "activity_type",
            "participation_role",
            "skill_code",
            name="uq_portfolio_entry_source",
        ),
    )

    def context(self) -> dict:
        if not self.context_json:
            return {}
        try:
            return json.loads(self.context_json)
        except json.JSONDecodeError:
            return {}


class AttendanceAdjustment(BaseModel):
    """Manual attendance credit — teaching, meetings, leave, conferences. HoD only."""

    __tablename__ = "attendance_adjustments"

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    adjustment_date = db.Column(db.Date, nullable=False, index=True)
    adjustment_type = db.Column(db.String(30), nullable=False, default=ADJUST_TEACHING, index=True)
    hours = db.Column(db.Numeric(4, 2), nullable=False, default=8)
    notes = db.Column(db.Text, nullable=True)
    approved_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    user = db.relationship("User", foreign_keys=[user_id])
    approved_by = db.relationship("User", foreign_keys=[approved_by_id])


class CompetencyStandard(BaseModel):
    """Configurable procedural skill competency requirement."""

    __tablename__ = "competency_standards"

    code = db.Column(db.String(80), nullable=False, unique=True, index=True)
    name = db.Column(db.String(150), nullable=False)
    specialty = db.Column(db.String(40), nullable=False, index=True)
    required_count = db.Column(db.Integer, nullable=False, default=1)
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
