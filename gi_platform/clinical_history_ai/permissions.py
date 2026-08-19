"""Clinical History AI RBAC — Gastro25 roles."""

from __future__ import annotations

from gi_platform.clinical_ai.permissions import PermissionDeniedError, require_use, require_view

HISTORY_VIEW_ROLES = frozenset({
    'admin', 'specialist', 'hod', 'consultant', 'registrar',
    'pg_trainee', 'house_officer', 'general_endoscopy', 'nurse_manager', 'staff_nurse',
})
HISTORY_DOCUMENT_ROLES = frozenset({
    'admin', 'specialist', 'hod', 'consultant', 'registrar',
    'pg_trainee', 'house_officer', 'general_endoscopy',
})


def require_history_view(*, role: str | None) -> None:
    if role not in HISTORY_VIEW_ROLES:
        raise PermissionDeniedError('Guided history view access denied.')


def require_history_document(*, role: str | None) -> None:
    if role not in HISTORY_DOCUMENT_ROLES:
        raise PermissionDeniedError('Guided history documentation access denied.')


def require_ai_generation(*, role: str | None) -> None:
    require_use(role=role)
