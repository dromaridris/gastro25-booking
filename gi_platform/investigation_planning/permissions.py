"""Investigation Planning RBAC."""

from gi_platform.clinical_ai.permissions import PermissionDeniedError, require_use

PLANNING_ROLES = frozenset({
    'admin', 'specialist', 'hod', 'consultant', 'registrar',
    'pg_trainee', 'house_officer', 'general_endoscopy',
})


def require_investigation_plan_view(*, role: str | None) -> None:
    if role not in PLANNING_ROLES:
        raise PermissionDeniedError('Investigation planning view denied.')


def require_investigation_plan_use(*, role: str | None) -> None:
    require_investigation_plan_view(role=role)
    require_use(role=role)
