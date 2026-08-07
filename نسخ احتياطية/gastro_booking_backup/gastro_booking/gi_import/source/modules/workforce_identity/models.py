"""Phase 7E — Workforce Identity & Duty Management models."""

from __future__ import annotations

from datetime import date, datetime, timezone

from app.core.base_model import BaseModel
from app.extensions import db


class UserAccountLifecycle(BaseModel):
    """Time-limited training account lifecycle — identity preserved after expiry."""

    __tablename__ = "user_account_lifecycles"

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, unique=True, index=True)
    start_date = db.Column(db.Date, nullable=False)
    expiry_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), nullable=False, default="pending", index=True)
    rotation_label = db.Column(db.String(120), nullable=True)
    invitation_id = db.Column(db.Integer, db.ForeignKey("training_invitations.id"), nullable=True, index=True)
    notes = db.Column(db.Text, nullable=True)

    user = db.relationship("User", foreign_keys=[user_id])
    invitation = db.relationship("TrainingInvitation", foreign_keys=[invitation_id])

    def is_login_allowed(self) -> bool:
        if self.status not in ("pending", "active"):
            return False
        if self.expiry_date and self.expiry_date < date.today():
            return False
        return True


class TrainingInvitation(BaseModel):
    """Invitation-based trainee registration — one-time token workflow."""

    __tablename__ = "training_invitations"

    email = db.Column(db.String(255), nullable=True, index=True)
    role_id = db.Column(db.Integer, db.ForeignKey("roles.id"), nullable=False, index=True)
    rotation_label = db.Column(db.String(120), nullable=True)
    start_date = db.Column(db.Date, nullable=False)
    expiry_date = db.Column(db.Date, nullable=False)
    token = db.Column(db.String(64), nullable=False, unique=True, index=True)
    token_expires_at = db.Column(db.DateTime(timezone=True), nullable=False, index=True)
    maximum_validity_days = db.Column(db.Integer, nullable=False, default=14)
    status = db.Column(db.String(20), nullable=False, default="pending", index=True)
    accepted_at = db.Column(db.DateTime(timezone=True), nullable=True)
    accepted_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    revoked_at = db.Column(db.DateTime(timezone=True), nullable=True)
    revoked_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    role = db.relationship("Role", foreign_keys=[role_id])
    created_by = db.relationship("User", foreign_keys="TrainingInvitation.created_by_id")
    accepted_user = db.relationship("User", foreign_keys=[accepted_user_id])
    revoked_by = db.relationship("User", foreign_keys=[revoked_by_id])

    def is_usable(self) -> bool:
        if self.status != "pending":
            return False
        if self.revoked_at is not None:
            return False
        now = datetime.now(timezone.utc)
        expires = self.token_expires_at
        if expires is not None and expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        if expires and expires < now:
            return False
        return True


class DutySwapRequest(BaseModel):
    """Shift swap workflow — schedule changes only after coordinator approval."""

    __tablename__ = "duty_swap_requests"

    requesting_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    replacement_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    original_roster_entry_id = db.Column(
        db.Integer, db.ForeignKey("duty_roster_entries.id"), nullable=False, index=True
    )
    requested_roster_entry_id = db.Column(
        db.Integer, db.ForeignKey("duty_roster_entries.id"), nullable=True, index=True
    )
    reason = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), nullable=False, default="pending", index=True)
    reviewed_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    reviewed_at = db.Column(db.DateTime(timezone=True), nullable=True)
    review_notes = db.Column(db.Text, nullable=True)
    schedule_snapshot_before = db.Column(db.JSON, nullable=True)
    schedule_snapshot_after = db.Column(db.JSON, nullable=True)

    requesting_user = db.relationship("User", foreign_keys=[requesting_user_id])
    replacement_user = db.relationship("User", foreign_keys=[replacement_user_id])
    original_roster_entry = db.relationship("DutyRosterEntry", foreign_keys=[original_roster_entry_id])
    requested_roster_entry = db.relationship("DutyRosterEntry", foreign_keys=[requested_roster_entry_id])
    reviewed_by = db.relationship("User", foreign_keys=[reviewed_by_id])
