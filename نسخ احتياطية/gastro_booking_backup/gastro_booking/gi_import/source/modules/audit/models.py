"""
Audit log storage.

Deliberately NOT a BaseModel subclass. BaseModel gives you archive/restore
and updated_at — an audit log must never be editable or archivable after
the fact, or it stops being trustworthy as an audit trail. This model has
create-only semantics: the service layer (AuditEngine, app/engines/audit_engine.py)
only ever INSERTs; nothing in this codebase should ever UPDATE or DELETE
a row here. There is deliberately no update()/archive() method on this
class, unlike every BaseModel subclass.
"""

import json

from app.extensions import db
from app.core.base_model import utcnow


class AuditLog(db.Model):
    __tablename__ = "audit_logs"

    id = db.Column(db.Integer, primary_key=True)

    # Scoping, same convention as BaseModel, but no FK-enforced default
    # here — audit logs must still be writable even in an edge case where
    # department resolution fails, so this stays nullable rather than
    # blocking the log write.
    department_id = db.Column(db.Integer, db.ForeignKey("departments.id"), nullable=True)

    # Nullable: some events (e.g. a failed login for an email that
    # doesn't exist) have no authenticated user to attribute the action to.
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    # Dotted, namespaced action strings: "auth.login_success",
    # "auth.login_failed", "auth.logout", "user.created", "user.updated",
    # "user.role_changed", "user.deactivated", "user.reactivated",
    # "permission.denied". Namespacing by module keeps this greppable as
    # more modules add their own actions later.
    action = db.Column(db.String(100), nullable=False, index=True)

    target_type = db.Column(db.String(100), nullable=True)
    target_id = db.Column(db.Integer, nullable=True)

    # Stored as a JSON string rather than JSONB — keeps this table
    # portable between the SQLite unit-test engine and Postgres, per the
    # "must remain fully PostgreSQL-compatible, never SQLite-specific"
    # rule (JSONB has no SQLite equivalent; TEXT does).
    details_json = db.Column(db.Text, nullable=True)

    ip_address = db.Column(db.String(45), nullable=True)  # IPv6-safe length

    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False, index=True)

    @property
    def details(self) -> dict:
        if not self.details_json:
            return {}
        return json.loads(self.details_json)

    @details.setter
    def details(self, value: dict) -> None:
        self.details_json = json.dumps(value) if value else None

    def __repr__(self):
        return f"<AuditLog {self.action} user_id={self.user_id} at={self.created_at}>"
