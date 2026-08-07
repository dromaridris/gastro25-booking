"""Clinical AI RBAC helpers."""

from __future__ import annotations

from app.engines import permission_engine

from .config import ClinicalAIConfig
from .constants import PERM_CONFIGURE, PERM_USE, PERM_VIEW

TRAINEE_ROLE_CODES = frozenset(
    {
        "senior_registrar",
        "house_officer",
        "visiting_trainee",
    }
)


def require_view(user) -> None:
    permission_engine.require(user, PERM_VIEW)


def require_use(user) -> None:
    permission_engine.require(user, PERM_USE)
    _enforce_trainee_policy(user)


def require_configure(user) -> None:
    permission_engine.require(user, PERM_CONFIGURE)


def can_view(user) -> bool:
    return permission_engine.check(user, PERM_VIEW)


def can_use(user) -> bool:
    if not permission_engine.check(user, PERM_USE):
        return False
    return _trainee_allowed(user)


def can_configure(user) -> bool:
    return permission_engine.check(user, PERM_CONFIGURE)


def _enforce_trainee_policy(user) -> None:
    if _trainee_allowed(user):
        return
    from app.core.exceptions import PermissionDeniedError

    raise PermissionDeniedError("Clinical AI is not enabled for trainee roles.")


def _trainee_allowed(user) -> bool:
    role_code = getattr(getattr(user, "role", None), "code", None)
    if role_code not in TRAINEE_ROLE_CODES:
        return True
    cfg = ClinicalAIConfig.from_app()
    return cfg.trainee_ai_enabled
