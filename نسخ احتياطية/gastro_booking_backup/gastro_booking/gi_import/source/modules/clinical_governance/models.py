"""Clinical Governance models — Sprint 7D. References clinical records by ID only."""

from app.core.base_model import BaseModel
from app.extensions import db


class ClinicalIncident(BaseModel):
    __tablename__ = "clinical_incidents"

    incident_date = db.Column(db.DateTime(timezone=True), nullable=False, index=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=True, index=True)
    encounter_id = db.Column(db.Integer, db.ForeignKey("clinical_encounters.id"), nullable=True, index=True)
    procedure_id = db.Column(db.Integer, db.ForeignKey("procedures.id"), nullable=True, index=True)
    is_anonymous = db.Column(db.Boolean, nullable=False, default=False)
    category = db.Column(db.String(40), nullable=False, index=True)
    severity = db.Column(db.String(20), nullable=False, index=True)
    description = db.Column(db.Text, nullable=False)
    root_cause = db.Column(db.Text, nullable=True)
    corrective_action = db.Column(db.Text, nullable=True)
    preventive_action = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), nullable=False, default="open", index=True)
    reviewer_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    reported_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    patient = db.relationship("Patient", foreign_keys=[patient_id])
    reviewer = db.relationship("User", foreign_keys=[reviewer_id])
    reported_by = db.relationship("User", foreign_keys=[reported_by_id])


class MortalityMorbidityCase(BaseModel):
    __tablename__ = "mm_cases"

    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=True, index=True)
    procedure_id = db.Column(db.Integer, db.ForeignKey("procedures.id"), nullable=True, index=True)
    presentation_date = db.Column(db.Date, nullable=True, index=True)
    case_summary = db.Column(db.Text, nullable=False)
    discussion_notes = db.Column(db.Text, nullable=True)
    lessons_learned = db.Column(db.Text, nullable=True)
    recommendations = db.Column(db.Text, nullable=True)
    follow_up_actions = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), nullable=False, default="scheduled", index=True)
    presenter_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    chair_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    patient = db.relationship("Patient", foreign_keys=[patient_id])
    presenter = db.relationship("User", foreign_keys=[presenter_id])
    chair = db.relationship("User", foreign_keys=[chair_id])


class AuditProject(BaseModel):
    __tablename__ = "audit_projects"

    title = db.Column(db.String(200), nullable=False)
    objective = db.Column(db.Text, nullable=False)
    methodology = db.Column(db.Text, nullable=True)
    inclusion_criteria = db.Column(db.Text, nullable=True)
    variables_json = db.Column(db.Text, nullable=True)
    timeline_start = db.Column(db.Date, nullable=True)
    timeline_end = db.Column(db.Date, nullable=True)
    status = db.Column(db.String(20), nullable=False, default="planned", index=True)
    investigator_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    research_study_id = db.Column(db.Integer, db.ForeignKey("research_studies.id"), nullable=True, index=True)
    findings_summary = db.Column(db.Text, nullable=True)

    investigator = db.relationship("User", foreign_keys=[investigator_id])


class ChecklistComplianceRecord(BaseModel):
    __tablename__ = "checklist_compliance_records"

    checklist_type = db.Column(db.String(30), nullable=False, index=True)
    reference_type = db.Column(db.String(40), nullable=False, index=True)
    reference_id = db.Column(db.Integer, nullable=False, index=True)
    completed_at = db.Column(db.DateTime(timezone=True), nullable=True)
    completed_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    is_complete = db.Column(db.Boolean, nullable=False, default=False)
    items_json = db.Column(db.Text, nullable=True)

    completed_by = db.relationship("User", foreign_keys=[completed_by_id])


class ControlledDocument(BaseModel):
    __tablename__ = "controlled_documents"

    title = db.Column(db.String(200), nullable=False, index=True)
    document_type = db.Column(db.String(20), nullable=False, index=True)
    version = db.Column(db.String(20), nullable=False, default="1.0")
    status = db.Column(db.String(20), nullable=False, default="draft", index=True)
    content_summary = db.Column(db.Text, nullable=True)
    approval_date = db.Column(db.Date, nullable=True)
    expiry_date = db.Column(db.Date, nullable=True, index=True)
    approved_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    supersedes_id = db.Column(db.Integer, db.ForeignKey("controlled_documents.id"), nullable=True)

    approved_by = db.relationship("User", foreign_keys=[approved_by_id])


class DocumentAcknowledgement(BaseModel):
    __tablename__ = "document_acknowledgements"

    document_id = db.Column(db.Integer, db.ForeignKey("controlled_documents.id"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    acknowledged_at = db.Column(db.DateTime(timezone=True), nullable=False, index=True)

    document = db.relationship("ControlledDocument", foreign_keys=[document_id])
    user = db.relationship("User", foreign_keys=[user_id])

    __table_args__ = (db.UniqueConstraint("document_id", "user_id", name="uq_document_ack"),)
