"""
Structured clinical report storage — Sprint 3C.

One ClinicalReportDocument per frozen Sprint 3A Report when using structured
templates (ercp, future EUS, etc.). Does not modify reports/ models.
"""

import json

from app.core.base_model import BaseModel
from app.extensions import db

SCHEMA_VERSION = "2"

# Generic workflow states (platform); template configs use subsets/transitions.
WF_CONTEXT = "WF_CONTEXT"
WF_ACCESS = "WF_ACCESS"
WF_IMAGING = "WF_IMAGING"
WF_THERAPY = "WF_THERAPY"
WF_CLOSURE = "WF_CLOSURE"
WF_SYNTHESIS = "WF_SYNTHESIS"
WF_REVIEW = "WF_REVIEW"
WF_FINALIZE = "WF_FINALIZE"

ALL_WORKFLOW_STATES = [
    WF_CONTEXT,
    WF_ACCESS,
    WF_IMAGING,
    WF_THERAPY,
    WF_CLOSURE,
    WF_SYNTHESIS,
    WF_REVIEW,
    WF_FINALIZE,
]


class ClinicalReportDocument(BaseModel):
    """Structured payload + workflow state for a clinical report template."""

    __tablename__ = "clinical_report_documents"
    __table_args__ = (db.UniqueConstraint("report_id", name="uq_clinical_report_documents_report_id"),)

    report_id = db.Column(db.Integer, db.ForeignKey("reports.id"), nullable=False, index=True)
    template_key = db.Column(db.String(40), nullable=False, index=True)
    workflow_state = db.Column(db.String(40), nullable=False, default=WF_CONTEXT, index=True)
    schema_version = db.Column(db.String(10), nullable=False, default=SCHEMA_VERSION)
    payload_json = db.Column(db.Text, nullable=False, default="{}")
    impression_edited_manually = db.Column(db.Boolean, nullable=False, default=False)
    last_quick_fill_profile = db.Column(db.String(60), nullable=True)

    report = db.relationship("Report", foreign_keys=[report_id])
    timeline_events = db.relationship(
        "ClinicalReportTimelineEvent",
        back_populates="document",
        order_by="ClinicalReportTimelineEvent.sequence_order.asc()",
    )
    metrics = db.relationship("ClinicalReportMetric", back_populates="document")
    workflow_logs = db.relationship(
        "ClinicalReportWorkflowLog",
        back_populates="document",
        order_by="ClinicalReportWorkflowLog.created_at.asc()",
    )
    attachments = db.relationship(
        "ClinicalReportAttachment",
        back_populates="document",
        order_by="ClinicalReportAttachment.sequence_order.asc()",
    )

    def get_payload(self) -> dict:
        try:
            return json.loads(self.payload_json or "{}")
        except json.JSONDecodeError:
            return {}

    def set_payload(self, data: dict) -> None:
        self.payload_json = json.dumps(data or {}, ensure_ascii=False)


class ClinicalReportAttachment(BaseModel):
    """Binary image stored via StorageBackend; metadata referenced in payload.components.images."""

    __tablename__ = "clinical_report_attachments"

    document_id = db.Column(
        db.Integer, db.ForeignKey("clinical_report_documents.id"), nullable=False, index=True
    )
    storage_key = db.Column(db.String(255), nullable=False)
    content_type = db.Column(db.String(80), nullable=False, default="image/jpeg")
    original_filename = db.Column(db.String(255), nullable=True)
    file_size_bytes = db.Column(db.Integer, nullable=False, default=0)
    sequence_order = db.Column(db.Integer, nullable=False, default=0)

    document = db.relationship("ClinicalReportDocument", back_populates="attachments")


class ClinicalReportTimelineEvent(BaseModel):
    __tablename__ = "clinical_report_timeline_events"

    document_id = db.Column(
        db.Integer, db.ForeignKey("clinical_report_documents.id"), nullable=False, index=True
    )
    event_key = db.Column(db.String(60), nullable=False, index=True)
    occurred_at = db.Column(db.DateTime(timezone=True), nullable=True)
    source = db.Column(db.String(20), nullable=False, default="manual")
    sequence_order = db.Column(db.Integer, nullable=False, default=0)

    document = db.relationship("ClinicalReportDocument", back_populates="timeline_events")


class ClinicalReportMetric(BaseModel):
    __tablename__ = "clinical_report_metrics"
    __table_args__ = (
        db.UniqueConstraint("document_id", "metric_key", name="uq_clinical_report_metrics_doc_key"),
    )

    document_id = db.Column(
        db.Integer, db.ForeignKey("clinical_report_documents.id"), nullable=False, index=True
    )
    metric_key = db.Column(db.String(60), nullable=False)
    metric_value = db.Column(db.String(60), nullable=True)
    is_computed = db.Column(db.Boolean, nullable=False, default=True)
    override_reason = db.Column(db.String(255), nullable=True)

    document = db.relationship("ClinicalReportDocument", back_populates="metrics")


class ClinicalReportWorkflowLog(BaseModel):
    __tablename__ = "clinical_report_workflow_logs"

    document_id = db.Column(
        db.Integer, db.ForeignKey("clinical_report_documents.id"), nullable=False, index=True
    )
    from_state = db.Column(db.String(40), nullable=True)
    to_state = db.Column(db.String(40), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    document = db.relationship("ClinicalReportDocument", back_populates="workflow_logs")


class VocabularyTerm(BaseModel):
    """Knowledge Library MVP — configurable controlled vocabularies."""

    __tablename__ = "vocabulary_terms"
    __table_args__ = (
        db.UniqueConstraint("vocabulary_key", "code", name="uq_vocabulary_terms_key_code"),
    )

    vocabulary_key = db.Column(db.String(80), nullable=False, index=True)
    code = db.Column(db.String(80), nullable=False)
    display_label = db.Column(db.String(200), nullable=False)
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    active = db.Column(db.Boolean, nullable=False, default=True)

    def __repr__(self):
        return f"<VocabularyTerm {self.vocabulary_key}:{self.code}>"
