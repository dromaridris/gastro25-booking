"""Pharma / educational banner slides."""

from app.extensions import db


def _utcnow():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc)


class PharmaBannerSlide(db.Model):
    __tablename__ = "pharma_banner_slides"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    body_html = db.Column(db.Text, nullable=True)
    link_url = db.Column(db.String(500), nullable=True)
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    is_active = db.Column(db.Boolean, nullable=False, default=True, index=True)
    created_at = db.Column(db.DateTime(timezone=True), default=_utcnow, nullable=False)
