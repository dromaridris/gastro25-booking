"""Archive policy and archived asset registry."""

from app.core.base_model import BaseModel, utcnow
from app.extensions import db


class ArchivePolicy(BaseModel):
    __tablename__ = "archive_policies"

    name = db.Column(db.String(120), nullable=False, unique=True)
    resource_type = db.Column(db.String(50), nullable=False, index=True)
    retention_days = db.Column(db.Integer, nullable=False, default=365)
    auto_archive = db.Column(db.Boolean, nullable=False, default=False)
    notes = db.Column(db.Text, nullable=True)


class ArchivedAsset(BaseModel):
    __tablename__ = "archived_assets"

    policy_id = db.Column(db.Integer, db.ForeignKey("archive_policies.id"), nullable=True, index=True)
    resource_type = db.Column(db.String(50), nullable=False, index=True)
    resource_id = db.Column(db.Integer, nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    archived_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, index=True)
    archived_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    storage_key = db.Column(db.String(255), nullable=True)
    metadata_json = db.Column(db.Text, nullable=True)
    restored_at = db.Column(db.DateTime(timezone=True), nullable=True)

    policy = db.relationship("ArchivePolicy", foreign_keys=[policy_id])
    archived_by = db.relationship("User", foreign_keys=[archived_by_id])

    __table_args__ = (
        db.Index("ix_archived_asset_resource", "resource_type", "resource_id"),
    )
