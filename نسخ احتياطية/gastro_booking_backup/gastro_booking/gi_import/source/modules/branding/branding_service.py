"""Branding service — setup wizard, settings and runtime context."""

from __future__ import annotations

from datetime import datetime, timezone

from flask import current_app

from app.core.exceptions import PermissionDeniedError, ValidationError
from app.engines import permission_engine
from app.extensions import db
from app.modules.branding.branding_config import BrandingView, branding_view_from_model, platform_identity
from app.modules.branding.colour_palette_generator import generate_palette_from_image, parse_manual_color
from app.modules.branding.constants import (
    DEFAULT_ACCENT,
    DEFAULT_PRIMARY,
    DEFAULT_SECONDARY,
    THEME_MODES,
    THEME_SYSTEM,
)
from app.modules.branding.logo_manager import logo_url, save_department_logo, save_hospital_logo
from app.modules.branding.models import BrandingConfig
from app.modules.branding.theme_engine import render_theme_css
from app.storage.local_backend import get_storage_backend


def suggest_slogan(hospital_name: str, department_name: str) -> str:
    hospital = hospital_name.strip() or "your hospital"
    department = department_name.strip() or "Gastroenterology"
    return f"Excellence in {department} — advancing patient care at {hospital}"


def get_config() -> BrandingConfig | None:
    return BrandingConfig.query.get(1)


def is_setup_required() -> bool:
    if current_app.config.get("TESTING") and current_app.config.get("BRANDING_SKIP_SETUP_REDIRECT"):
        return False
    config = get_config()
    return config is None or not config.setup_complete


def _get_or_create_config() -> BrandingConfig:
    config = get_config()
    if config is None:
        config = BrandingConfig(id=1)
        db.session.add(config)
        db.session.flush()
    return config


def complete_initial_setup(
    *,
    hospital_name: str,
    department_name: str,
    hospital_logo_file,
    hospital_logo_filename: str | None,
    department_logo_file,
    department_logo_filename: str | None,
    primary_color: str | None,
    secondary_color: str | None,
    accent_color: str | None,
    slogan: str | None,
    accept_suggested_slogan: bool = False,
    suggested_slogan: str | None = None,
) -> BrandingConfig:
    hospital_name = (hospital_name or "").strip()
    department_name = (department_name or "").strip()
    if not hospital_name:
        raise ValidationError("Hospital name is required.")
    if not department_name:
        raise ValidationError("Department name is required.")
    if not hospital_logo_file and not hospital_logo_filename:
        raise ValidationError("Hospital logo is required for initial setup.")

    config = _get_or_create_config()
    config.hospital_name = hospital_name
    config.department_name = department_name

    palette = None
    if hospital_logo_file and hospital_logo_filename:
        config.hospital_logo_key = save_hospital_logo(hospital_logo_file, hospital_logo_filename)
        hospital_logo_file.seek(0)
        palette = generate_palette_from_image(hospital_logo_file.read())

    if department_logo_file and department_logo_filename:
        config.department_logo_key = save_department_logo(
            department_logo_file, department_logo_filename
        )

    if palette:
        config.primary_color = parse_manual_color(primary_color, palette["primary"])
        config.secondary_color = parse_manual_color(secondary_color, palette["secondary"])
        config.accent_color = parse_manual_color(accent_color, palette["accent"])
    else:
        config.primary_color = parse_manual_color(primary_color, DEFAULT_PRIMARY)
        config.secondary_color = parse_manual_color(secondary_color, DEFAULT_SECONDARY)
        config.accent_color = parse_manual_color(accent_color, DEFAULT_ACCENT)

    if accept_suggested_slogan and suggested_slogan:
        config.slogan = suggested_slogan.strip() or None
    elif slogan and slogan.strip():
        config.slogan = slogan.strip()
    else:
        config.slogan = None

    config.theme_mode = THEME_SYSTEM
    config.setup_complete = True
    config.updated_at = datetime.now(timezone.utc)
    db.session.commit()
    from app.modules.branding_integration.cache import invalidate_branding_cache

    invalidate_branding_cache()
    return config


def update_branding(
    acting_user,
    *,
    hospital_name: str,
    department_name: str,
    hospital_logo_file=None,
    hospital_logo_filename: str | None = None,
    department_logo_file=None,
    department_logo_filename: str | None = None,
    remove_department_logo: bool = False,
    primary_color: str | None = None,
    secondary_color: str | None = None,
    accent_color: str | None = None,
    slogan: str | None = None,
    theme_mode: str = THEME_SYSTEM,
) -> BrandingConfig:
    if not permission_engine.check(acting_user, "branding:manage"):
        raise PermissionDeniedError("branding:manage")

    config = _get_or_create_config()
    hospital_name = (hospital_name or "").strip()
    department_name = (department_name or "").strip()
    if not hospital_name or not department_name:
        raise ValidationError("Hospital and department names are required.")

    config.hospital_name = hospital_name
    config.department_name = department_name
    config.primary_color = parse_manual_color(primary_color, config.primary_color)
    config.secondary_color = parse_manual_color(secondary_color, config.secondary_color)
    config.accent_color = parse_manual_color(accent_color, config.accent_color)
    config.slogan = slogan.strip() if slogan and slogan.strip() else None

    if theme_mode not in THEME_MODES:
        raise ValidationError("Invalid theme mode.")
    config.theme_mode = theme_mode

    if hospital_logo_file and hospital_logo_filename:
        config.hospital_logo_key = save_hospital_logo(hospital_logo_file, hospital_logo_filename)

    if remove_department_logo:
        config.department_logo_key = None
    elif department_logo_file and department_logo_filename:
        config.department_logo_key = save_department_logo(
            department_logo_file, department_logo_filename
        )

    config.setup_complete = True
    config.updated_at = datetime.now(timezone.utc)
    db.session.commit()
    from app.modules.branding_integration.cache import invalidate_branding_cache

    invalidate_branding_cache()
    return config


def get_branding_view() -> BrandingView:
    config = get_config()
    return branding_view_from_model(
        config,
        hospital_logo_url=logo_url(config.hospital_logo_key) if config else None,
        department_logo_url=logo_url(config.department_logo_key) if config else None,
    )


def get_template_context() -> dict:
    view = get_branding_view()
    platform = platform_identity()
    theme_css = render_theme_css(
        view.primary_color,
        view.secondary_color,
        view.accent_color,
        theme_mode=view.theme_mode,
    )
    from app.modules.branding.logo_manager import platform_logo_url

    return {
        "branding": view,
        "platform": platform,
        "theme_css": theme_css,
        "platform_logo_url": platform_logo_url(),
        "copyright_year": datetime.now(timezone.utc).year,
    }


def seed_test_branding(
    *,
    hospital_name: str = "Test Hospital",
    department_name: str = "Gastroenterology",
) -> BrandingConfig:
    """Used by test fixtures — marks setup complete with defaults."""
    import os
    from io import BytesIO

    config = _get_or_create_config()
    config.hospital_name = hospital_name
    config.department_name = department_name
    config.primary_color = DEFAULT_PRIMARY
    config.secondary_color = DEFAULT_SECONDARY
    config.accent_color = DEFAULT_ACCENT
    config.theme_mode = THEME_SYSTEM
    config.setup_complete = True

    if not config.hospital_logo_key:
        static_logo = os.path.join(
            current_app.root_path,
            "static",
            "platform",
            "gastrointelligence.svg",
        )
        if os.path.isfile(static_logo):
            with open(static_logo, "rb") as logo_file:
                config.hospital_logo_key = save_hospital_logo(
                    BytesIO(logo_file.read()),
                    "gastrointelligence.svg",
                )

    db.session.commit()
    return config


def read_logo_bytes(storage_key: str | None) -> bytes | None:
    if not storage_key:
        return None
    backend = get_storage_backend(current_app.config)
    if not backend.exists(storage_key):
        return None
    return backend.read(storage_key)


def preview_palette_from_upload(file_obj) -> dict[str, str]:
    data = file_obj.read()
    file_obj.seek(0)
    return generate_palette_from_image(data)
