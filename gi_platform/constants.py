"""Shared constants for governance, logbook, roster, and attendance."""

from __future__ import annotations

# CanMEDS competency domains — international postgraduate medical education framework
CANMEDS_DOMAINS = (
    ('medical_expert', 'Medical Expert'),
    ('communicator', 'Communicator'),
    ('collaborator', 'Collaborator'),
    ('leader', 'Leader'),
    ('health_advocate', 'Health Advocate'),
    ('scholar', 'Scholar'),
    ('professional', 'Professional'),
)

CANMEDS_SCORE_LABELS = {
    1: 'Observes only — not yet entrusted',
    2: 'Direct supervision required',
    3: 'Indirect supervision — ready with backup',
    4: 'Independent practice expected',
    5: 'Teaches / supervises others',
}

ROSTER_TYPE_TRAINEE = 'pg_trainee'
ROSTER_TYPE_HOUSE_OFFICER = 'house_officer'
ROSTER_TYPES = (ROSTER_TYPE_TRAINEE, ROSTER_TYPE_HOUSE_OFFICER)
ROSTER_TYPE_LABELS = {
    ROSTER_TYPE_TRAINEE: 'PG Trainee on-call',
    ROSTER_TYPE_HOUSE_OFFICER: 'House Officer on-call',
}

PERM_ROSTER_TRAINEE = 'roster_manager_trainee'
PERM_ROSTER_HOUSE_OFFICER = 'roster_manager_house_officer'
ROSTER_PERMISSIONS = (PERM_ROSTER_TRAINEE, PERM_ROSTER_HOUSE_OFFICER)
ROSTER_PERMISSION_LABELS = {
    PERM_ROSTER_TRAINEE: 'Trainee roster manager',
    PERM_ROSTER_HOUSE_OFFICER: 'House Officer roster manager',
}

CLINICAL_STAFF_ROLES = frozenset({
    'admin', 'hod', 'consultant', 'specialist', 'registrar',
    'house_officer', 'pg_trainee', 'general_endoscopy',
})

# Admin and Head of Department — full platform access (routes, nav, booking overrides).
FULL_ACCESS_ROLES = frozenset({'admin', 'hod'})

# Ward / training tasks — delete allowed for these roles (presenters mark done, not delete).
TASK_DELETE_ROLES = frozenset({'admin', 'hod', 'consultant', 'registrar'})

# Ward tasks — consultants and registrars may complete any ward task on a patient file.
WARD_TASK_APPROVE_ROLES = frozenset({'admin', 'hod', 'consultant', 'specialist', 'registrar'})


def has_full_access(role: str | None) -> bool:
    return bool(role) and role in FULL_ACCESS_ROLES


def can_delete_task(role: str | None) -> bool:
    return has_full_access(role) or bool(role and role in TASK_DELETE_ROLES)


def can_approve_ward_task(role: str | None) -> bool:
    return has_full_access(role) or bool(role and role in WARD_TASK_APPROVE_ROLES)

INCIDENT_CATEGORIES = (
    'medication_error', 'procedure_complication', 'patient_fall',
    'wrong_site', 'delay_in_care', 'equipment_failure', 'communication',
    'documentation', 'infection', 'other',
)
INCIDENT_SEVERITIES = ('minor', 'moderate', 'major', 'sentinel')
MM_STATUSES = ('scheduled', 'presented', 'closed')
AUDIT_STATUSES = ('planned', 'in_progress', 'completed', 'cancelled')
DOCUMENT_TYPES = ('sop', 'protocol', 'policy', 'guideline', 'form')
DOCUMENT_STATUSES = ('draft', 'active', 'archived')
CHECKLIST_TYPES = ('endoscopy_safety', 'sedation', 'who_surgical', 'ward_round')

SHIFT_TYPES = ('day', 'evening', 'on_call', 'night', 'leave')
ATTENDANCE_ADJUST_TYPES = ('teaching', 'meeting', 'conference', 'leave', 'other')

JOURNEY_EVENT_TYPES = (
    'admission', 'history', 'examination', 'investigation_order',
    'investigation_result', 'procedure', 'management_plan', 'discharge',
    'follow_up', 'research_enrollment', 'note',
)

DISCHARGE_OUTCOMES = (
    ('discharged', 'Discharged home'),
    ('referred', 'Referred'),
    ('lama', 'LAMA (left against medical advice)'),
    ('dor', 'DOR (discharge on request)'),
    ('expired', 'Expired'),
)
