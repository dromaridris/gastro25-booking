"""Management Plan Assistant constants — Gastro25."""

from __future__ import annotations

CATEGORY_TREATMENT = 'treatment_consideration'
CATEGORY_MONITORING = 'monitoring'
CATEGORY_FOLLOW_UP = 'follow_up'
CATEGORY_PATIENT_EDUCATION = 'patient_education'
CATEGORY_SAFETY = 'safety'
CATEGORY_REFERRAL = 'referral'

CATEGORY_DISPLAY_ORDER = (
    CATEGORY_TREATMENT, CATEGORY_MONITORING, CATEGORY_FOLLOW_UP,
    CATEGORY_PATIENT_EDUCATION, CATEGORY_SAFETY, CATEGORY_REFERRAL,
)

PRIORITY_ESSENTIAL = 'essential'
PRIORITY_RECOMMENDED = 'recommended'
PRIORITY_OPTIONAL = 'optional'

PLAN_STATUS_DRAFT = 'draft'
PLAN_STATUS_REVIEWED = 'reviewed'
PLAN_STATUS_APPROVED = 'approved'
PLAN_STATUS_MODIFIED = 'modified'
PLAN_STATUS_REJECTED = 'rejected'

SUGGESTION_STATUS_SUGGESTED = 'suggested'

DECISION_ACCEPTED = 'accepted'
DECISION_REJECTED = 'rejected'
DECISION_MODIFIED = 'modified'
DECISION_MANUAL = 'manual'

CONFIDENCE_HIGH = 'high'
CONFIDENCE_MEDIUM = 'medium'
CONFIDENCE_LOW = 'low'

AUDIT_PREFIX = 'management_plan_ai'

WORKING_DIAGNOSIS_STATUSES = frozenset({
    'confirmed', 'suspected', 'accepted', 'manual', 'modified',
})
