"""Clinical History & Reasoning — Sprint 4C-HIST."""

import json

from app.core.base_model import BaseModel, utcnow
from app.extensions import db

SESSION_STATUS_DRAFT = "draft"
SESSION_STATUS_IN_PROGRESS = "in_progress"
SESSION_STATUS_COMPLETED = "completed"

ALL_SESSION_STATUSES = (SESSION_STATUS_DRAFT, SESSION_STATUS_IN_PROGRESS, SESSION_STATUS_COMPLETED)

SESSION_KIND_INITIAL = "initial_history"
SESSION_KIND_FOLLOW_UP = "follow_up"

ALL_SESSION_KINDS = (SESSION_KIND_INITIAL, SESSION_KIND_FOLLOW_UP)

ANSWER_TYPE_BOOLEAN = "boolean"
ANSWER_TYPE_CHOICE = "choice"
ANSWER_TYPE_TEXT = "text"

SUGGESTION_TIER_BASELINE = "baseline"
SUGGESTION_TIER_ADVANCED = "advanced"

NARRATIVE_SECTION_HPI = "hpi"
NARRATIVE_SECTION_NEGATIVES = "relevant_negatives"
NARRATIVE_SECTION_PMH = "past_medical_history"
NARRATIVE_SECTION_SURGICAL = "surgical_history"
NARRATIVE_SECTION_DRUGS = "drug_history"
NARRATIVE_SECTION_ALLERGY = "allergy_history"
NARRATIVE_SECTION_FAMILY = "family_history"
NARRATIVE_SECTION_SOCIAL = "social_history"

ALL_NARRATIVE_SECTIONS = (
    NARRATIVE_SECTION_HPI,
    NARRATIVE_SECTION_NEGATIVES,
    NARRATIVE_SECTION_PMH,
    NARRATIVE_SECTION_SURGICAL,
    NARRATIVE_SECTION_DRUGS,
    NARRATIVE_SECTION_ALLERGY,
    NARRATIVE_SECTION_FAMILY,
    NARRATIVE_SECTION_SOCIAL,
)


class ChiefComplaintDefinition(BaseModel):
    __tablename__ = "chief_complaint_definitions"

    code = db.Column(db.String(50), nullable=False, unique=True, index=True)
    name = db.Column(db.String(150), nullable=False)
    category = db.Column(db.String(50), nullable=False, default="gi")
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    knowledge_topic_key = db.Column(db.String(80), nullable=True)


class HistoryQuestionDefinition(BaseModel):
    __tablename__ = "history_question_definitions"

    code = db.Column(db.String(80), nullable=False, unique=True, index=True)
    prompt_text = db.Column(db.Text, nullable=False)
    section = db.Column(db.String(40), nullable=False, index=True)
    answer_type = db.Column(db.String(20), nullable=False, default=ANSWER_TYPE_BOOLEAN)
    choices_json = db.Column(db.Text, nullable=True)
    is_exclusion_question = db.Column(db.Boolean, nullable=False, default=False)
    help_text = db.Column(db.Text, nullable=True)
    knowledge_topic_key = db.Column(db.String(80), nullable=True)

    @property
    def choices(self) -> list[str]:
        if not self.choices_json:
            return []
        return json.loads(self.choices_json)


class ComplaintQuestionRule(BaseModel):
    __tablename__ = "complaint_question_rules"

    complaint_code = db.Column(db.String(50), nullable=False, index=True)
    question_code = db.Column(db.String(80), nullable=False, index=True)
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    parent_question_code = db.Column(db.String(80), nullable=True)
    parent_answer_required = db.Column(db.String(100), nullable=True)
    activation_json = db.Column(db.Text, nullable=True)
    question_purpose = db.Column(db.String(30), nullable=False, default="contextual")
    differential_priority = db.Column(db.Float, nullable=False, default=1.0)
    target_diagnosis_codes_json = db.Column(db.Text, nullable=True)
    clinical_rationale = db.Column(db.Text, nullable=True)
    show_when_differential_includes = db.Column(db.Text, nullable=True)
    hide_when_differential_below = db.Column(db.Float, nullable=True)
    gate_diagnosis_codes_json = db.Column(db.Text, nullable=True)


class ComplaintDifferentialPrior(BaseModel):
    """Baseline differential priors when a complaint is selected — before any answers."""

    __tablename__ = "complaint_differential_priors"

    complaint_code = db.Column(db.String(50), nullable=False, index=True)
    diagnosis_code = db.Column(db.String(80), nullable=False, index=True)
    prior_weight = db.Column(db.Float, nullable=False, default=0.5)

    __table_args__ = (
        db.UniqueConstraint("complaint_code", "diagnosis_code", name="uq_complaint_dx_prior"),
    )


class DiagnosisDefinition(BaseModel):
    __tablename__ = "diagnosis_definitions"

    code = db.Column(db.String(80), nullable=False, unique=True, index=True)
    name = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(50), nullable=False, default="gi")
    knowledge_topic_key = db.Column(db.String(80), nullable=True)


class AnswerWeightRule(BaseModel):
    __tablename__ = "answer_weight_rules"

    complaint_code = db.Column(db.String(50), nullable=False, index=True)
    question_code = db.Column(db.String(80), nullable=False, index=True)
    answer_match = db.Column(db.String(100), nullable=False)
    diagnosis_code = db.Column(db.String(80), nullable=False, index=True)
    weight_delta = db.Column(db.Float, nullable=False, default=0.0)


class InvestigationGuidanceRule(BaseModel):
    __tablename__ = "investigation_guidance_rules"

    complaint_code = db.Column(db.String(80), nullable=True, index=True)
    diagnosis_code = db.Column(db.String(80), nullable=True, index=True)
    investigation_code = db.Column(db.String(80), nullable=False)
    tier = db.Column(db.String(20), nullable=False, default=SUGGESTION_TIER_BASELINE)
    reason_text = db.Column(db.String(255), nullable=True)
    sort_order = db.Column(db.Integer, nullable=False, default=0)


class ManagementGuidanceRule(BaseModel):
    __tablename__ = "management_guidance_rules"

    diagnosis_code = db.Column(db.String(80), nullable=False, index=True)
    summary_text = db.Column(db.Text, nullable=False)
    principles_text = db.Column(db.Text, nullable=True)
    scores_text = db.Column(db.Text, nullable=True)
    red_flags_text = db.Column(db.Text, nullable=True)
    follow_up_text = db.Column(db.Text, nullable=True)
    knowledge_topic_key = db.Column(db.String(80), nullable=True)


class HistorySession(BaseModel):
    __tablename__ = "history_sessions"

    encounter_id = db.Column(db.Integer, db.ForeignKey("clinical_encounters.id"), nullable=False, index=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False, index=True)
    chief_complaint_code = db.Column(db.String(50), nullable=True, index=True)
    status = db.Column(db.String(20), nullable=False, default=SESSION_STATUS_DRAFT, index=True)
    session_kind = db.Column(db.String(30), nullable=False, default=SESSION_KIND_INITIAL)
    parent_session_id = db.Column(db.Integer, db.ForeignKey("history_sessions.id"), nullable=True)
    differential_json = db.Column(db.Text, nullable=True)
    confirmed_diagnosis_code = db.Column(db.String(80), nullable=True)
    diagnosis_confirmed_at = db.Column(db.DateTime(timezone=True), nullable=True)
    diagnosis_confirmed_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    completed_at = db.Column(db.DateTime(timezone=True), nullable=True)
    teaching_json = db.Column(db.Text, nullable=True)

    encounter = db.relationship("ClinicalEncounter", foreign_keys=[encounter_id])
    patient = db.relationship("Patient", foreign_keys=[patient_id])
    parent_session = db.relationship("HistorySession", remote_side="HistorySession.id")
    answers = db.relationship("HistoryAnswer", back_populates="session", lazy="dynamic")
    narrative_sections = db.relationship("HistoryNarrativeSection", back_populates="session", lazy="dynamic")
    diagnosis_confirmed_by = db.relationship("User", foreign_keys=[diagnosis_confirmed_by_id])

    @property
    def differential(self) -> dict:
        if not self.differential_json:
            return {}
        return json.loads(self.differential_json)

    @differential.setter
    def differential(self, value: dict) -> None:
        self.differential_json = json.dumps(value)

    @property
    def teaching(self) -> dict:
        if not self.teaching_json:
            return {}
        return json.loads(self.teaching_json)


class HistoryAnswer(BaseModel):
    __tablename__ = "history_answers"

    session_id = db.Column(db.Integer, db.ForeignKey("history_sessions.id"), nullable=False, index=True)
    question_code = db.Column(db.String(80), nullable=False, index=True)
    answer_value = db.Column(db.String(255), nullable=False, index=True)
    answer_display = db.Column(db.String(500), nullable=True)
    section = db.Column(db.String(40), nullable=False, index=True)
    answered_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    answered_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    session = db.relationship("HistorySession", back_populates="answers")
    __table_args__ = (
        db.UniqueConstraint("session_id", "question_code", name="uq_history_answer_session_question"),
    )


class HistoryNarrativeSection(BaseModel):
    __tablename__ = "history_narrative_sections"

    session_id = db.Column(db.Integer, db.ForeignKey("history_sessions.id"), nullable=False, index=True)
    section_key = db.Column(db.String(40), nullable=False, index=True)
    generated_text = db.Column(db.Text, nullable=True)
    edited_text = db.Column(db.Text, nullable=True)
    is_manually_edited = db.Column(db.Boolean, nullable=False, default=False)

    session = db.relationship("HistorySession", back_populates="narrative_sections")
    __table_args__ = (
        db.UniqueConstraint("session_id", "section_key", name="uq_history_narrative_session_section"),
    )

    @property
    def display_text(self) -> str:
        if self.is_manually_edited and self.edited_text:
            return self.edited_text
        return self.generated_text or ""

    @display_text.setter
    def display_text(self, value: str) -> None:
        self.edited_text = value
        self.is_manually_edited = True


class InvestigationSuggestionRecord(BaseModel):
    __tablename__ = "investigation_suggestion_records"

    session_id = db.Column(db.Integer, db.ForeignKey("history_sessions.id"), nullable=False, index=True)
    investigation_code = db.Column(db.String(80), nullable=False, index=True)
    tier = db.Column(db.String(20), nullable=False)
    reason_text = db.Column(db.String(255), nullable=True)
    is_dismissed = db.Column(db.Boolean, nullable=False, default=False)
    is_accepted = db.Column(db.Boolean, nullable=False, default=False)


class FollowUpEntry(BaseModel):
    """Immutable chronological follow-up — create only, never update clinical content."""

    __tablename__ = "follow_up_entries"

    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False, index=True)
    encounter_id = db.Column(db.Integer, db.ForeignKey("clinical_encounters.id"), nullable=True, index=True)
    prior_session_id = db.Column(db.Integer, db.ForeignKey("history_sessions.id"), nullable=True)
    narrative_text = db.Column(db.Text, nullable=False)
    structured_snapshot_json = db.Column(db.Text, nullable=True)
    documented_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    documented_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    patient = db.relationship("Patient", foreign_keys=[patient_id])
    encounter = db.relationship("ClinicalEncounter", foreign_keys=[encounter_id])
    prior_session = db.relationship("HistorySession", foreign_keys=[prior_session_id])
    documented_by = db.relationship("User", foreign_keys=[documented_by_id])
