"""
Abstract base model for every table in the system.

Three architectural rules are enforced here so that no future module can
accidentally skip them:

1. NEVER DELETE CLINICAL DATA -> ArchivableMixin (is_archived, archived_at,
   archived_by_id) instead of a DELETE statement. Every service-layer
   "delete" operation must call .archive(), never db.session.delete().

2. MULTI-DEPARTMENT READINESS -> department_id lives on the base model now.
   Only one department exists today (Gastroenterology), and no query
   currently needs to filter by it — but the column existing from day one
   means adding a second department later is a data-population task, not
   a schema migration touching every table.

3. AUDIT TRAIL -> created_at/updated_at/created_by_id on everything, since
   this is a clinical system and "who changed this and when" must always
   be answerable.
"""

from datetime import datetime, timezone

from app.extensions import db


def utcnow():
    return datetime.now(timezone.utc)


class BaseModel(db.Model):
    __abstract__ = True

    id = db.Column(db.Integer, primary_key=True)

    # Threaded through every table from day one — see module docstring.
    department_id = db.Column(
        db.Integer,
        db.ForeignKey("departments.id"),
        nullable=False,
        default=1,  # DEFAULT_DEPARTMENT_ID (Gastroenterology) until a second exists
        index=True,
    )

    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    # --- Archival, never deletion ---
    is_archived = db.Column(db.Boolean, default=False, nullable=False, index=True)
    archived_at = db.Column(db.DateTime(timezone=True), nullable=True)
    archived_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    archive_reason = db.Column(db.String(255), nullable=True)

    def archive(self, by_user_id: int, reason: str = None):
        """The ONLY sanctioned way to remove a record from active views.
        Never call db.session.delete() on clinical data."""
        self.is_archived = True
        self.archived_at = utcnow()
        self.archived_by_id = by_user_id
        self.archive_reason = reason

    def restore(self):
        self.is_archived = False
        self.archived_at = None
        self.archived_by_id = None
        self.archive_reason = None
