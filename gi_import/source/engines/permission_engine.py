"""
Permission Engine — the single runtime entry point every module uses for
authorization.

Queries the database (roles / permissions / role_permissions, via
app/modules/rbac/models.py) on every call. There is deliberately no
in-memory cache of the role->permission mapping: at the scale this table
operates at (a handful of roles, a few dozen permissions, a few hundred
grants), a cache would add invalidation complexity for no measurable
benefit — a premature optimization the project's KISS principle argues
against. If profiling ever shows this matters, add caching then, with
real numbers to justify it.

Every module (Users, Reports, Research, Knowledge Library, AI, ...)
calls `permission_engine.check(...)` or `permission_engine.require(...)`
— never `user.role.code == "..."` and never a re-implementation of
permission logic local to that module.
"""

from app.core.exceptions import PermissionDeniedError


def _has_permission(user, permission_code: str) -> bool:
    if getattr(user, "is_superuser", False):
        # Bypasses the role/permission lookup entirely — this is what
        # makes a Super Administrator's access independent of whatever
        # permissions exist today or get added by a future sprint. See
        # User.is_superuser's docstring for why this isn't just "a role
        # with every permission granted."
        return True

    role = getattr(user, "role", None)
    if role is None or not getattr(role, "is_active", False):
        return False
    return role.has_permission(permission_code)


def check(user, permission: str) -> bool:
    """Silent boolean check — use this for UI decisions (e.g. whether to
    show an "Edit" button). Never logged: rendering a hidden button is
    not an access attempt worth auditing."""
    return _has_permission(user, permission)


def require(user, permission: str, *, audit_context: dict = None) -> None:
    """
    Use this at the top of every service-layer function that performs a
    permission-gated action. Raises PermissionDeniedError on failure —
    routes catch it and return HTTP 403.

    A denial is always audit-logged. `audit_context` lets the caller
    attach what was being attempted, e.g.
    {"target_type": "User", "target_id": 42}.
    """
    if _has_permission(user, permission):
        return

    # Imported here (not at module top) to avoid a hard import-time
    # dependency between the Permission Engine and the Audit Engine —
    # each can be unit-tested in isolation.
    from app.engines.audit_engine import log as audit_log

    audit_log(
        action="permission.denied",
        user=user,
        details={"permission": permission, **(audit_context or {})},
    )
    raise PermissionDeniedError(f"User does not have required permission: {permission}")
