"""Hospital and department logo storage and URL resolution."""

from __future__ import annotations

import os
import uuid
from typing import BinaryIO

from flask import current_app, url_for, has_request_context

from app.modules.branding.constants import (
    ALLOWED_LOGO_EXTENSIONS,
    LOGO_DEPARTMENT,
    LOGO_HOSPITAL,
    MAX_LOGO_BYTES,
    PLATFORM_LOGO_DIR,
    PLATFORM_LOGO_FILENAME,
    PLATFORM_LOGO_STATIC,
)
from app.storage.local_backend import get_storage_backend


def _extension(filename: str) -> str:
    return os.path.splitext(filename)[1].lower()


def validate_logo_upload(filename: str, file_size: int) -> None:
    from app.core.exceptions import ValidationError

    ext = _extension(filename)
    if ext not in ALLOWED_LOGO_EXTENSIONS:
        raise ValidationError(
            f"Unsupported logo format. Allowed: {', '.join(sorted(ALLOWED_LOGO_EXTENSIONS))}"
        )
    if file_size > MAX_LOGO_BYTES:
        raise ValidationError(f"Logo file too large (max {MAX_LOGO_BYTES // (1024 * 1024)} MB).")


def save_logo(file_obj: BinaryIO, filename: str, logo_type: str) -> str:
    file_obj.seek(0, 2)
    size = file_obj.tell()
    file_obj.seek(0)
    validate_logo_upload(filename, size)

    ext = _extension(filename)
    key = f"branding/{logo_type}/{uuid.uuid4().hex}{ext}"
    backend = get_storage_backend(current_app.config)
    backend.save(key, file_obj)
    return key


def logo_url(storage_key: str | None) -> str | None:
    if not storage_key:
        return None
    backend = get_storage_backend(current_app.config)
    if not backend.exists(storage_key):
        return None
    if not has_request_context():
        return f"/files/{storage_key}"
    return backend.url_for(storage_key)


def save_hospital_logo(file_obj: BinaryIO, filename: str) -> str:
    return save_logo(file_obj, filename, LOGO_HOSPITAL)


def save_department_logo(file_obj: BinaryIO, filename: str) -> str:
    return save_logo(file_obj, filename, LOGO_DEPARTMENT)


def platform_logo_url() -> str:
    """Resolve developer platform logo — project folder first, static fallback."""
    project_logo = os.path.join(PLATFORM_LOGO_DIR, PLATFORM_LOGO_FILENAME)
    if not has_request_context():
        if os.path.isfile(project_logo):
            return "/platform-logo"
        return f"/static/{PLATFORM_LOGO_STATIC}"
    if os.path.isfile(project_logo):
        return url_for("branding.platform_logo")
    return url_for("static", filename=PLATFORM_LOGO_STATIC)
