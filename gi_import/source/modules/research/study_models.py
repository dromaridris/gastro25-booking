"""Research study registry models — Sprint 6C."""

import json

from app.core.base_model import BaseModel, utcnow
from app.extensions import db
from app.modules.research.study_constants import STUDY_STATUS_DRAFT


class ResearchStudy(BaseModel):
    __tablename__ = "research_studies"

    study_code = db.Column(db.String(50), nullable=False, unique=True, index=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    registry_code = db.Column(db.String(50), nullable=False, index=True)
    principal_investigator_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    status = db.Column(db.String(20), nullable=False, default=STUDY_STATUS_DRAFT, index=True)
    start_date = db.Column(db.Date, nullable=True)
    end_date = db.Column(db.Date, nullable=True)
    ethics_approval_number = db.Column(db.String(80), nullable=True)
    version = db.Column(db.Integer, nullable=False, default=1)
    inclusion_criteria_json = db.Column(db.Text, nullable=True)
    exclusion_criteria_json = db.Column(db.Text, nullable=True)
    auto_enroll_enabled = db.Column(db.Boolean, nullable=False, default=False)
    updated_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    principal_investigator = db.relationship("User", foreign_keys=[principal_investigator_id])
    updated_by = db.relationship("User", foreign_keys=[updated_by_id])
    cases = db.relationship("ResearchCase", back_populates="study", lazy="dynamic")

    def inclusion_criteria(self) -> list:
        return _json_list(self.inclusion_criteria_json)

    def exclusion_criteria(self) -> list:
        return _json_list(self.exclusion_criteria_json)


class StudyMemberAssignment(BaseModel):
    __tablename__ = "study_member_assignments"

    study_id = db.Column(db.Integer, db.ForeignKey("research_studies.id"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    assignment_role = db.Column(db.String(30), nullable=False, index=True)

    study = db.relationship("ResearchStudy", foreign_keys=[study_id])
    user = db.relationship("User", foreign_keys=[user_id])

    __table_args__ = (
        db.UniqueConstraint("study_id", "user_id", "assignment_role", name="uq_study_member_assignment"),
    )


class ResearchCase(BaseModel):
    """Enrolled study case — references clinical entities by ID only."""

    __tablename__ = "research_cases"

    study_id = db.Column(db.Integer, db.ForeignKey("research_studies.id"), nullable=False, index=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False, index=True)
    encounter_id = db.Column(db.Integer, db.ForeignKey("clinical_encounters.id"), nullable=True, index=True)
    procedure_id = db.Column(db.Integer, db.ForeignKey("procedures.id"), nullable=True, index=True)
    registry_enrollment_id = db.Column(db.Integer, db.ForeignKey("registry_enrollments.id"), nullable=True)
    case_status = db.Column(db.String(20), nullable=False, default="enrolled", index=True)
    enrolled_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    enrolled_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    reviewer_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    completeness_pct = db.Column(db.Numeric(5, 2), nullable=False, default=0)
    notes = db.Column(db.Text, nullable=True)

    study = db.relationship("ResearchStudy", back_populates="cases", foreign_keys=[study_id])
    patient = db.relationship("Patient", foreign_keys=[patient_id])
    encounter = db.relationship("ClinicalEncounter", foreign_keys=[encounter_id])
    enrolled_by = db.relationship("User", foreign_keys=[enrolled_by_id])
    reviewer = db.relationship("User", foreign_keys=[reviewer_id])

    __table_args__ = (
        db.UniqueConstraint("study_id", "patient_id", name="uq_research_case_study_patient"),
    )


class ScreeningLogEntry(BaseModel):
    __tablename__ = "research_screening_log"

    study_id = db.Column(db.Integer, db.ForeignKey("research_studies.id"), nullable=False, index=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False, index=True)
    outcome = db.Column(db.String(20), nullable=False, index=True)
    reason = db.Column(db.Text, nullable=True)
    screened_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    screened_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    study = db.relationship("ResearchStudy", foreign_keys=[study_id])
    patient = db.relationship("Patient", foreign_keys=[patient_id])
    screened_by = db.relationship("User", foreign_keys=[screened_by_id])


class EnrollmentLogEntry(BaseModel):
    __tablename__ = "research_enrollment_log"

    study_id = db.Column(db.Integer, db.ForeignKey("research_studies.id"), nullable=False, index=True)
    case_id = db.Column(db.Integer, db.ForeignKey("research_cases.id"), nullable=True, index=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False, index=True)
    action = db.Column(db.String(30), nullable=False, index=True)
    details_json = db.Column(db.Text, nullable=True)
    logged_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    study = db.relationship("ResearchStudy", foreign_keys=[study_id])
    case = db.relationship("ResearchCase", foreign_keys=[case_id])
    patient = db.relationship("Patient", foreign_keys=[patient_id])
    user = db.relationship("User", foreign_keys=[user_id])


class ResearchExportSnapshot(BaseModel):
    """Immutable frozen export — never overwrites clinical data."""

    __tablename__ = "research_export_snapshots"

    study_id = db.Column(db.Integer, db.ForeignKey("research_studies.id"), nullable=False, index=True)
    snapshot_name = db.Column(db.String(120), nullable=False)
    export_format = db.Column(db.String(10), nullable=False, default="csv")
    filters_json = db.Column(db.Text, nullable=True)
    variable_codes_json = db.Column(db.Text, nullable=True)
    row_count = db.Column(db.Integer, nullable=False, default=0)
    data_json = db.Column(db.Text, nullable=False)
    exported_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    exported_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    is_frozen = db.Column(db.Boolean, nullable=False, default=True)

    study = db.relationship("ResearchStudy", foreign_keys=[study_id])
    exported_by = db.relationship("User", foreign_keys=[exported_by_id])


def _json_list(raw: str | None) -> list:
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, list) else []
    except json.JSONDecodeError:
        return []
