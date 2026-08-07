"""
Generic Endoscopy Reporting Engine — Sprint 3A.

Infrastructure only: one Report per ProcedureSession, reusable section
framework, lifecycle (draft / finalized / locked), and generic print
foundation. No procedure-specific report types, templates, AI, or image
annotation — those belong to later sprints.
"""

from app.core.base_model import BaseModel
from app.extensions import db

# --- Lifecycle ---
STATUS_DRAFT = "draft"
STATUS_FINALIZED = "finalized"
STATUS_LOCKED = "locked"

ALL_STATUSES = [STATUS_DRAFT, STATUS_FINALIZED, STATUS_LOCKED]

# --- Generic section keys (Sprint 3A feature 4) ---
SECTION_CLINICAL_INDICATION = "clinical_indication"
SECTION_PROCEDURE_DESCRIPTION = "procedure_description"
SECTION_FINDINGS = "findings"
SECTION_IMPRESSION = "impression"
SECTION_RECOMMENDATIONS = "recommendations"
SECTION_COMPLICATIONS = "complications"

ALL_SECTION_KEYS = [
    SECTION_CLINICAL_INDICATION,
    SECTION_PROCEDURE_DESCRIPTION,
    SECTION_FINDINGS,
    SECTION_IMPRESSION,
    SECTION_RECOMMENDATIONS,
    SECTION_COMPLICATIONS,
]

SECTION_LABELS = {
    SECTION_CLINICAL_INDICATION: "Clinical Indication",
    SECTION_PROCEDURE_DESCRIPTION: "Procedure Description",
    SECTION_FINDINGS: "Findings",
    SECTION_IMPRESSION: "Impression",
    SECTION_RECOMMENDATIONS: "Recommendations",
    SECTION_COMPLICATIONS: "Complications",
}


class ReportNumberCounter(db.Model):
    """Per-department report number sequence — mirrors MRNCounter pattern."""

    __tablename__ = "report_number_counters"

    id = db.Column(db.Integer, primary_key=True)
    department_id = db.Column(
        db.Integer, db.ForeignKey("departments.id"), nullable=False, unique=True
    )
    next_value = db.Column(db.Integer, nullable=False, default=1)


class Report(BaseModel):
    """
    Generic endoscopy report. One row per ProcedureSession (unique FK).
    Links explicitly to Patient, Appointment, Procedure, and Session.
    """

    __tablename__ = "reports"

    report_number = db.Column(db.String(30), nullable=False, unique=True, index=True)

    procedure_session_id = db.Column(
        db.Integer, db.ForeignKey("procedure_sessions.id"), nullable=False, unique=True, index=True
    )
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False, index=True)
    appointment_id = db.Column(
        db.Integer, db.ForeignKey("appointments.id"), nullable=False, index=True
    )
    procedure_id = db.Column(
        db.Integer, db.ForeignKey("procedures.id"), nullable=False, index=True
    )

    status = db.Column(db.String(20), nullable=False, default=STATUS_DRAFT, index=True)

    author_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    supervising_consultant_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    last_modified_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    finalized_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    finalized_at = db.Column(db.DateTime(timezone=True), nullable=True)
    locked_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    locked_at = db.Column(db.DateTime(timezone=True), nullable=True)

    # Header snapshot — populated at finalize for stable printing (feature 3).
    header_patient_name = db.Column(db.String(200), nullable=True)
    header_patient_mrn = db.Column(db.String(30), nullable=True)
    header_procedure_type = db.Column(db.String(120), nullable=True)
    header_procedure_date = db.Column(db.DateTime(timezone=True), nullable=True)
    header_room_name = db.Column(db.String(120), nullable=True)
    header_endoscopist_name = db.Column(db.String(200), nullable=True)
    header_team_summary = db.Column(db.Text, nullable=True)
    header_sedation_category = db.Column(db.String(30), nullable=True)

    procedure_session = db.relationship("ProcedureSession", foreign_keys=[procedure_session_id])
    patient = db.relationship("Patient", foreign_keys=[patient_id])
    appointment = db.relationship("Appointment", foreign_keys=[appointment_id])
    procedure = db.relationship("Procedure", foreign_keys=[procedure_id])
    author = db.relationship("User", foreign_keys=[author_id])
    supervising_consultant = db.relationship("User", foreign_keys=[supervising_consultant_id])
    last_modified_by = db.relationship("User", foreign_keys=[last_modified_by_id])
    finalized_by = db.relationship("User", foreign_keys=[finalized_by_id])
    locked_by = db.relationship("User", foreign_keys=[locked_by_id])
    sections = db.relationship(
        "ReportSection",
        back_populates="report",
        order_by="ReportSection.section_key.asc()",
    )

    @property
    def is_editable(self) -> bool:
        return self.status == STATUS_DRAFT

    def __repr__(self):
        return f"<Report {self.report_number} status={self.status}>"


class ReportSection(BaseModel):
    """One generic text section belonging to a report."""

    __tablename__ = "report_sections"
    __table_args__ = (
        db.UniqueConstraint("report_id", "section_key", name="uq_report_sections_report_section"),
    )

    report_id = db.Column(db.Integer, db.ForeignKey("reports.id"), nullable=False, index=True)
    section_key = db.Column(db.String(40), nullable=False, index=True)
    content = db.Column(db.Text, nullable=False, default="")

    report = db.relationship("Report", back_populates="sections")

    def __repr__(self):
        return f"<ReportSection report={self.report_id} key={self.section_key}>"
