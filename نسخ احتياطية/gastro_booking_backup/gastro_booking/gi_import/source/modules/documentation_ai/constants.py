"""Clinical Documentation Intelligence constants."""

from __future__ import annotations

DOC_TYPE_ADMISSION = "admission_note"
DOC_TYPE_PROGRESS = "progress_note"
DOC_TYPE_DISCHARGE = "discharge_summary"
DOC_TYPE_REFERRAL = "referral_letter"
DOC_TYPE_FOLLOW_UP = "follow_up_note"
DOC_TYPE_CLINICAL_REPORT = "clinical_report"
DOC_TYPE_PROCEDURE_SUMMARY = "procedure_summary"

ALL_DOC_TYPES = (
    DOC_TYPE_ADMISSION,
    DOC_TYPE_PROGRESS,
    DOC_TYPE_DISCHARGE,
    DOC_TYPE_REFERRAL,
    DOC_TYPE_FOLLOW_UP,
    DOC_TYPE_CLINICAL_REPORT,
    DOC_TYPE_PROCEDURE_SUMMARY,
)

DOC_STATUS_DRAFT = "draft"
DOC_STATUS_REVIEWED = "reviewed"
DOC_STATUS_APPROVED = "approved"
DOC_STATUS_REJECTED = "rejected"
DOC_STATUS_SIGNED = "signed"

SECTION_STATUS_DRAFT = "draft"
SECTION_STATUS_APPROVED = "approved"
SECTION_STATUS_REJECTED = "rejected"
SECTION_STATUS_MODIFIED = "modified"

ACTION_EDIT = "edit"
ACTION_REGENERATE = "regenerate"
ACTION_APPROVE = "approve"
ACTION_REJECT = "reject"
ACTION_SIGN = "sign"
ACTION_MANUAL = "manual"

AUDIT_PREFIX = "documentation_ai"
