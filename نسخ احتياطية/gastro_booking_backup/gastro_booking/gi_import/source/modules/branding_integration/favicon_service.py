"""Favicon generation from hospital logo."""

from __future__ import annotations

import io
import os

from flask import current_app, has_request_context, url_for
from PIL import Image

from app.modules.branding import branding_service

_FAVICON_CACHE: bytes | None = None
_FAVICON_KEY: str | None = None


def _platform_favicon_bytes() -> bytes:
    static_path = os.path.join(current_app.root_path, "static", "platform", "favicon.png")
    if os.path.isfile(static_path):
        with open(static_path, "rb") as f:
            return f.read()
    buf = io.BytesIO()
    Image.new("RGB", (32, 32), (26, 82, 118)).save(buf, format="PNG")
    return buf.getvalue()


def generate_favicon_bytes() -> bytes:
    global _FAVICON_CACHE, _FAVICON_KEY
    config = branding_service.get_config()
    logo_key = config.hospital_logo_key if config else None
    if _FAVICON_CACHE is not None and _FAVICON_KEY == logo_key:
        return _FAVICON_CACHE

    raw = branding_service.read_logo_bytes(logo_key) if logo_key else None
    if raw:
        try:
            img = Image.open(io.BytesIO(raw)).convert("RGBA")
            img.thumbnail((32, 32), Image.Resampling.LANCZOS)
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            data = buf.getvalue()
        except Exception:
            data = _platform_favicon_bytes()
    else:
        data = _platform_favicon_bytes()

    _FAVICON_CACHE = data
    _FAVICON_KEY = logo_key
    return data


def favicon_url() -> str:
    if not has_request_context():
        return "/favicon.ico"
    return url_for("branding_integration.favicon")
