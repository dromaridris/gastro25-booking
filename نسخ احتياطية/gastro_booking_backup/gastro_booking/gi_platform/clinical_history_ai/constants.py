"""Clinical History AI constants."""

from __future__ import annotations

CATEGORY_HPI = 'history_of_present_illness'
CATEGORY_ASSOCIATED_SYMPTOMS = 'associated_symptoms'
CATEGORY_NEGATIVE_FINDINGS = 'negative_findings'
CATEGORY_RED_FLAGS = 'red_flags'
CATEGORY_PMH = 'past_medical_history'
CATEGORY_MEDICATION = 'medication_history'
CATEGORY_ALLERGY = 'allergy_history'
CATEGORY_FAMILY = 'family_history'
CATEGORY_SOCIAL = 'social_history'
CATEGORY_RISK_FACTORS = 'risk_factors'
CATEGORY_ROS = 'review_of_systems'

QUESTION_TYPE_BOOLEAN = 'boolean'
QUESTION_TYPE_CHOICE = 'choice'
QUESTION_TYPE_TEXT = 'text'
QUESTION_TYPE_MULTI_CHOICE = 'multi_choice'

QUESTION_STATUS_ACTIVE = 'active'

SESSION_STATUS_QUESTIONING = 'questioning'
SESSION_STATUS_COMPOSING = 'composing'
SESSION_STATUS_DRAFT_READY = 'draft_ready'
SESSION_STATUS_APPROVED = 'approved'
SESSION_STATUS_DISCARDED = 'discarded'

DRAFT_STATUS_DRAFT = 'draft'
DRAFT_STATUS_REVIEWED = 'reviewed'
DRAFT_STATUS_MODIFIED = 'modified'
DRAFT_STATUS_APPROVED = 'approved'
DRAFT_STATUS_REJECTED = 'rejected'

AUDIT_PREFIX = 'clinical_history_ai'

COMPOSER_SECTIONS = (
    'chief_complaint',
    'history_of_present_illness',
    'associated_symptoms',
    'relevant_negative_findings',
    'past_medical_history',
    'medication_history',
    'social_history',
    'family_history',
    'risk_factors',
)

DEFAULT_COMPLAINT = '__default__'
