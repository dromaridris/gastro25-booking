"""Clinical Interpretation RBAC."""

from gi_platform.clinical_ai.permissions import PermissionDeniedError, require_use

INTERPRETATION_ROLES = frozenset({
    'admin', 'specialist', 'hod', 'consultant', 'registrar',
    'pg_trainee', 'house_officer', 'general_endoscopy',
})


def require_interpretation_view(*, role: str | None) -> None:
    if role not in INTERPRETATION_ROLES:
        raise PermissionDeniedError('Clinical interpretation view denied.')


def require_interpretation_use(*, role: str | None) -> None:
    require_interpretation_view(role=role)
    require_use(role=role)
