"""Account lifecycle management — Phase 7E."""

from __future__ import annotations

from datetime import date, timedelta

from app.core.exceptions import NotFoundError, ValidationError
from app.engines import audit_engine, permission_engine
from app.extensions import db
from app.modules.auth.models import User
from app.modules.workforce_identity.constants import (
    ACCOUNT_STATUSES,
    STATUS_ACTIVE,
    STATUS_CLOSED,
    STATUS_EXPIRED,
    STATUS_PENDING,
    STATUS_SUSPENDED,
    TRAINING_ROLE_CODES,
)
from app.modules.workforce_identity.models import UserAccountLifecycle


def _require(user, permission: str) -> None:
    permission_engine.require(user, permission)


def get_lifecycle(user_id: int) -> UserAccountLifecycle | None:
    return UserAccountLifecycle.query.filter_by(user_id=user_id, is_archived=False).first()


def enforce_login_lifecycle(user: User) -> None:
    """Called from authenticate() — blocks expired/suspended training accounts."""
    lifecycle = get_lifecycle(user.id)
    if lifecycle is None:
        return
    if lifecycle.expiry_date and lifecycle.expiry_date < date.today():
        if lifecycle.status == STATUS_ACTIVE:
            lifecycle.status = STATUS_EXPIRED
            db.session.commit()
            audit_engine.log(
                action="workforce_identity.account_expired",
                user=user,
                target_type="UserAccountLifecycle",
                target_id=lifecycle.id,
                details={"user_id": user.id, "expiry_date": lifecycle.expiry_date.isoformat()},
            )
        raise ValidationError("This training account has expired.")
    if lifecycle.status == STATUS_SUSPENDED:
        raise ValidationError("This account has been suspended.")
    if lifecycle.status == STATUS_CLOSED:
        raise ValidationError("This account has been closed.")
    if lifecycle.status == STATUS_EXPIRED:
        raise ValidationError("This training account has expired.")
    if lifecycle.status == STATUS_PENDING:
        lifecycle.status = STATUS_ACTIVE
        db.session.commit()


def create_lifecycle(
    acting_user,
    *,
    user_id: int,
    start_date: date,
    expiry_date: date,
    rotation_label: str | None = None,
    invitation_id: int | None = None,
    status: str = STATUS_PENDING,
) -> UserAccountLifecycle:
    _require(acting_user, "workforce_identity:account_manage")
    return _persist_lifecycle(
        user_id=user_id,
        start_date=start_date,
        expiry_date=expiry_date,
        rotation_label=rotation_label,
        invitation_id=invitation_id,
        status=status,
        created_by_id=getattr(acting_user, "id", None),
    )


def create_lifecycle_from_invitation(
    *,
    user_id: int,
    start_date: date,
    expiry_date: date,
    rotation_label: str | None = None,
    invitation_id: int | None = None,
) -> UserAccountLifecycle:
    """Internal — called when a trainee completes invitation registration."""
    return _persist_lifecycle(
        user_id=user_id,
        start_date=start_date,
        expiry_date=expiry_date,
        rotation_label=rotation_label,
        invitation_id=invitation_id,
        status=STATUS_ACTIVE,
        created_by_id=None,
    )


def _persist_lifecycle(
    *,
    user_id: int,
    start_date: date,
    expiry_date: date,
    rotation_label: str | None,
    invitation_id: int | None,
    status: str,
    created_by_id: int | None,
) -> UserAccountLifecycle:
    if status not in ACCOUNT_STATUSES:
        raise ValidationError(f"Invalid account status '{status}'.")
    if expiry_date < start_date:
        raise ValidationError("Expiry date must be on or after start date.")
    if get_lifecycle(user_id):
        raise ValidationError("Lifecycle record already exists for this user.")
    user = User.query.get(user_id)
    if user is None:
        raise NotFoundError(f"No user with id {user_id}")
    record = UserAccountLifecycle(
        user_id=user_id,
        start_date=start_date,
        expiry_date=expiry_date,
        status=status,
        rotation_label=rotation_label,
        invitation_id=invitation_id,
        department_id=getattr(user, "department_id", 1) or 1,
        created_by_id=created_by_id,
    )
    db.session.add(record)
    db.session.commit()
    return record


def extend_account(acting_user, user_id: int, *, new_expiry_date: date, notes: str | None = None) -> UserAccountLifecycle:
    _require(acting_user, "workforce_identity:account_manage")
    record = get_lifecycle(user_id)
    if record is None:
        raise NotFoundError("No lifecycle record for this user.")
    old_expiry = record.expiry_date
    record.expiry_date = new_expiry_date
    if record.status == STATUS_EXPIRED and new_expiry_date >= date.today():
        record.status = STATUS_ACTIVE
    if notes:
        record.notes = notes
    db.session.commit()
    audit_engine.log(
        action="workforce_identity.account_extended",
        user=acting_user,
        target_type="UserAccountLifecycle",
        target_id=record.id,
        details={"user_id": user_id, "old_expiry": old_expiry.isoformat(), "new_expiry": new_expiry_date.isoformat()},
    )
    return record


def suspend_account(acting_user, user_id: int, *, reason: str | None = None) -> UserAccountLifecycle:
    _require(acting_user, "workforce_identity:account_manage")
    record = get_lifecycle(user_id)
    if record is None:
        raise NotFoundError("No lifecycle record for this user.")
    record.status = STATUS_SUSPENDED
    if reason:
        record.notes = reason
    db.session.commit()
    audit_engine.log(
        action="workforce_identity.account_suspended",
        user=acting_user,
        target_type="UserAccountLifecycle",
        target_id=record.id,
        details={"user_id": user_id},
    )
    return record


def close_account(acting_user, user_id: int, *, reason: str | None = None) -> UserAccountLifecycle:
    _require(acting_user, "workforce_identity:account_manage")
    record = get_lifecycle(user_id)
    if record is None:
        raise NotFoundError("No lifecycle record for this user.")
    record.status = STATUS_CLOSED
    user = User.query.get(user_id)
    if user:
        user.is_active_account = False
    if reason:
        record.notes = reason
    db.session.commit()
    audit_engine.log(
        action="workforce_identity.account_closed",
        user=acting_user,
        target_type="UserAccountLifecycle",
        target_id=record.id,
        details={"user_id": user_id},
    )
    return record


def expire_due_accounts() -> int:
    """Batch expiry job — preserves identity and historical records."""
    today = date.today()
    records = UserAccountLifecycle.query.filter(
        UserAccountLifecycle.is_archived.is_(False),
        UserAccountLifecycle.status.in_([STATUS_ACTIVE, STATUS_PENDING]),
        UserAccountLifecycle.expiry_date < today,
    ).all()
    for record in records:
        record.status = STATUS_EXPIRED
        audit_engine.log(
            action="workforce_identity.account_expired",
            target_type="UserAccountLifecycle",
            target_id=record.id,
            details={"user_id": record.user_id},
        )
    if records:
        db.session.commit()
    return len(records)


def list_expiring_within(days: int = 7) -> list[UserAccountLifecycle]:
    today = date.today()
    cutoff = today + timedelta(days=days)
    return (
        UserAccountLifecycle.query.filter(
            UserAccountLifecycle.is_archived.is_(False),
            UserAccountLifecycle.status == STATUS_ACTIVE,
            UserAccountLifecycle.expiry_date >= today,
            UserAccountLifecycle.expiry_date <= cutoff,
        )
        .order_by(UserAccountLifecycle.expiry_date.asc())
        .all()
    )


def list_active_trainees(department_id: int | None = None) -> list[UserAccountLifecycle]:
    query = UserAccountLifecycle.query.filter(
        UserAccountLifecycle.is_archived.is_(False),
        UserAccountLifecycle.status.in_([STATUS_ACTIVE, STATUS_PENDING]),
    )
    if department_id:
        query = query.filter_by(department_id=department_id)
    return query.order_by(UserAccountLifecycle.expiry_date.asc()).all()


def is_training_role(role_code: str) -> bool:
    return role_code in TRAINING_ROLE_CODES
