"""Management Plan Assistant domain models."""

from __future__ import annotations

import json

from app.core.base_model import BaseModel
from app.extensions import db

from .constants import PLAN_STATUS_DRAFT, SUGGESTION_STATUS_SUGGESTED


class ManagementPlanRule(BaseModel):
    """Configurable management recommendation rule — specialty data, not hardcoded logic."""

    __tablename__ = "management_plan_rules"

    diagnosis_name = db.Column(db.String(200), nullable=False, index=True)
    complaint_code = db.Column(db.String(80), nullable=True, index=True)
    category = db.Column(db.String(40), nullable=False, index=True)
    description_template = db.Column(db.Text, nullable=False)
    clinical_indication = db.Column(db.Text, nullable=True)
    priority = db.Column(db.String(20), nullable=False, default="recommended")
    knowledge_topic_key = db.Column(db.String(120), nullable=True)
    knowledge_stable_id = db.Column(db.String(120), nullable=True)
    guideline_reference = db.Column(db.String(200), nullable=True)
    sort_order = db.Column(db.Integer, nullable=False, default=100)
    specialty_code = db.Column(db.String(64), nullable=True, index=True)
    version = db.Column(db.Integer, nullable=False, default=1)
    status = db.Column(db.String(20), nullable=False, default="active", index=True)


class ManagementPlan(BaseModel):
    """Management plan draft for physician review."""

    __tablename__ = "management_plans"

    encounter_id = db.Column(db.Integer, db.ForeignKey("clinical_encounters.id"), nullable=False, index=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False, index=True)
    assessment_run_id = db.Column(
        db.Integer, db.ForeignKey("clinical_assessment_runs.id"), nullable=True, index=True
    )
    interpretation_run_id = db.Column(
        db.Integer, db.ForeignKey("clinical_interpretation_runs.id"), nullable=True, index=True
    )
    ai_session_uuid = db.Column(db.String(36), nullable=True, index=True)
    provider_key = db.Column(db.String(32), nullable=True)
    model_name = db.Column(db.String(128), nullable=True)
    status = db.Column(db.String(20), nullable=False, default=PLAN_STATUS_DRAFT, index=True)
    working_diagnoses_json = db.Column(db.Text, nullable=True)
    knowledge_sources_json = db.Column(db.Text, nullable=True)
    clinical_context_json = db.Column(db.Text, nullable=True)
    version = db.Column(db.Integer, nullable=False, default=1)

    suggestions = db.relationship("ManagementSuggestion", back_populates="plan", lazy="dynamic")

    @property
    def working_diagnoses(self) -> list[str]:
        return json.loads(self.working_diagnoses_json or "[]")

    @working_diagnoses.setter
    def working_diagnoses(self, value: list[str]) -> None:
        self.working_diagnoses_json = json.dumps(value or [])

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


class ManagementSuggestion(BaseModel):
    """AI-generated management suggestion — immutable physician-review snapshot."""

    __tablename__ = "management_suggestions"

    plan_id = db.Column(db.Integer, db.ForeignKey("management_plans.id"), nullable=False, index=True)
    encounter_id = db.Column(db.Integer, db.ForeignKey("clinical_encounters.id"), nullable=False, index=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False, index=True)

    suggestion_key = db.Column(db.String(80), nullable=False, index=True)
    category = db.Column(db.String(40), nullable=False, index=True)
    description = db.Column(db.Text, nullable=False)
    clinical_indication = db.Column(db.Text, nullable=True)
    related_diagnosis = db.Column(db.String(200), nullable=True)
    supporting_evidence_json = db.Column(db.Text, nullable=True)
    knowledge_references_json = db.Column(db.Text, nullable=True)
    guideline_references_json = db.Column(db.Text, nullable=True)
    priority = db.Column(db.String(20), nullable=False, index=True)
    confidence_indicator = db.Column(db.String(20), nullable=False, default="medium")
    ai_session_uuid = db.Column(db.String(36), nullable=True, index=True)
    status = db.Column(db.String(20), nullable=False, default=SUGGESTION_STATUS_SUGGESTED, index=True)
    version = db.Column(db.Integer, nullable=False, default=1)

    plan = db.relationship("ManagementPlan", back_populates="suggestions")
    physician_decisions = db.relationship(
        "PhysicianManagementDecision", back_populates="suggestion", lazy="dynamic"
    )

    @property
    def supporting_evidence(self) -> list[str]:
        return json.loads(self.supporting_evidence_json or "[]")

    @supporting_evidence.setter
    def supporting_evidence(self, value: list[str]) -> None:
        self.supporting_evidence_json = json.dumps(value or [])

    @property
    def knowledge_references(self) -> list[dict]:
        return json.loads(self.knowledge_references_json or "[]")

    @knowledge_references.setter
    def knowledge_references(self, value: list[dict]) -> None:
        self.knowledge_references_json = json.dumps(value or [])

    @property
    def guideline_references(self) -> list[str]:
        return json.loads(self.guideline_references_json or "[]")

    @guideline_references.setter
    def guideline_references(self, value: list[str]) -> None:
        self.guideline_references_json = json.dumps(value or [])


class PhysicianManagementDecision(BaseModel):
    """Physician decision stored separately from AI management suggestions."""

    __tablename__ = "physician_management_decisions"

    plan_id = db.Column(db.Integer, db.ForeignKey("management_plans.id"), nullable=True, index=True)
    suggestion_id = db.Column(db.Integer, db.ForeignKey("management_suggestions.id"), nullable=True, index=True)
    encounter_id = db.Column(db.Integer, db.ForeignKey("clinical_encounters.id"), nullable=False, index=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False, index=True)

    category = db.Column(db.String(40), nullable=True)
    description = db.Column(db.Text, nullable=False)
    original_description = db.Column(db.Text, nullable=True)
    physician_status = db.Column(db.String(20), nullable=False, index=True)
    physician_notes = db.Column(db.Text, nullable=True)
    modified_fields_json = db.Column(db.Text, nullable=True)
    version = db.Column(db.Integer, nullable=False, default=1)

    suggestion = db.relationship("ManagementSuggestion", back_populates="physician_decisions")

    @property
    def modified_fields(self) -> dict:
        return json.loads(self.modified_fields_json or "{}")

    @modified_fields.setter
    def modified_fields(self, value: dict) -> None:
        self.modified_fields_json = json.dumps(value or {})
