"""Clinical Documentation Intelligence constants — Gastro25."""

from __future__ import annotations

DOC_TYPE_ADMISSION = 'admission_note'
DOC_TYPE_PROGRESS = 'progress_note'
DOC_TYPE_DISCHARGE = 'discharge_summary'
DOC_TYPE_REFERRAL = 'referral_letter'
DOC_TYPE_FOLLOW_UP = 'follow_up_note'

DOC_STATUS_DRAFT = 'draft'
DOC_STATUS_APPROVED = 'approved'
DOC_STATUS_REJECTED = 'rejected'
DOC_STATUS_SIGNED = 'signed'

SECTION_STATUS_DRAFT = 'draft'
SECTION_STATUS_APPROVED = 'approved'
SECTION_STATUS_REJECTED = 'rejected'
SECTION_STATUS_MODIFIED = 'modified'

ACTION_EDIT = 'edit'
ACTION_REGENERATE = 'regenerate'
ACTION_APPROVE = 'approve'
ACTION_REJECT = 'reject'
ACTION_SIGN = 'sign'

AUDIT_PREFIX = 'documentation_ai'
