from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from app.core.base_model import BaseModel
from app.extensions import db


class User(BaseModel, UserMixin):
    """
    Inherits BaseModel: department_id (which department this user belongs
    to), audit fields, and archive support (deactivating a user account is
    an archive operation — an account is never deleted, since it may be
    referenced as created_by_id / archived_by_id / report author elsewhere).
    """

    __tablename__ = "users"

    full_name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(255), nullable=False, unique=True, index=True)
    password_hash = db.Column(db.String(255), nullable=False)

    # Role is a foreign key to the roles table (app/modules/rbac/models.py)
    # — NOT a hardcoded string. This is the ONLY place a user's role
    # assignment is stored; permission checks always go through
    # app.engines.permission_engine (check()/require()), never a direct
    # role-code comparison scattered elsewhere in the app.
    role_id = db.Column(db.Integer, db.ForeignKey("roles.id"), nullable=False)
    role = db.relationship("Role")

    is_active_account = db.Column(db.Boolean, default=True, nullable=False)

    # Super Administrator flag. Deliberately ORTHOGONAL to the role system:
    # a role's access is an enumerated set of permission grants (see
    # app/modules/rbac/), which means a role only has access to a NEW
    # permission a future module introduces if someone remembers to grant
    # it. is_superuser bypasses the permission check entirely (see
    # app/engines/permission_engine.py) — a Super Administrator's access
    # is guaranteed for every permission that exists today AND every one
    # a future sprint introduces, with no seed-data update required.
    # Bootstrapped via scripts/bootstrap_superadmin.py, guarded there
    # against silently minting extra privileged accounts.
    is_superuser = db.Column(db.Boolean, default=False, nullable=False)

    # Sprint 2A: optional per-user cap on how many appointments this
    # user may CREATE per calendar day. NULL = unlimited. Deliberately
    # not a stored/decrementing counter — see
    # app/modules/appointments/services.py's _enforce_daily_limit for why
    # (computed on demand from appointments.created_at, so it "resets"
    # automatically with no scheduled job needed). Editing, rescheduling,
    # checking in, or cancelling an existing appointment never counts
    # against this — only the creation action does.
    daily_appointment_limit = db.Column(db.Integer, nullable=True)

    # Sprint 2A: whether this user may be selected as an appointment
    # provider. Deliberately a dedicated flag, NOT derived from
    # report:draft/report:sign or any other permission -- "can this
    # person sign a report" and "does this person see patients on a
    # bookable schedule" are different questions, and coupling them
    # meant a role's permissions silently controlled scheduling
    # eligibility. Same orthogonal-flag pattern as is_superuser: set
    # explicitly per account by an administrator
    # (users/services.py::set_provider_flag), not inferred from role.
    is_provider = db.Column(db.Boolean, default=False, nullable=False)

    # Training supervision — consultant responsible for this trainee / house officer.
    clinical_supervisor_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    clinical_supervisor = db.relationship(
        "User",
        foreign_keys=[clinical_supervisor_id],
        remote_side="User.id",
    )

    def set_password(self, raw_password: str) -> None:
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password: str) -> bool:
        return check_password_hash(self.password_hash, raw_password)

    @property
    def is_active(self) -> bool:
        # Flask-Login uses this to block login for archived/deactivated
        # accounts, without deleting the row (per the archive-not-delete rule).
        return self.is_active_account and not self.is_archived

    def __repr__(self):
        role_code = self.role.code if self.role else None
        return f"<User {self.email} ({role_code})>"
