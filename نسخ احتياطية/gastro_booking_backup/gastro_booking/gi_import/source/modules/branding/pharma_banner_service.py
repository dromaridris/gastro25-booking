"""Pharma banner slide management."""

from app.core.exceptions import ValidationError
from app.engines import permission_engine
from app.extensions import db
from app.modules.branding.models import BrandingConfig
from app.modules.branding.pharma_banner_models import PharmaBannerSlide


def list_active_slides() -> list[PharmaBannerSlide]:
    config = BrandingConfig.query.get(1)
    if config is None or not config.pharma_banner_enabled:
        return []
    return (
        PharmaBannerSlide.query.filter_by(is_active=True)
        .order_by(PharmaBannerSlide.sort_order, PharmaBannerSlide.id)
        .all()
    )


def list_all_slides(acting_user) -> list[PharmaBannerSlide]:
    permission_engine.require(acting_user, "pharma_banner:manage")
    return PharmaBannerSlide.query.order_by(PharmaBannerSlide.sort_order, PharmaBannerSlide.id).all()


def create_slide(acting_user, *, title: str, body_html: str | None = None,
                 link_url: str | None = None, sort_order: int = 0) -> PharmaBannerSlide:
    permission_engine.require(acting_user, "pharma_banner:manage")
    slide = PharmaBannerSlide(title=title.strip(), body_html=body_html, link_url=link_url, sort_order=sort_order)
    db.session.add(slide)
    db.session.commit()
    return slide


def toggle_banner(acting_user, enabled: bool) -> BrandingConfig:
    permission_engine.require(acting_user, "pharma_banner:manage")
    config = BrandingConfig.query.get(1)
    if config is None:
        raise ValidationError("Branding not configured.")
    config.pharma_banner_enabled = enabled
    db.session.commit()
    return config


def delete_slide(acting_user, slide_id: int) -> None:
    permission_engine.require(acting_user, "pharma_banner:manage")
    slide = PharmaBannerSlide.query.get(slide_id)
    if slide:
        db.session.delete(slide)
        db.session.commit()
