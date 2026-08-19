"""Patient Journey AI RBAC."""

from gi_platform.clinical_ai.permissions import PermissionDeniedError, require_use

JOURNEY_ROLES = frozenset({
    'admin', 'specialist', 'hod', 'consultant', 'registrar',
    'pg_trainee', 'house_officer', 'general_endoscopy', 'nurse_manager',
})


def require_journey_view(*, role: str | None) -> None:
    if role not in JOURNEY_ROLES:
        raise PermissionDeniedError('Patient journey view denied.')


def require_journey_use(*, role: str | None) -> None:
    require_journey_view(role=role)
    require_use(role=role)
