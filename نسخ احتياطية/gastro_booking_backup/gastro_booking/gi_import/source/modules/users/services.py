"""
Service layer for user administration (as distinct from authentication —
see app/modules/auth/services.py for login/logout logic). Every function
here that changes state is permission-gated via the Permission Engine and
writes an audit trail entry via the Audit Engine. Routes stay thin:
parse request -> call service -> render/redirect.

Permission codes ("user:manage", "user:view") are string literals, not
imported constants — see app/modules/rbac/ for why: the set of
roles/permissions and what each role can do is database data, not Python.
A permission code in a require() call is just this function saying which
check applies to it, the same way a URL string in a redirect() call
isn't "hardcoding routes."
"""

from app.core.exceptions import NotFoundError, ValidationError
from app.engines import audit_engine, permission_engine
from app.extensions import db
from app.modules.auth.models import User
from app.modules.rbac import services as rbac_services
from app.modules.rbac.seed_data import SUPERUSER_ROLE_CODE


def _resolve_role(role_code: str):
    try:
        return rbac_services.get_role_by_code(role_code)
    except NotFoundError:
        raise ValidationError(f"Unknown role: {role_code}")


def list_users(acting_user, include_archived: bool = False):
    permission_engine.require(acting_user, "user:view")
    query = User.query
    if not include_archived:
        query = query.filter_by(is_archived=False)
    return query.order_by(User.full_name.asc()).all()


def get_user(acting_user, user_id: int) -> User:
    permission_engine.require(acting_user, "user:view")
    user = User.query.get(user_id)
    if user is None:
        raise NotFoundError(f"No user with id {user_id}")
    return user


def create_user(
    acting_user, full_name: str, email: str, password: str, role: str, department_id: int
) -> User:
    permission_engine.require(
        acting_user, "user:manage", audit_context={"target_type": "User"}
    )

    role_obj = _resolve_role(role)

    email_normalized = email.lower().strip()
    if User.query.filter_by(email=email_normalized).first() is not None:
        raise ValidationError("A user with this email already exists.")

    if not password or len(password) < 8:
        raise ValidationError("Password must be at least 8 characters.")

    user = User(
        full_name=full_name.strip(),
        email=email_normalized,
        role_id=role_obj.id,
        department_id=department_id,
        created_by_id=getattr(acting_user, "id", None),
    )
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    audit_engine.log(
        action="user.created",
        user=acting_user,
        target_type="User",
        target_id=user.id,
        details={"email": user.email, "role": role_obj.code},
    )
    return user


def update_user(acting_user, target_user: User, full_name: str, email: str) -> User:
    """Updates non-sensitive profile fields. Role changes go through
    change_role() — kept separate because a role change is a more
    sensitive action worth its own explicit audit action name."""
    permission_engine.require(
        acting_user,
        "user:manage",
        audit_context={"target_type": "User", "target_id": target_user.id},
    )

    email_normalized = email.lower().strip()
    existing = User.query.filter_by(email=email_normalized).first()
    if existing is not None and existing.id != target_user.id:
        raise ValidationError("A user with this email already exists.")

    before = {"full_name": target_user.full_name, "email": target_user.email}
    target_user.full_name = full_name.strip()
    target_user.email = email_normalized
    db.session.commit()

    audit_engine.log(
        action="user.updated",
        user=acting_user,
        target_type="User",
        target_id=target_user.id,
        details={"before": before, "after": {"full_name": target_user.full_name, "email": target_user.email}},
    )
    return target_user


def change_role(acting_user, target_user: User, new_role: str) -> User:
    permission_engine.require(
        acting_user,
        "user:manage",
        audit_context={"target_type": "User", "target_id": target_user.id},
    )

    new_role_obj = _resolve_role(new_role)

    old_role_code = target_user.role.code if target_user.role else None
    target_user.role_id = new_role_obj.id
    db.session.commit()

    audit_engine.log(
        action="user.role_changed",
        user=acting_user,
        target_type="User",
        target_id=target_user.id,
        details={"old_role": old_role_code, "new_role": new_role_obj.code},
    )
    return target_user


def deactivate_user(acting_user, target_user: User, reason: str = None) -> User:
    """Deactivation is an archive operation, not a delete — the account
    row is preserved so historical records (reports authored, audit
    trail entries) still resolve correctly."""
    permission_engine.require(
        acting_user,
        "user:manage",
        audit_context={"target_type": "User", "target_id": target_user.id},
    )

    target_user.is_active_account = False
    target_user.archive(by_user_id=getattr(acting_user, "id", None), reason=reason)
    db.session.commit()

    audit_engine.log(
        action="user.deactivated",
        user=acting_user,
        target_type="User",
        target_id=target_user.id,
        details={"reason": reason},
    )
    return target_user


def reactivate_user(acting_user, target_user: User) -> User:
    permission_engine.require(
        acting_user,
        "user:manage",
        audit_context={"target_type": "User", "target_id": target_user.id},
    )

    target_user.is_active_account = True
    target_user.restore()
    db.session.commit()

    audit_engine.log(
        action="user.reactivated",
        user=acting_user,
        target_type="User",
        target_id=target_user.id,
    )
    return target_user


def set_daily_appointment_limit(
    acting_user, target_user: User, limit: int = None
) -> User:
    """
    Sprint 2A: sets target_user's per-day appointment-CREATION cap (see
    app/modules/appointments/services.py's _enforce_daily_limit for how
    it's enforced). limit=None means unlimited -- the same gate
    ("user:manage") as every other account-administration action, since
    this is account configuration, not a clinical/scheduling decision.
    """
    permission_engine.require(
        acting_user,
        "user:manage",
        audit_context={"target_type": "User", "target_id": target_user.id},
    )

    if limit is not None and limit < 0:
        raise ValidationError("Daily appointment limit cannot be negative.")

    old_limit = target_user.daily_appointment_limit
    target_user.daily_appointment_limit = limit
    db.session.commit()

    audit_engine.log(
        action="user.appointment_limit_changed",
        user=acting_user,
        target_type="User",
        target_id=target_user.id,
        details={"old_limit": old_limit, "new_limit": limit},
    )
    return target_user


def set_provider_flag(acting_user, target_user: User, is_provider: bool) -> User:
    """
    Sprint 2A correction: toggles target_user's eligibility to be
    selected as an appointment provider (see
    app/modules/appointments/forms.py's _provider_choices). Gated by
    user:manage, same as every other account-configuration action --
    deliberately NOT inferred from the user's role/permissions, per
    explicit decision that provider status must be a dedicated flag,
    not coupled to report:draft/report:sign or any other permission.
    """
    permission_engine.require(
        acting_user,
        "user:manage",
        audit_context={"target_type": "User", "target_id": target_user.id},
    )

    old_value = target_user.is_provider
    target_user.is_provider = bool(is_provider)
    db.session.commit()

    audit_engine.log(
        action="user.provider_flag_changed",
        user=acting_user,
        target_type="User",
        target_id=target_user.id,
        details={"old_value": old_value, "new_value": target_user.is_provider},
    )
    return target_user


def bootstrap_superadmin(
    full_name: str, email: str, password: str, department_id: int, force: bool = False
) -> User:
    """
    Creates a Super Administrator account. Deliberately bypasses
    permission_engine.require("user:manage") — that gate assumes an
    authorized acting_user already exists, and the entire point of a
    bootstrap mechanism is that on a fresh system, no such user does yet.

    Safety instead comes from this guard: refuses to create another
    Super Administrator if an active one already exists, unless
    force=True is passed explicitly. Without this, re-running the
    bootstrap script (or someone finding it later) could silently mint
    extra privileged accounts on a system that's already live.
    """
    existing_superusers = User.query.filter_by(is_superuser=True, is_archived=False).count()
    if existing_superusers > 0 and not force:
        raise ValidationError(
            f"{existing_superusers} active Super Administrator account(s) already "
            "exist. Pass force=True to create an additional one deliberately."
        )

    email_normalized = email.lower().strip()
    if User.query.filter_by(email=email_normalized).first() is not None:
        raise ValidationError("A user with this email already exists.")

    if not password or len(password) < 8:
        raise ValidationError("Password must be at least 8 characters.")

    role = rbac_services.get_role_by_code(SUPERUSER_ROLE_CODE)

    user = User(
        full_name=full_name.strip(),
        email=email_normalized,
        role_id=role.id,
        department_id=department_id,
        is_superuser=True,
    )
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    audit_engine.log(
        action="user.superuser_bootstrap",
        user=user,
        target_type="User",
        target_id=user.id,
        details={"email": user.email, "force": force},
    )
    return user
