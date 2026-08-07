"""
Database-driven RBAC schema.

Replaces the old app/core/permissions.py (a hardcoded Python dict of
role -> permission set). Nothing about WHICH roles exist, WHICH
permissions exist, or WHICH role has WHICH permission lives in Python
anymore — it's all rows in these three tables. Creating a new role,
retiring one, or reassigning permissions is a database write (via
app/modules/rbac/services.py or a future admin UI in Sprint 1B), never a
code change or redeploy.

What's NOT eliminated, and can't be: application code that gates an
action still has to say *which* permission it's checking —
`permission_engine.require(user, "user:manage")` somewhere in
users/services.py. That permission code is a string literal in code
because the code needs to know which check applies to which action. What
this schema eliminates is the ROLE -> PERMISSION mapping and the
enumeration of roles/permissions themselves being Python — those are
pure data now.

Role and Permission are deliberately plain db.Model, not BaseModel
subclasses: they aren't department-scoped (a role like "Consultant"
applies across the whole system, not to one department), and archiving
a role is a distinct, more consequential operation than archiving a
clinical record — handled here via `is_active` instead, so a role can be
retired without ever breaking historical FK references from users who
held it.
"""

from datetime import datetime, timezone

from sqlalchemy.ext.associationproxy import association_proxy

from app.extensions import db


def _utcnow():
    return datetime.now(timezone.utc)


class Role(db.Model):
    __tablename__ = "roles"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), nullable=False, unique=True, index=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255), nullable=True)

    # Protects the seeded/built-in roles from deletion via a future admin
    # UI — that UI should refuse to delete a row where is_system=True,
    # offering deactivation (is_active=False) instead.
    is_system = db.Column(db.Boolean, default=False, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    created_at = db.Column(db.DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    permission_links = db.relationship(
        "RolePermission", back_populates="role", cascade="all, delete-orphan"
    )
    # role.permissions -> list[Permission], without exposing the RolePermission
    # rows themselves to callers that just want "what can this role do".
    permissions = association_proxy("permission_links", "permission")

    def has_permission(self, permission_code: str) -> bool:
        return any(p.code == permission_code for p in self.permissions)

    def __repr__(self):
        return f"<Role {self.code}>"


class Permission(db.Model):
    __tablename__ = "permissions"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(100), nullable=False, unique=True, index=True)
    name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.String(255), nullable=True)

    # Groups permissions for a future admin UI (e.g. checkboxes grouped
    # by "Users", "Knowledge Library", "Research"). Purely descriptive —
    # nothing in the engine branches on this.
    category = db.Column(db.String(50), nullable=True, index=True)

    created_at = db.Column(db.DateTime(timezone=True), default=_utcnow, nullable=False)

    def __repr__(self):
        return f"<Permission {self.code}>"


class RolePermission(db.Model):
    """
    The role<->permission mapping, as its own table (not a bare
    association table) so grants are themselves auditable: who granted
    this permission to this role, and when. That matters for a system
    where "who can edit the Knowledge Library" is a governance question,
    not just an implementation detail.
    """

    __tablename__ = "role_permissions"
    __table_args__ = (
        db.UniqueConstraint("role_id", "permission_id", name="uq_role_permission"),
    )

    id = db.Column(db.Integer, primary_key=True)
    role_id = db.Column(db.Integer, db.ForeignKey("roles.id"), nullable=False, index=True)
    permission_id = db.Column(
        db.Integer, db.ForeignKey("permissions.id"), nullable=False, index=True
    )
    granted_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=_utcnow, nullable=False)

    role = db.relationship("Role", back_populates="permission_links")
    permission = db.relationship("Permission")
