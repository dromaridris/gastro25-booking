"""HoD tools for training account expiry and clinical supervisor assignment."""

from __future__ import annotations

from datetime import date

from app.core.exceptions import NotFoundError, ValidationError
from app.engines import audit_engine, permission_engine
from app.extensions import db
from app.modules.auth.models import User
from app.modules.rbac.models import Role
from app.modules.workforce_identity.constants import TRAINING_ROLE_CODES
from app.modules.workforce_identity.lifecycle_services import (
    create_lifecycle,
    extend_account,
    get_lifecycle,
    is_training_role,
)

SUPERVISOR_ROLE_CODES = frozenset({"head_of_department", "core_consultant", "consultant"})


def _require(user, permission: str) -> None:
    permission_engine.require(user, permission)


def list_eligible_supervisors(department_id: int | None = None) -> list[User]:
    base_query = (
        User.query.join(Role, User.role_id == Role.id)
        .filter(
            User.is_archived.is_(False),
            User.is_active_account.is_(True),
            Role.code.in_(SUPERVISOR_ROLE_CODES),
        )
        .order_by(User.full_name.asc())
    )
    if department_id:
        dept_supervisors = base_query.filter(User.department_id == department_id).all()
        if dept_supervisors:
            return dept_supervisors
    return base_query.all()


def assign_clinical_supervisor(acting_user, user_id: int, *, supervisor_user_id: int | None) -> User:
    _require(acting_user, "workforce_identity:account_manage")
    trainee = User.query.get(user_id)
    if trainee is None:
        raise NotFoundError(f"No user with id {user_id}")
    role_code = trainee.role.code if trainee.role else None
    if role_code not in TRAINING_ROLE_CODES:
        raise ValidationError("Clinical supervisor can only be assigned to training accounts.")

    old_supervisor_id = trainee.clinical_supervisor_id
    if supervisor_user_id is None:
        trainee.clinical_supervisor_id = None
    else:
        supervisor = User.query.get(supervisor_user_id)
        if supervisor is None:
            raise NotFoundError(f"No user with id {supervisor_user_id}")
        sup_role = supervisor.role.code if supervisor.role else None
        if sup_role not in SUPERVISOR_ROLE_CODES:
            raise ValidationError("Supervisor must be a consultant or head of department.")
        if trainee.id == supervisor.id:
            raise ValidationError("A user cannot supervise themselves.")
        trainee.clinical_supervisor_id = supervisor.id

    db.session.commit()
    audit_engine.log(
        action="workforce_identity.supervisor_assigned",
        user=acting_user,
        target_type="User",
        target_id=trainee.id,
        details={"old_supervisor_id": old_supervisor_id, "new_supervisor_id": trainee.clinical_supervisor_id},
    )
    return trainee


def set_account_period(
    acting_user,
    user_id: int,
    *,
    start_date: date,
    expiry_date: date,
    rotation_label: str | None = None,
) -> User:
    """Create or update the time-limited account period for a training user."""
    _require(acting_user, "workforce_identity:account_manage")
    user = User.query.get(user_id)
    if user is None:
        raise NotFoundError(f"No user with id {user_id}")
    role_code = user.role.code if user.role else None
    if not is_training_role(role_code or ""):
        raise ValidationError("Account expiry applies only to trainee and house officer roles.")

    record = get_lifecycle(user_id)
    if record is None:
        create_lifecycle(
            acting_user,
            user_id=user_id,
            start_date=start_date,
            expiry_date=expiry_date,
            rotation_label=rotation_label,
            status="active",
        )
    else:
        if expiry_date < start_date:
            raise ValidationError("Expiry date must be on or after start date.")
        record.start_date = start_date
        record.expiry_date = expiry_date
        if rotation_label is not None:
            record.rotation_label = rotation_label or None
        if record.status == "expired" and expiry_date >= date.today():
            record.status = "active"
        db.session.commit()
        audit_engine.log(
            action="workforce_identity.account_period_updated",
            user=acting_user,
            target_type="UserAccountLifecycle",
            target_id=record.id,
            details={
                "user_id": user_id,
                "start_date": start_date.isoformat(),
                "expiry_date": expiry_date.isoformat(),
            },
        )
    return user
