"""Management Plan AI RBAC."""

from gi_platform.clinical_ai.permissions import PermissionDeniedError, require_use

MGMT_ROLES = frozenset({
    'admin', 'specialist', 'hod', 'consultant', 'registrar',
    'pg_trainee', 'house_officer', 'general_endoscopy',
})


def require_management_plan_ai_view(*, role: str | None) -> None:
    if role not in MGMT_ROLES:
        raise PermissionDeniedError('Management plan AI view denied.')


def require_management_plan_ai_use(*, role: str | None) -> None:
    require_management_plan_ai_view(role=role)
    require_use(role=role)
