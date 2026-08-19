"""Chart colour palette derived from the active Theme Engine variables."""

from __future__ import annotations

from app.modules.branding.theme_engine import build_theme_variables


def build_chart_palette(primary: str, secondary: str, accent: str, *, mode: str = "light") -> dict:
    """Return a Chart.js-compatible palette that follows hospital branding."""
    vars_ = build_theme_variables(primary, secondary, accent, mode=mode)
    return {
        "primary": vars_["--gi-color-primary"],
        "secondary": vars_["--gi-color-secondary"],
        "accent": vars_["--gi-color-accent"],
        "background": vars_["--gi-color-bg"],
        "surface": vars_["--gi-color-surface"],
        "text": vars_["--gi-color-text"],
        "muted": vars_["--gi-color-muted"],
        "series": [
            vars_["--gi-color-primary"],
            vars_["--gi-color-secondary"],
            vars_["--gi-color-accent"],
            vars_["--gi-color-secondary"],
            vars_["--gi-color-primary"],
        ],
        "grid": vars_["--gi-color-card-border"],
    }


def chart_palette_for_branding(branding_view) -> dict:
    mode = "dark" if branding_view.theme_mode == "dark" else "light"
    return build_chart_palette(
        branding_view.primary_color,
        branding_view.secondary_color,
        branding_view.accent_color,
        mode=mode,
    )


def chart_palette_json(branding_view) -> str:
    import json

    return json.dumps(chart_palette_for_branding(branding_view))
