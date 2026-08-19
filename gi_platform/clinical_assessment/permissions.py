"""Clinical Assessment RBAC."""

from gi_platform.clinical_ai.permissions import PermissionDeniedError, require_use

ASSESSMENT_ROLES = frozenset({
    'admin', 'specialist', 'hod', 'consultant', 'registrar',
    'pg_trainee', 'house_officer', 'general_endoscopy',
})


def require_assessment_view(*, role: str | None) -> None:
    if role not in ASSESSMENT_ROLES:
        raise PermissionDeniedError('Clinical assessment view denied.')


def require_assessment_use(*, role: str | None) -> None:
    require_assessment_view(role=role)
    require_use(role=role)
