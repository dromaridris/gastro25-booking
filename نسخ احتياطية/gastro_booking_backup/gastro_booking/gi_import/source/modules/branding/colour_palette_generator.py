"""Extract a professional colour palette from an uploaded hospital logo."""

from __future__ import annotations

import io
from collections import Counter

from PIL import Image

from app.modules.branding.constants import DEFAULT_ACCENT, DEFAULT_PRIMARY, DEFAULT_SECONDARY


def _normalize_hex(r: int, g: int, b: int) -> str:
    return f"#{r:02x}{g:02x}{b:02x}"


def _is_neutral(r: int, g: int, b: int) -> bool:
    spread = max(r, g, b) - min(r, g, b)
    brightness = (r + g + b) / 3
    return spread < 28 or brightness > 235 or brightness < 18


def _saturation(r: int, g: int, b: int) -> float:
    mx, mn = max(r, g, b), min(r, g, b)
    if mx == 0:
        return 0.0
    return (mx - mn) / mx


def generate_palette_from_image(image_bytes: bytes) -> dict[str, str]:
    """
    Derive primary, secondary and accent colours from logo pixels.
    Falls back to professional defaults when extraction is inconclusive.
    """
    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
    except Exception:
        return _default_palette()

    img = img.resize((120, 120))
    pixels = list(img.getdata())
    counts: Counter[tuple[int, int, int]] = Counter()

    for r, g, b, a in pixels:
        if a < 128:
            continue
        if _is_neutral(r, g, b):
            continue
        bucket = (r // 8 * 8, g // 8 * 8, b // 8 * 8)
        counts[bucket] += 1

    if not counts:
        return _default_palette()

    ranked = sorted(counts.items(), key=lambda item: (-item[1], -_saturation(*item[0])))
    primary = _normalize_hex(*ranked[0][0])

    secondary = primary
    accent = primary
    for rgb, _ in ranked[1:]:
        candidate = _normalize_hex(*rgb)
        if candidate != primary:
            secondary = candidate
            break
    for rgb, _ in ranked[2:]:
        candidate = _normalize_hex(*rgb)
        if candidate not in (primary, secondary):
            accent = candidate
            break

    return {"primary": primary, "secondary": secondary, "accent": accent}


def _default_palette() -> dict[str, str]:
    return {
        "primary": DEFAULT_PRIMARY,
        "secondary": DEFAULT_SECONDARY,
        "accent": DEFAULT_ACCENT,
    }


def parse_manual_color(value: str | None, fallback: str) -> str:
    if not value:
        return fallback
    value = value.strip()
    if len(value) == 7 and value.startswith("#"):
        try:
            int(value[1:], 16)
            return value.lower()
        except ValueError:
            pass
    return fallback
