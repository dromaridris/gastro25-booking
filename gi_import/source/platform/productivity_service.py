"""User productivity preferences — favorites and recent pages."""

import json

from app.extensions import db


class UserProductivityPrefs(db.Model):
    __tablename__ = "user_productivity_prefs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, unique=True, index=True)
    favorites_json = db.Column(db.Text, nullable=False, default="[]")
    recent_pages_json = db.Column(db.Text, nullable=False, default="[]")
    updated_at = db.Column(db.DateTime(timezone=True), nullable=True)

    user = db.relationship("User", foreign_keys=[user_id])


def get_prefs(user_id: int) -> UserProductivityPrefs:
    prefs = UserProductivityPrefs.query.filter_by(user_id=user_id).first()
    if prefs is None:
        prefs = UserProductivityPrefs(user_id=user_id)
        db.session.add(prefs)
        db.session.commit()
    return prefs


def sync_prefs(user_id: int, *, favorites: list | None = None, recent_pages: list | None = None) -> dict:
    from app.core.base_model import utcnow
    prefs = get_prefs(user_id)
    if favorites is not None:
        prefs.favorites_json = json.dumps(favorites[:20])
    if recent_pages is not None:
        prefs.recent_pages_json = json.dumps(recent_pages[:15])
    prefs.updated_at = utcnow()
    db.session.commit()
    return prefs_to_dict(prefs)


def prefs_to_dict(prefs: UserProductivityPrefs) -> dict:
    return {
        "favorites": json.loads(prefs.favorites_json or "[]"),
        "recent_pages": json.loads(prefs.recent_pages_json or "[]"),
    }
