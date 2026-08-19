"""Branding configuration model — Sprint 8A."""

from datetime import datetime, timezone

from app.extensions import db


def _utcnow():
    return datetime.now(timezone.utc)


class BrandingConfig(db.Model):
    """
    Singleton installation branding. One row (id=1) per deployment instance.
    Hospital branding owns the interface; platform identity stays in constants.
    """

    __tablename__ = "branding_configs"

    id = db.Column(db.Integer, primary_key=True)
    hospital_name = db.Column(db.String(200), nullable=False, default="")
    department_name = db.Column(db.String(200), nullable=False, default="")
    hospital_logo_key = db.Column(db.String(255), nullable=True)
    department_logo_key = db.Column(db.String(255), nullable=True)
    primary_color = db.Column(db.String(7), nullable=False, default="#1a5276")
    secondary_color = db.Column(db.String(7), nullable=False, default="#2874a6")
    accent_color = db.Column(db.String(7), nullable=False, default="#3498db")
    slogan = db.Column(db.String(255), nullable=True)
    theme_mode = db.Column(db.String(10), nullable=False, default="system")
    setup_complete = db.Column(db.Boolean, nullable=False, default=False)
    pharma_banner_enabled = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    def display_title(self) -> str:
        parts = [p for p in (self.hospital_name, self.department_name) if p]
        return " — ".join(parts) if parts else PLATFORM_FALLBACK_TITLE


PLATFORM_FALLBACK_TITLE = "Clinical Platform"
