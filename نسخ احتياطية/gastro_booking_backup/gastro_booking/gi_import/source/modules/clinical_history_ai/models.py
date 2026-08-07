"""Clinical History AI domain models."""

from __future__ import annotations

import json

from app.core.base_model import BaseModel, utcnow
from app.extensions import db

from .constants import (
    DRAFT_STATUS_DRAFT,
    QUESTION_STATUS_ACTIVE,
    SESSION_STATUS_QUESTIONING,
)


class GuidedHistoryQuestion(BaseModel):
    """Configurable history question definition."""

    __tablename__ = "guided_history_questions"

    question_id = db.Column(db.String(80), nullable=False, unique=True, index=True)
    question_text = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(64), nullable=False, index=True)
    clinical_purpose = db.Column(db.String(120), nullable=True)
    question_type = db.Column(db.String(32), nullable=False, default="boolean")
    answer_options_json = db.Column(db.Text, nullable=True)
    is_required = db.Column(db.Boolean, nullable=False, default=False)
    priority = db.Column(db.Integer, nullable=False, default=100)
    conditional_rules_json = db.Column(db.Text, nullable=True)
    knowledge_topic_key = db.Column(db.String(120), nullable=True)
    knowledge_stable_id = db.Column(db.String(120), nullable=True)
    version = db.Column(db.Integer, nullable=False, default=1)
    status = db.Column(db.String(20), nullable=False, default=QUESTION_STATUS_ACTIVE, index=True)
    specialty_code = db.Column(db.String(64), nullable=True, index=True)

    @property
    def answer_options(self) -> list[str]:
        if not self.answer_options_json:
            return []
        return json.loads(self.answer_options_json)

    @property
    def conditional_rules(self) -> dict:
        if not self.conditional_rules_json:
            return {}
        return json.loads(self.conditional_rules_json)


class GuidedHistoryQuestionRule(BaseModel):
    """Maps complaints to questions with ordering and activation rules."""

    __tablename__ = "guided_history_question_rules"

    complaint_code = db.Column(db.String(80), nullable=False, index=True)
    question_id = db.Column(db.String(80), nullable=False, index=True)
    sort_order = db.Column(db.Integer, nullable=False, default=100)
    activation_rules_json = db.Column(db.Text, nullable=True)
    specialty_code = db.Column(db.String(64), nullable=True, index=True)

    @property
    def activation_rules(self) -> dict:
        if not self.activation_rules_json:
            return {}
        return json.loads(self.activation_rules_json)


class GuidedHistorySession(BaseModel):
    """AI-guided history workflow session for an encounter."""

    __tablename__ = "guided_history_sessions"

    encounter_id = db.Column(db.Integer, db.ForeignKey("clinical_encounters.id"), nullable=False, index=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False, index=True)
    intake_record_id = db.Column(db.Integer, db.ForeignKey("clinical_intake_records.id"), nullable=True, index=True)

    chief_complaint = db.Column(db.String(255), nullable=True)
    normalized_complaint = db.Column(db.String(255), nullable=True, index=True)
    complaint_entry_code = db.Column(db.String(80), nullable=True, index=True)
    status = db.Column(db.String(32), nullable=False, default=SESSION_STATUS_QUESTIONING, index=True)
    ai_session_uuid = db.Column(db.String(36), nullable=True, index=True)
    presented_question_ids_json = db.Column(db.Text, nullable=True)

    encounter = db.relationship("ClinicalEncounter", foreign_keys=[encounter_id])
    patient = db.relationship("Patient", foreign_keys=[patient_id])
    answers = db.relationship("GuidedHistoryAnswer", back_populates="session", lazy="dynamic")
    drafts = db.relationship("GuidedHistoryDraft", back_populates="session", lazy="dynamic")

    __table_args__ = (
        db.UniqueConstraint("encounter_id", name="uq_guided_history_session_encounter"),
    )

    @property
    def presented_question_ids(self) -> list[str]:
        if not self.presented_question_ids_json:
            return []
        return json.loads(self.presented_question_ids_json)

    @presented_question_ids.setter
    def presented_question_ids(self, value: list[str]) -> None:
        self.presented_question_ids_json = json.dumps(value or [])


class GuidedHistoryAnswer(BaseModel):
    """Structured answer stored separately from generated narrative."""

    __tablename__ = "guided_history_answers"

    session_id = db.Column(db.Integer, db.ForeignKey("guided_history_sessions.id"), nullable=False, index=True)
    encounter_id = db.Column(db.Integer, db.ForeignKey("clinical_encounters.id"), nullable=False, index=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False, index=True)
    question_id = db.Column(db.String(80), nullable=False, index=True)
    response_value = db.Column(db.Text, nullable=False)
    response_display = db.Column(db.Text, nullable=True)
    answered_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    answered_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    version = db.Column(db.Integer, nullable=False, default=1)

    session = db.relationship("GuidedHistorySession", back_populates="answers")

    __table_args__ = (
        db.UniqueConstraint("session_id", "question_id", name="uq_guided_history_answer_session_question"),
    )


class GuidedHistoryDraft(BaseModel):
    """Generated clinical history draft awaiting physician review."""

    __tablename__ = "guided_history_drafts"

    session_id = db.Column(db.Integer, db.ForeignKey("guided_history_sessions.id"), nullable=False, index=True)
    status = db.Column(db.String(20), nullable=False, default=DRAFT_STATUS_DRAFT, index=True)
    sections_json = db.Column(db.Text, nullable=False)
    source_answer_ids_json = db.Column(db.Text, nullable=True)
    ai_session_uuid = db.Column(db.String(36), nullable=True, index=True)
    physician_edited_text = db.Column(db.Text, nullable=True)
    missing_information_json = db.Column(db.Text, nullable=True)
    structured_findings_json = db.Column(db.Text, nullable=True)
    learning_notes_json = db.Column(db.Text, nullable=True)

    session = db.relationship("GuidedHistorySession", back_populates="drafts")

    @property
    def sections(self) -> dict:
        return json.loads(self.sections_json or "{}")

    @sections.setter
    def sections(self, value: dict) -> None:
        self.sections_json = json.dumps(value or {})

    @property
    def source_answer_ids(self) -> list[int]:
        if not self.source_answer_ids_json:
            return []
        return json.loads(self.source_answer_ids_json)

    @source_answer_ids.setter
    def source_answer_ids(self, value: list[int]) -> None:
        self.source_answer_ids_json = json.dumps(value or [])

    @property
    def missing_information(self) -> list[str]:
        if not self.missing_information_json:
            return []
        return json.loads(self.missing_information_json)

    @missing_information.setter
    def missing_information(self, value: list[str]) -> None:
        self.missing_information_json = json.dumps(value or [])

    @property
    def structured_findings(self) -> list[dict]:
        if not self.structured_findings_json:
            return []
        return json.loads(self.structured_findings_json)

    @structured_findings.setter
    def structured_findings(self, value: list[dict]) -> None:
        self.structured_findings_json = json.dumps(value or [])

    @property
    def learning_notes(self) -> dict:
        if not self.learning_notes_json:
            return {}
        return json.loads(self.learning_notes_json)

    @learning_notes.setter
    def learning_notes(self, value: dict) -> None:
        self.learning_notes_json = json.dumps(value or {})
