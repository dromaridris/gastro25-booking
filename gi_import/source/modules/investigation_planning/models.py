"""Investigation Planning domain models."""

from __future__ import annotations

import json

from app.core.base_model import BaseModel
from app.extensions import db

from .constants import PLAN_STATUS_DRAFT, SUGGESTION_STATUS_SUGGESTED


class InvestigationLibraryEntry(BaseModel):
    """Configurable investigation library entry."""

    __tablename__ = "investigation_library_entries"

    investigation_id = db.Column(db.String(80), nullable=False, unique=True, index=True)
    name = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(40), nullable=False, index=True)
    catalogue_code = db.Column(db.String(80), nullable=True, index=True)
    indications_json = db.Column(db.Text, nullable=True)
    contraindications_json = db.Column(db.Text, nullable=True)
    related_diagnosis_concepts_json = db.Column(db.Text, nullable=True)
    knowledge_topic_key = db.Column(db.String(120), nullable=True)
    knowledge_stable_id = db.Column(db.String(120), nullable=True)
    version = db.Column(db.Integer, nullable=False, default=1)
    status = db.Column(db.String(20), nullable=False, default="active", index=True)
    specialty_code = db.Column(db.String(64), nullable=True, index=True)

    @property
    def indications(self) -> list[str]:
        return json.loads(self.indications_json or "[]")

    @property
    def related_diagnosis_concepts(self) -> list[str]:
        return json.loads(self.related_diagnosis_concepts_json or "[]")


class InvestigationRecommendationRule(BaseModel):
    """Maps clinical context to investigation recommendations."""

    __tablename__ = "investigation_recommendation_rules"

    complaint_code = db.Column(db.String(80), nullable=True, index=True)
    diagnosis_name = db.Column(db.String(200), nullable=True, index=True)
    investigation_id = db.Column(db.String(80), nullable=False, index=True)
    workup_group = db.Column(db.String(40), nullable=False, index=True)
    priority = db.Column(db.String(20), nullable=False, default="recommended")
    reason_template = db.Column(db.Text, nullable=True)
    related_diagnosis = db.Column(db.String(200), nullable=True)
    missing_info_addressed = db.Column(db.String(200), nullable=True)
    sort_order = db.Column(db.Integer, nullable=False, default=100)
    specialty_code = db.Column(db.String(64), nullable=True)


class InvestigationPlan(BaseModel):
    """Investigation plan draft for physician review."""

    __tablename__ = "investigation_plans"

    encounter_id = db.Column(db.Integer, db.ForeignKey("clinical_encounters.id"), nullable=False, index=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False, index=True)
    assessment_run_id = db.Column(
        db.Integer, db.ForeignKey("clinical_assessment_runs.id"), nullable=True, index=True
    )
    ai_session_uuid = db.Column(db.String(36), nullable=True, index=True)
    provider_key = db.Column(db.String(32), nullable=True)
    model_name = db.Column(db.String(128), nullable=True)
    status = db.Column(db.String(20), nullable=False, default=PLAN_STATUS_DRAFT, index=True)
    knowledge_sources_json = db.Column(db.Text, nullable=True)
    clinical_context_json = db.Column(db.Text, nullable=True)
    version = db.Column(db.Integer, nullable=False, default=1)

    suggestions = db.relationship("InvestigationSuggestion", back_populates="plan", lazy="dynamic")

    @property
    def knowledge_sources(self) -> list[dict]:
        return json.loads(self.knowledge_sources_json or "[]")

    @knowledge_sources.setter
    def knowledge_sources(self, value: list[dict]) -> None:
        self.knowledge_sources_json = json.dumps(value or [])

    @property
    def clinical_context(self) -> dict:
        return json.loads(self.clinical_context_json or "{}")

    @clinical_context.setter
    def clinical_context(self, value: dict) -> None:
        self.clinical_context_json = json.dumps(value or {})


class InvestigationSuggestion(BaseModel):
    """AI-generated investigation suggestion — immutable snapshot."""

    __tablename__ = "investigation_suggestions"

    plan_id = db.Column(db.Integer, db.ForeignKey("investigation_plans.id"), nullable=False, index=True)
    encounter_id = db.Column(db.Integer, db.ForeignKey("clinical_encounters.id"), nullable=False, index=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False, index=True)

    investigation_id = db.Column(db.String(80), nullable=False, index=True)
    investigation_name = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(40), nullable=False, index=True)
    priority = db.Column(db.String(20), nullable=False, index=True)
    workup_group = db.Column(db.String(40), nullable=False, index=True)
    reason = db.Column(db.Text, nullable=True)
    related_diagnosis = db.Column(db.String(200), nullable=True)
    clinical_purpose = db.Column(db.Text, nullable=True)
    missing_info_addressed = db.Column(db.String(200), nullable=True)
    knowledge_references_json = db.Column(db.Text, nullable=True)
    confidence_indicator = db.Column(db.String(20), nullable=False, default="medium")
    ai_session_uuid = db.Column(db.String(36), nullable=True, index=True)
    duplicate_skipped = db.Column(db.Boolean, nullable=False, default=False)
    status = db.Column(db.String(20), nullable=False, default=SUGGESTION_STATUS_SUGGESTED, index=True)
    version = db.Column(db.Integer, nullable=False, default=1)

    plan = db.relationship("InvestigationPlan", back_populates="suggestions")
    physician_decisions = db.relationship(
        "PhysicianInvestigationDecision", back_populates="suggestion", lazy="dynamic"
    )

    @property
    def knowledge_references(self) -> list[dict]:
        return json.loads(self.knowledge_references_json or "[]")

    @knowledge_references.setter
    def knowledge_references(self, value: list[dict]) -> None:
        self.knowledge_references_json = json.dumps(value or [])


class PhysicianInvestigationDecision(BaseModel):
    """Physician decision stored separately from AI suggestions."""

    __tablename__ = "physician_investigation_decisions"

    plan_id = db.Column(db.Integer, db.ForeignKey("investigation_plans.id"), nullable=True, index=True)
    suggestion_id = db.Column(db.Integer, db.ForeignKey("investigation_suggestions.id"), nullable=True, index=True)
    encounter_id = db.Column(db.Integer, db.ForeignKey("clinical_encounters.id"), nullable=False, index=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False, index=True)

    investigation_name = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(40), nullable=True)
    priority = db.Column(db.String(20), nullable=True)
    physician_status = db.Column(db.String(20), nullable=False, index=True)
    physician_reason = db.Column(db.Text, nullable=True)
    modified_fields_json = db.Column(db.Text, nullable=True)
    version = db.Column(db.Integer, nullable=False, default=1)

    suggestion = db.relationship("InvestigationSuggestion", back_populates="physician_decisions")

    @property
    def modified_fields(self) -> dict:
        return json.loads(self.modified_fields_json or "{}")

    @modified_fields.setter
    def modified_fields(self, value: dict) -> None:
        self.modified_fields_json = json.dumps(value or {})
