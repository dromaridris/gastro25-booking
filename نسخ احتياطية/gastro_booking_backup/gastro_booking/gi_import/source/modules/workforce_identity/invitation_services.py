"""Invitation-based trainee registration — Phase 7E."""

from __future__ import annotations

import secrets
from datetime import date, datetime, timedelta, timezone

from flask import url_for

from app.core.exceptions import NotFoundError, ValidationError
from app.engines import audit_engine, permission_engine
from app.extensions import db
from app.modules.auth.models import User
from app.modules.rbac import services as rbac_services
from app.modules.workforce_identity.constants import (
    DEFAULT_INVITATION_VALIDITY_DAYS,
    INVITATION_ACCEPTED,
    INVITATION_EXPIRED,
    INVITATION_PENDING,
    INVITATION_REVOKED,
    STATUS_ACTIVE,
    TRAINING_ROLE_CODES,
)
from app.modules.workforce_identity import lifecycle_services
from app.modules.workforce_identity.models import TrainingInvitation


def _require(user, permission: str) -> None:
    permission_engine.require(user, permission)


def _generate_token() -> str:
    return secrets.token_urlsafe(32)


def create_invitation(
    acting_user,
    *,
    role_code: str,
    start_date: date,
    expiry_date: date,
    rotation_label: str | None = None,
    email: str | None = None,
    maximum_validity_days: int = DEFAULT_INVITATION_VALIDITY_DAYS,
) -> TrainingInvitation:
    _require(acting_user, "workforce_identity:invite_manage")
    if role_code not in TRAINING_ROLE_CODES:
        raise ValidationError(
            f"Role '{role_code}' is not eligible for invitation-based registration."
        )
    if expiry_date < start_date:
        raise ValidationError("Account expiry must be on or after start date.")
    role = rbac_services.get_role_by_code(role_code)
    now = datetime.now(timezone.utc)
    invitation = TrainingInvitation(
        email=email.lower().strip() if email else None,
        role_id=role.id,
        rotation_label=rotation_label,
        start_date=start_date,
        expiry_date=expiry_date,
        token=_generate_token(),
        token_expires_at=now + timedelta(days=maximum_validity_days),
        maximum_validity_days=maximum_validity_days,
        status=INVITATION_PENDING,
        department_id=getattr(acting_user, "department_id", 1) or 1,
        created_by_id=acting_user.id,
    )
    db.session.add(invitation)
    db.session.commit()
    audit_engine.log(
        action="workforce_identity.invitation_created",
        user=acting_user,
        target_type="TrainingInvitation",
        target_id=invitation.id,
        details={"role": role_code, "rotation": rotation_label},
    )
    return invitation


def registration_url(invitation: TrainingInvitation, *, external: bool = False) -> str:
    return url_for("workforce_identity.register", token=invitation.token, _external=external)


def get_invitation_by_token(token: str) -> TrainingInvitation:
    invitation = TrainingInvitation.query.filter_by(token=token, is_archived=False).first()
    if invitation is None:
        raise NotFoundError("Invitation not found.")
    return invitation


def _aware(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def validate_invitation_token(token: str) -> TrainingInvitation:
    invitation = get_invitation_by_token(token)
    now = datetime.now(timezone.utc)
    if invitation.status == INVITATION_REVOKED:
        raise ValidationError("This invitation has been revoked.")
    if invitation.status == INVITATION_ACCEPTED:
        raise ValidationError("This invitation has already been used.")
    if invitation.token_expires_at and _aware(invitation.token_expires_at) < now:
        invitation.status = INVITATION_EXPIRED
        db.session.commit()
        raise ValidationError("This invitation link has expired.")
    if not invitation.is_usable():
        raise ValidationError("This invitation is no longer valid.")
    return invitation


def accept_invitation(
    token: str,
    *,
    full_name: str,
    email: str,
    password: str,
) -> User:
    invitation = validate_invitation_token(token)
    email_normalized = email.lower().strip()
    if invitation.email and invitation.email != email_normalized:
        raise ValidationError("Email does not match the invitation.")
    if User.query.filter_by(email=email_normalized).first():
        raise ValidationError("An account with this email already exists.")
    if not password or len(password) < 8:
        raise ValidationError("Password must be at least 8 characters.")

    user = User(
        full_name=full_name.strip(),
        email=email_normalized,
        role_id=invitation.role_id,
        department_id=invitation.department_id,
    )
    user.set_password(password)
    db.session.add(user)
    db.session.flush()

    lifecycle_services.create_lifecycle_from_invitation(
        user_id=user.id,
        start_date=invitation.start_date,
        expiry_date=invitation.expiry_date,
        rotation_label=invitation.rotation_label,
        invitation_id=invitation.id,
    )

    invitation.status = INVITATION_ACCEPTED
    invitation.accepted_at = datetime.now(timezone.utc)
    invitation.accepted_user_id = user.id
    db.session.commit()

    audit_engine.log(
        action="workforce_identity.invitation_accepted",
        user=user,
        target_type="TrainingInvitation",
        target_id=invitation.id,
        details={"email": user.email},
    )
    return user


def revoke_invitation(acting_user, invitation_id: int, *, reason: str | None = None) -> TrainingInvitation:
    _require(acting_user, "workforce_identity:invite_manage")
    invitation = TrainingInvitation.query.get(invitation_id)
    if invitation is None or invitation.is_archived:
        raise NotFoundError("Invitation not found.")
    if invitation.status == INVITATION_ACCEPTED:
        raise ValidationError("Cannot revoke an accepted invitation.")
    invitation.status = INVITATION_REVOKED
    invitation.revoked_at = datetime.now(timezone.utc)
    invitation.revoked_by_id = acting_user.id
    db.session.commit()
    audit_engine.log(
        action="workforce_identity.invitation_revoked",
        user=acting_user,
        target_type="TrainingInvitation",
        target_id=invitation.id,
        details={"reason": reason},
    )
    return invitation


def list_invitations(acting_user, *, status: str | None = None) -> list[TrainingInvitation]:
    _require(acting_user, "workforce_identity:invite_manage")
    query = TrainingInvitation.query.filter_by(is_archived=False)
    if status:
        query = query.filter_by(status=status)
    return query.order_by(TrainingInvitation.created_at.desc()).all()
