"""
Small, composable mixins. BaseModel already includes audit + archive
fields for every table. These are for behavior that only SOME tables need,
so we don't bloat every table with columns it will never use.
"""

from app.extensions import db


class VersionedMixin:
    """
    For tables that need explicit version history rather than just
    updated_at overwriting the previous value — this is what the
    Knowledge Library (guideline documents) will need, since guideline
    version history must always be preserved per project rules.

    Usage pattern for a future model:
        class GuidelineVersion(BaseModel, VersionedMixin):
            ...
    The convention: never UPDATE a versioned row's content in place.
    Insert a new row with version_number + 1 and supersedes_id pointing
    at the previous row. This mixin only supplies the columns; the
    service layer enforces the insert-not-update rule.
    """

    version_number = db.Column(db.Integer, nullable=False, default=1)
    supersedes_id = db.Column(db.Integer, nullable=True)
    is_current_version = db.Column(db.Boolean, default=True, nullable=False)
