"""Analytics RBAC helpers."""

from __future__ import annotations

import os

from app.engines import permission_engine

from .constants import (
    PERM_CONFIGURE,
    PERM_EXPORT,
    PERM_VIEW,
    TRAINEE_ROLE_CODES,
)


def _trainee_enabled() -> bool:
    return os.environ.get("ANALYTICS_TRAINEE_ENABLED", "").lower() in ("1", "true", "yes")


def require_view(user) -> None:
    permission_engine.require(user, PERM_VIEW)
    _enforce_trainee_policy(user)


def require_configure(user) -> None:
    permission_engine.require(user, PERM_CONFIGURE)


def require_export(user) -> None:
    permission_engine.require(user, PERM_EXPORT)
    _enforce_trainee_policy(user)


def can_view(user) -> bool:
    if not permission_engine.check(user, PERM_VIEW):
        return False
    return _trainee_allowed(user)


def can_configure(user) -> bool:
    return permission_engine.check(user, PERM_CONFIGURE)


def can_export(user) -> bool:
    if not permission_engine.check(user, PERM_EXPORT):
        return False
    return _trainee_allowed(user)


def _enforce_trainee_policy(user) -> None:
    if _trainee_allowed(user):
        return
    from app.core.exceptions import PermissionDeniedError

    raise PermissionDeniedError("Analytics access is not enabled for trainee roles.")


def _trainee_allowed(user) -> bool:
    role_code = getattr(getattr(user, "role", None), "code", None)
    if role_code not in TRAINEE_ROLE_CODES:
        return True
    return _trainee_enabled()
