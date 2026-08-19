"""Typed accessors for the singleton branding configuration."""

from __future__ import annotations

from dataclasses import dataclass

from app.modules.branding.constants import (
    DEFAULT_ACCENT,
    DEFAULT_PRIMARY,
    DEFAULT_SECONDARY,
    PLATFORM_NAME,
    PLATFORM_SUPPORT_EMAIL,
    PLATFORM_VERSION,
    THEME_SYSTEM,
)
from app.modules.branding.models import BrandingConfig, PLATFORM_FALLBACK_TITLE


@dataclass(frozen=True)
class PlatformIdentity:
    name: str
    support_email: str
    version: str


@dataclass(frozen=True)
class BrandingView:
    hospital_name: str
    department_name: str
    hospital_logo_url: str | None
    department_logo_url: str | None
    primary_color: str
    secondary_color: str
    accent_color: str
    slogan: str | None
    theme_mode: str
    setup_complete: bool
    display_title: str
    logo_layout: str  # both | hospital | department | text


def platform_identity() -> PlatformIdentity:
    return PlatformIdentity(
        name=PLATFORM_NAME,
        support_email=PLATFORM_SUPPORT_EMAIL,
        version=PLATFORM_VERSION,
    )


def _logo_layout(hospital_url: str | None, department_url: str | None) -> str:
    if hospital_url and department_url:
        return "both"
    if hospital_url:
        return "hospital"
    if department_url:
        return "department"
    return "text"


def branding_view_from_model(
    config: BrandingConfig | None,
    *,
    hospital_logo_url: str | None = None,
    department_logo_url: str | None = None,
) -> BrandingView:
    if config is None:
        return BrandingView(
            hospital_name="",
            department_name="",
            hospital_logo_url=None,
            department_logo_url=None,
            primary_color=DEFAULT_PRIMARY,
            secondary_color=DEFAULT_SECONDARY,
            accent_color=DEFAULT_ACCENT,
            slogan=None,
            theme_mode=THEME_SYSTEM,
            setup_complete=False,
            display_title=PLATFORM_FALLBACK_TITLE,
            logo_layout="text",
        )
    return BrandingView(
        hospital_name=config.hospital_name,
        department_name=config.department_name,
        hospital_logo_url=hospital_logo_url,
        department_logo_url=department_logo_url,
        primary_color=config.primary_color,
        secondary_color=config.secondary_color,
        accent_color=config.accent_color,
        slogan=config.slogan,
        theme_mode=config.theme_mode,
        setup_complete=config.setup_complete,
        display_title=config.display_title(),
        logo_layout=_logo_layout(hospital_logo_url, department_logo_url),
    )
