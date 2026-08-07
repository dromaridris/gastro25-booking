"""Patient Journey domain models."""

from __future__ import annotations

import json

from app.core.base_model import BaseModel
from app.extensions import db

from .constants import FOLLOWUP_STATUS_PLANNED, SUMMARY_STATUS_DRAFT


class FollowUpPlan(BaseModel):
    """Follow-up plan for patient journey continuation."""

    __tablename__ = "follow_up_plans"

    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False, index=True)
    encounter_id = db.Column(db.Integer, db.ForeignKey("clinical_encounters.id"), nullable=False, index=True)
    management_plan_id = db.Column(db.Integer, db.ForeignKey("management_plans.id"), nullable=True, index=True)

    related_condition = db.Column(db.String(200), nullable=True)
    responsible_physician_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    recommended_interval_days = db.Column(db.Integer, nullable=True)
    recommended_interval_text = db.Column(db.String(100), nullable=True)
    reason = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), nullable=False, default=FOLLOWUP_STATUS_PLANNED, index=True)
    knowledge_references_json = db.Column(db.Text, nullable=True)
    version = db.Column(db.Integer, nullable=False, default=1)

    events = db.relationship("FollowUpEvent", back_populates="plan", lazy="dynamic")

    @property
    def knowledge_references(self) -> list[dict]:
        return json.loads(self.knowledge_references_json or "[]")

    @knowledge_references.setter
    def knowledge_references(self, value: list[dict]) -> None:
        self.knowledge_references_json = json.dumps(value or [])


class FollowUpEvent(BaseModel):
    """Clinical update recorded during follow-up period."""

    __tablename__ = "follow_up_events"

    plan_id = db.Column(db.Integer, db.ForeignKey("follow_up_plans.id"), nullable=False, index=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False, index=True)
    encounter_id = db.Column(db.Integer, db.ForeignKey("clinical_encounters.id"), nullable=True, index=True)

    clinical_update = db.Column(db.Text, nullable=True)
    new_findings_json = db.Column(db.Text, nullable=True)
    symptoms_status = db.Column(db.String(100), nullable=True)
    investigation_updates_json = db.Column(db.Text, nullable=True)
    physician_assessment = db.Column(db.Text, nullable=True)
    next_action = db.Column(db.String(30), nullable=True, index=True)
    version = db.Column(db.Integer, nullable=False, default=1)

    plan = db.relationship("FollowUpPlan", back_populates="events")

    @property
    def new_findings(self) -> list[str]:
        return json.loads(self.new_findings_json or "[]")

    @new_findings.setter
    def new_findings(self, value: list[str]) -> None:
        self.new_findings_json = json.dumps(value or [])

    @property
    def investigation_updates(self) -> list[str]:
        return json.loads(self.investigation_updates_json or "[]")

    @investigation_updates.setter
    def investigation_updates(self, value: list[str]) -> None:
        self.investigation_updates_json = json.dumps(value or [])


class ClinicalOutcomeRecord(BaseModel):
    """Physician-entered or physician-confirmed clinical outcome."""

    __tablename__ = "clinical_outcome_records"

    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False, index=True)
    encounter_id = db.Column(db.Integer, db.ForeignKey("clinical_encounters.id"), nullable=False, index=True)
    follow_up_plan_id = db.Column(db.Integer, db.ForeignKey("follow_up_plans.id"), nullable=True, index=True)
    follow_up_event_id = db.Column(db.Integer, db.ForeignKey("follow_up_events.id"), nullable=True, index=True)

    outcome = db.Column(db.String(30), nullable=False, index=True)
    outcome_notes = db.Column(db.Text, nullable=True)
    physician_confirmed = db.Column(db.Boolean, nullable=False, default=True)
    recorded_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    version = db.Column(db.Integer, nullable=False, default=1)


class JourneySummaryDraft(BaseModel):
    """AI-generated follow-up summary draft — requires physician approval."""

    __tablename__ = "journey_summary_drafts"

    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False, index=True)
    encounter_id = db.Column(db.Integer, db.ForeignKey("clinical_encounters.id"), nullable=False, index=True)
    follow_up_plan_id = db.Column(db.Integer, db.ForeignKey("follow_up_plans.id"), nullable=True, index=True)

    ai_session_uuid = db.Column(db.String(36), nullable=True, index=True)
    provider_key = db.Column(db.String(32), nullable=True)
    model_name = db.Column(db.String(128), nullable=True)
    draft_text = db.Column(db.Text, nullable=True)
    approved_text = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), nullable=False, default=SUMMARY_STATUS_DRAFT, index=True)
    knowledge_references_json = db.Column(db.Text, nullable=True)
    missing_information_json = db.Column(db.Text, nullable=True)
    version = db.Column(db.Integer, nullable=False, default=1)

    @property
    def knowledge_references(self) -> list[dict]:
        return json.loads(self.knowledge_references_json or "[]")

    @knowledge_references.setter
    def knowledge_references(self, value: list[dict]) -> None:
        self.knowledge_references_json = json.dumps(value or [])

    @property
    def missing_information(self) -> list[str]:
        return json.loads(self.missing_information_json or "[]")

    @missing_information.setter
    def missing_information(self, value: list[str]) -> None:
        self.missing_information_json = json.dumps(value or [])


class FollowUpRecommendationRule(BaseModel):
    """Configurable follow-up interval recommendations."""

    __tablename__ = "follow_up_recommendation_rules"

    diagnosis_name = db.Column(db.String(200), nullable=True, index=True)
    related_condition = db.Column(db.String(200), nullable=True)
    interval_days = db.Column(db.Integer, nullable=True)
    interval_text = db.Column(db.String(100), nullable=True)
    reason_template = db.Column(db.Text, nullable=True)
    knowledge_topic_key = db.Column(db.String(120), nullable=True)
    knowledge_stable_id = db.Column(db.String(120), nullable=True)
    specialty_code = db.Column(db.String(64), nullable=True)
    sort_order = db.Column(db.Integer, nullable=False, default=100)
    status = db.Column(db.String(20), nullable=False, default="active", index=True)
    version = db.Column(db.Integer, nullable=False, default=1)
