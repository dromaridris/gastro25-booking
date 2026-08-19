"""Data export/import job tracking."""

from app.core.base_model import BaseModel, utcnow
from app.extensions import db

JOB_EXPORT = "export"
JOB_IMPORT = "import"
JOB_PENDING = "pending"
JOB_RUNNING = "running"
JOB_COMPLETED = "completed"
JOB_FAILED = "failed"


class DataExchangeJob(BaseModel):
    __tablename__ = "data_exchange_jobs"

    job_type = db.Column(db.String(20), nullable=False, index=True)
    format = db.Column(db.String(20), nullable=False, default="csv")
    status = db.Column(db.String(20), nullable=False, default=JOB_PENDING, index=True)
    requested_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    started_at = db.Column(db.DateTime(timezone=True), nullable=True)
    completed_at = db.Column(db.DateTime(timezone=True), nullable=True)
    storage_key = db.Column(db.String(255), nullable=True)
    record_count = db.Column(db.Integer, nullable=True)
    error_message = db.Column(db.Text, nullable=True)
    filters_json = db.Column(db.Text, nullable=True)

    requested_by = db.relationship("User", foreign_keys=[requested_by_id])
