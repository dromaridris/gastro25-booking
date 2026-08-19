"""Clinical Assessment domain models."""

from __future__ import annotations

import json

from app.core.base_model import BaseModel
from app.extensions import db

from .constants import RUN_STATUS_GENERATED, STATUS_SUGGESTED


class DiagnosisRuleDefinition(BaseModel):
    """Configurable differential rule — specialty data, not hardcoded logic."""

    __tablename__ = "diagnosis_rule_definitions"

    complaint_code = db.Column(db.String(80), nullable=False, index=True)
    diagnosis_name = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(40), nullable=False, index=True)
    base_priority = db.Column(db.Integer, nullable=False, default=100)
    base_confidence = db.Column(db.Float, nullable=False, default=0.5)
    inclusion_reason = db.Column(db.Text, nullable=True)
    supporting_patterns_json = db.Column(db.Text, nullable=True)
    missing_patterns_json = db.Column(db.Text, nullable=True)
    contradicting_patterns_json = db.Column(db.Text, nullable=True)
    knowledge_topic_key = db.Column(db.String(120), nullable=True)
    knowledge_stable_id = db.Column(db.String(120), nullable=True)
    specialty_code = db.Column(db.String(64), nullable=True, index=True)
    version = db.Column(db.Integer, nullable=False, default=1)
    status = db.Column(db.String(20), nullable=False, default="active", index=True)

    @property
    def supporting_patterns(self) -> list[dict]:
        if not self.supporting_patterns_json:
            return []
        return json.loads(self.supporting_patterns_json)

    @property
    def missing_patterns(self) -> list[dict]:
        if not self.missing_patterns_json:
            return []
        return json.loads(self.missing_patterns_json)

    @property
    def contradicting_patterns(self) -> list[dict]:
        if not self.contradicting_patterns_json:
            return []
        return json.loads(self.contradicting_patterns_json)


class ClinicalAssessmentRun(BaseModel):
    """One differential assessment generation run."""

    __tablename__ = "clinical_assessment_runs"

    encounter_id = db.Column(db.Integer, db.ForeignKey("clinical_encounters.id"), nullable=False, index=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False, index=True)
    guided_history_session_id = db.Column(
        db.Integer, db.ForeignKey("guided_history_sessions.id"), nullable=True, index=True
    )
    ai_session_uuid = db.Column(db.String(36), nullable=True, index=True)
    provider_key = db.Column(db.String(32), nullable=True)
    model_name = db.Column(db.String(128), nullable=True)
    status = db.Column(db.String(20), nullable=False, default=RUN_STATUS_GENERATED, index=True)
    knowledge_sources_json = db.Column(db.Text, nullable=True)
    clinical_context_json = db.Column(db.Text, nullable=True)

    suggestions = db.relationship("DiagnosisSuggestion", back_populates="assessment_run", lazy="dynamic")

    @property
    def knowledge_sources(self) -> list[dict]:
        if not self.knowledge_sources_json:
            return []
        return json.loads(self.knowledge_sources_json)

    @knowledge_sources.setter
    def knowledge_sources(self, value: list[dict]) -> None:
        self.knowledge_sources_json = json.dumps(value or [])

    @property
    def clinical_context(self) -> dict:
        if not self.clinical_context_json:
            return {}
        return json.loads(self.clinical_context_json)

    @clinical_context.setter
    def clinical_context(self, value: dict) -> None:
        self.clinical_context_json = json.dumps(value or {})


class DiagnosisSuggestion(BaseModel):
    """AI-generated differential suggestion — immutable physician-review snapshot."""

    __tablename__ = "diagnosis_suggestions"

    assessment_run_id = db.Column(
        db.Integer, db.ForeignKey("clinical_assessment_runs.id"), nullable=False, index=True
    )
    encounter_id = db.Column(db.Integer, db.ForeignKey("clinical_encounters.id"), nullable=False, index=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False, index=True)

    diagnosis_name = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(40), nullable=False, index=True)
    priority_rank = db.Column(db.Integer, nullable=False, default=100)
    supporting_findings_json = db.Column(db.Text, nullable=True)
    missing_information_json = db.Column(db.Text, nullable=True)
    contradicting_findings_json = db.Column(db.Text, nullable=True)
    inclusion_reason = db.Column(db.Text, nullable=True)
    confidence_indicator = db.Column(db.String(20), nullable=False, default="medium")
    knowledge_references_json = db.Column(db.Text, nullable=True)
    clinical_findings_used_json = db.Column(db.Text, nullable=True)
    ai_session_uuid = db.Column(db.String(36), nullable=True, index=True)
    version = db.Column(db.Integer, nullable=False, default=1)
    status = db.Column(db.String(20), nullable=False, default=STATUS_SUGGESTED, index=True)

    assessment_run = db.relationship("ClinicalAssessmentRun", back_populates="suggestions")
    physician_decisions = db.relationship(
        "PhysicianDiagnosisDecision", back_populates="suggestion", lazy="dynamic"
    )

    @property
    def supporting_findings(self) -> list[str]:
        return json.loads(self.supporting_findings_json or "[]")

    @supporting_findings.setter
    def supporting_findings(self, value: list[str]) -> None:
        self.supporting_findings_json = json.dumps(value or [])

    @property
    def missing_information(self) -> list[str]:
        return json.loads(self.missing_information_json or "[]")

    @missing_information.setter
    def missing_information(self, value: list[str]) -> None:
        self.missing_information_json = json.dumps(value or [])

    @property
    def contradicting_findings(self) -> list[str]:
        return json.loads(self.contradicting_findings_json or "[]")

    @contradicting_findings.setter
    def contradicting_findings(self, value: list[str]) -> None:
        self.contradicting_findings_json = json.dumps(value or [])

    @property
    def knowledge_references(self) -> list[dict]:
        return json.loads(self.knowledge_references_json or "[]")

    @knowledge_references.setter
    def knowledge_references(self, value: list[dict]) -> None:
        self.knowledge_references_json = json.dumps(value or [])

    @property
    def clinical_findings_used(self) -> list[dict]:
        return json.loads(self.clinical_findings_used_json or "[]")

    @clinical_findings_used.setter
    def clinical_findings_used(self, value: list[dict]) -> None:
        self.clinical_findings_used_json = json.dumps(value or [])


class PhysicianDiagnosisDecision(BaseModel):
    """Physician decision stored separately from AI suggestions."""

    __tablename__ = "physician_diagnosis_decisions"

    encounter_id = db.Column(db.Integer, db.ForeignKey("clinical_encounters.id"), nullable=False, index=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False, index=True)
    assessment_run_id = db.Column(
        db.Integer, db.ForeignKey("clinical_assessment_runs.id"), nullable=True, index=True
    )
    suggestion_id = db.Column(db.Integer, db.ForeignKey("diagnosis_suggestions.id"), nullable=True, index=True)

    diagnosis_name = db.Column(db.String(200), nullable=False)
    original_suggestion_name = db.Column(db.String(200), nullable=True)
    physician_status = db.Column(db.String(20), nullable=False, index=True)
    physician_notes = db.Column(db.Text, nullable=True)
    modified_fields_json = db.Column(db.Text, nullable=True)
    version = db.Column(db.Integer, nullable=False, default=1)

    suggestion = db.relationship("DiagnosisSuggestion", back_populates="physician_decisions")

    @property
    def modified_fields(self) -> dict:
        if not self.modified_fields_json:
            return {}
        return json.loads(self.modified_fields_json)

    @modified_fields.setter
    def modified_fields(self, value: dict) -> None:
        self.modified_fields_json = json.dumps(value or {})
