"""Education activities — portfolio integration via source reference."""

from app.core.base_model import BaseModel
from app.extensions import db


class EducationActivity(BaseModel):
    __tablename__ = "education_activities"

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    activity_type = db.Column(db.String(50), nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    activity_date = db.Column(db.Date, nullable=False, index=True)
    duration_minutes = db.Column(db.Integer, nullable=True)
    location = db.Column(db.String(120), nullable=True)
    supervisor_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    verified = db.Column(db.Boolean, nullable=False, default=False, index=True)

    user = db.relationship("User", foreign_keys=[user_id])
    supervisor = db.relationship("User", foreign_keys=[supervisor_id])
