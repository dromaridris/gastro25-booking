"""Cached branding context — theme generation occurs once per config revision."""

from __future__ import annotations

from app.modules.branding import branding_service
from app.modules.branding_integration.accessibility import validate_branding_contrast
from app.modules.branding_integration.chart_theme import chart_palette_for_branding
from app.modules.branding_integration.print_branding import build_print_css


_cache: dict | None = None
_cache_key: tuple | None = None


def _cache_revision() -> tuple:
    config = branding_service.get_config()
    if config is None:
        return (None,)
    return (
        config.updated_at.isoformat() if config.updated_at else None,
        config.hospital_name,
        config.primary_color,
        config.secondary_color,
        config.accent_color,
        config.theme_mode,
        config.hospital_logo_key,
        config.department_logo_key,
        config.slogan,
    )


def invalidate_branding_cache() -> None:
    global _cache, _cache_key
    _cache = None
    _cache_key = None


def get_cached_template_context() -> dict:
    global _cache, _cache_key
    key = _cache_revision()
    if _cache is not None and _cache_key == key:
        return _cache

    ctx = branding_service.get_template_context()
    branding = ctx["branding"]
    ctx["print_css"] = build_print_css(
        branding.primary_color,
        branding.secondary_color,
        branding.accent_color,
    )
    ctx["chart_palette"] = chart_palette_for_branding(branding)
    ctx["accessibility_warnings"] = validate_branding_contrast(
        branding.primary_color,
        branding.secondary_color,
        branding.accent_color,
    )
    from app.modules.branding_integration.favicon_service import favicon_url

    ctx["favicon_url"] = favicon_url()
    _cache = ctx
    _cache_key = key
    return ctx
