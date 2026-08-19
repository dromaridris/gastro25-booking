"""Calendar hub — stored events plus aggregated views from other modules."""

from app.core.base_model import BaseModel
from app.extensions import db

EVENT_APPOINTMENT = "appointment"
EVENT_PROCEDURE = "procedure"
EVENT_ROSTER = "roster"
EVENT_EDUCATION = "education"
EVENT_DUTY = "duty"
EVENT_CUSTOM = "custom"


class CalendarEvent(BaseModel):
    __tablename__ = "calendar_events"

    title = db.Column(db.String(200), nullable=False)
    event_type = db.Column(db.String(30), nullable=False, default=EVENT_CUSTOM, index=True)
    start_at = db.Column(db.DateTime(timezone=True), nullable=False, index=True)
    end_at = db.Column(db.DateTime(timezone=True), nullable=True)
    all_day = db.Column(db.Boolean, nullable=False, default=False)
    location = db.Column(db.String(120), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    source_module = db.Column(db.String(50), nullable=True, index=True)
    source_id = db.Column(db.Integer, nullable=True)
    assigned_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)

    assigned_user = db.relationship("User", foreign_keys=[assigned_user_id])
