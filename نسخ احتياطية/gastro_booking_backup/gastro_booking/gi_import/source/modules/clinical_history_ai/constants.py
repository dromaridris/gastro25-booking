"""Clinical History AI constants."""

from __future__ import annotations

CATEGORY_HPI = "history_of_present_illness"
CATEGORY_ASSOCIATED_SYMPTOMS = "associated_symptoms"
CATEGORY_NEGATIVE_FINDINGS = "negative_findings"
CATEGORY_RED_FLAGS = "red_flags"
CATEGORY_PMH = "past_medical_history"
CATEGORY_MEDICATION = "medication_history"
CATEGORY_ALLERGY = "allergy_history"
CATEGORY_FAMILY = "family_history"
CATEGORY_SOCIAL = "social_history"
CATEGORY_RISK_FACTORS = "risk_factors"
CATEGORY_ROS = "review_of_systems"

ALL_QUESTION_CATEGORIES = (
    CATEGORY_HPI,
    CATEGORY_ASSOCIATED_SYMPTOMS,
    CATEGORY_NEGATIVE_FINDINGS,
    CATEGORY_RED_FLAGS,
    CATEGORY_PMH,
    CATEGORY_MEDICATION,
    CATEGORY_ALLERGY,
    CATEGORY_FAMILY,
    CATEGORY_SOCIAL,
    CATEGORY_RISK_FACTORS,
    CATEGORY_ROS,
)

QUESTION_TYPE_BOOLEAN = "boolean"
QUESTION_TYPE_CHOICE = "choice"
QUESTION_TYPE_TEXT = "text"
QUESTION_TYPE_MULTI_CHOICE = "multi_choice"

ALL_QUESTION_TYPES = (
    QUESTION_TYPE_BOOLEAN,
    QUESTION_TYPE_CHOICE,
    QUESTION_TYPE_TEXT,
    QUESTION_TYPE_MULTI_CHOICE,
)

QUESTION_STATUS_ACTIVE = "active"
QUESTION_STATUS_INACTIVE = "inactive"

SESSION_STATUS_QUESTIONING = "questioning"
SESSION_STATUS_COMPOSING = "composing"
SESSION_STATUS_DRAFT_READY = "draft_ready"
SESSION_STATUS_APPROVED = "approved"
SESSION_STATUS_DISCARDED = "discarded"

ALL_SESSION_STATUSES = (
    SESSION_STATUS_QUESTIONING,
    SESSION_STATUS_COMPOSING,
    SESSION_STATUS_DRAFT_READY,
    SESSION_STATUS_APPROVED,
    SESSION_STATUS_DISCARDED,
)

DRAFT_STATUS_DRAFT = "draft"
DRAFT_STATUS_REVIEWED = "reviewed"
DRAFT_STATUS_MODIFIED = "modified"
DRAFT_STATUS_APPROVED = "approved"
DRAFT_STATUS_REJECTED = "rejected"

ALL_DRAFT_STATUSES = (
    DRAFT_STATUS_DRAFT,
    DRAFT_STATUS_REVIEWED,
    DRAFT_STATUS_MODIFIED,
    DRAFT_STATUS_APPROVED,
    DRAFT_STATUS_REJECTED,
)

AUDIT_PREFIX = "clinical_history_ai"

COMPOSER_SECTIONS = (
    "chief_complaint",
    "history_of_present_illness",
    "associated_symptoms",
    "relevant_negative_findings",
    "past_medical_history",
    "medication_history",
    "social_history",
    "family_history",
    "risk_factors",
)
