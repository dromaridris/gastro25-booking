"""Clinical AI RBAC — Gastro25 role mapping."""

from __future__ import annotations

from gi_platform.clinical_ai.config import ClinicalAIConfig
from gi_platform.constants import has_full_access

VIEW_ROLES = frozenset({
    'admin', 'specialist', 'hod', 'consultant', 'registrar',
    'pg_trainee', 'house_officer', 'general_endoscopy',
})
USE_ROLES = VIEW_ROLES
CONFIGURE_ROLES = frozenset({'admin', 'specialist', 'hod'})
TRAINEE_ROLES = frozenset({'pg_trainee', 'house_officer'})


class PermissionDeniedError(PermissionError):
    pass


def require_view(*, role: str | None) -> None:
    if not can_view(role=role):
        raise PermissionDeniedError('Clinical AI view access denied.')


def require_use(*, role: str | None) -> None:
    if not can_use(role=role):
        raise PermissionDeniedError('Clinical AI use access denied.')


def require_configure(*, role: str | None) -> None:
    if not can_configure(role=role):
        raise PermissionDeniedError('Clinical AI configuration access denied.')


def can_view(*, role: str | None) -> bool:
    if has_full_access(role):
        return True
    return role in VIEW_ROLES


def can_use(*, role: str | None) -> bool:
    if not can_view(role=role):
        return False
    if role not in TRAINEE_ROLES:
        return True
    return ClinicalAIConfig.from_env().trainee_ai_enabled


def can_configure(*, role: str | None) -> bool:
    if has_full_access(role):
        return True
    return role in CONFIGURE_ROLES
