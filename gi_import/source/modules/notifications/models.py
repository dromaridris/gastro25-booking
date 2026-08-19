"""In-app user notifications."""

from app.core.base_model import BaseModel, utcnow
from app.extensions import db


class UserNotification(BaseModel):
    __tablename__ = "user_notifications"

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    body = db.Column(db.Text, nullable=True)
    category = db.Column(db.String(50), nullable=False, default="general", index=True)
    link_url = db.Column(db.String(500), nullable=True)
    is_read = db.Column(db.Boolean, nullable=False, default=False, index=True)
    read_at = db.Column(db.DateTime(timezone=True), nullable=True)
    source_module = db.Column(db.String(50), nullable=True, index=True)
    source_id = db.Column(db.Integer, nullable=True)

    user = db.relationship("User", foreign_keys=[user_id])
