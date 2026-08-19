"""Documentation AI RBAC."""

from gi_platform.clinical_ai.permissions import PermissionDeniedError, require_use

DOC_ROLES = frozenset({
    'admin', 'specialist', 'hod', 'consultant', 'registrar',
    'pg_trainee', 'house_officer', 'general_endoscopy',
})

SIGN_ROLES = frozenset({'admin', 'hod', 'consultant', 'specialist', 'registrar'})


def require_documentation_view(*, role: str | None) -> None:
    if role not in DOC_ROLES:
        raise PermissionDeniedError('Documentation AI view denied.')


def require_documentation_use(*, role: str | None) -> None:
    require_documentation_view(role=role)
    require_use(role=role)


def require_documentation_sign(*, role: str | None) -> None:
    require_documentation_use(role=role)
    if role not in SIGN_ROLES:
        raise PermissionDeniedError('Document signing requires registrar or above.')
