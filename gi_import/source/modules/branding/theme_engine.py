"""Theme engine — CSS variables for light, dark and system modes."""

from __future__ import annotations

import colorsys


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    hex_color = hex_color.lstrip("#")
    return int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)


def _rgb_to_hex(r: int, g: int, b: int) -> str:
    return f"#{r:02x}{g:02x}{b:02x}"


def _adjust_lightness(hex_color: str, factor: float) -> str:
    r, g, b = _hex_to_rgb(hex_color)
    h, l, s = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
    l = max(0.0, min(1.0, l * factor))
    nr, ng, nb = colorsys.hls_to_rgb(h, l, s)
    return _rgb_to_hex(int(nr * 255), int(ng * 255), int(nb * 255))


def _contrast_text(bg_hex: str, light: str = "#ffffff", dark: str = "#1a1a1a") -> str:
    r, g, b = _hex_to_rgb(bg_hex)
    luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
    return light if luminance < 0.55 else dark


def build_theme_variables(
    primary: str,
    secondary: str,
    accent: str,
    *,
    mode: str = "light",
) -> dict[str, str]:
    """Build semantic CSS variable map for the requested colour scheme."""
    if mode == "dark":
        bg = "#0f1419"
        surface = "#1a2332"
        text = "#e8edf2"
        muted = "#9aa8b8"
        nav_bg = _adjust_lightness(primary, 0.55)
        nav_text = _contrast_text(nav_bg)
        btn_primary = accent
        btn_primary_text = _contrast_text(accent)
    else:
        bg = "#f7f9fb"
        surface = "#ffffff"
        text = "#1a2332"
        muted = "#5c6b7a"
        nav_bg = primary
        nav_text = _contrast_text(primary)
        btn_primary = primary
        btn_primary_text = _contrast_text(primary)

    return {
        "--gi-color-primary": primary,
        "--gi-color-secondary": secondary,
        "--gi-color-accent": accent,
        "--gi-color-bg": bg,
        "--gi-color-surface": surface,
        "--gi-color-text": text,
        "--gi-color-muted": muted,
        "--gi-color-nav-bg": nav_bg,
        "--gi-color-nav-text": nav_text,
        "--gi-color-btn-primary": btn_primary,
        "--gi-color-btn-primary-text": btn_primary_text,
        "--gi-color-card-border": _adjust_lightness(secondary, 1.15 if mode != "dark" else 0.85),
        "--gi-color-footer-bg": _adjust_lightness(bg, 0.96 if mode != "dark" else 1.05),
        "--gi-color-footer-text": muted,
        "--gi-color-link": secondary if mode != "dark" else accent,
        "--gi-color-focus-ring": accent,
        # Bootstrap 5 semantic bridge — stops default blue leaking into UI chrome
        "--bs-primary": btn_primary,
        "--bs-primary-rgb": f"{_hex_to_rgb(btn_primary)[0]}, {_hex_to_rgb(btn_primary)[1]}, {_hex_to_rgb(btn_primary)[2]}",
        "--bs-link-color": secondary if mode != "dark" else accent,
        "--bs-link-hover-color": primary,
    }


def render_theme_css(
    primary: str,
    secondary: str,
    accent: str,
    *,
    theme_mode: str = "system",
) -> str:
    """Render inline CSS setting variables for light, dark and system preference."""
    light_vars = build_theme_variables(primary, secondary, accent, mode="light")
    dark_vars = build_theme_variables(primary, secondary, accent, mode="dark")

    def _block(selector: str, variables: dict[str, str]) -> str:
        lines = [f"{selector} {{"]
        for key, value in variables.items():
            lines.append(f"  {key}: {value};")
        lines.append("}")
        return "\n".join(lines)

    parts = [
        _block(":root, [data-theme-mode='light']", light_vars),
        _block("[data-theme-mode='dark']", dark_vars),
        "@media (prefers-color-scheme: dark) {",
        "  :root[data-theme-mode='system'] {",
    ]
    for key, value in dark_vars.items():
        parts.append(f"    {key}: {value};")
    parts.append("  }")
    parts.append("}")
    parts.append("@media (prefers-color-scheme: light) {")
    parts.append("  :root[data-theme-mode='system'] {")
    for key, value in light_vars.items():
        parts.append(f"    {key}: {value};")
    parts.append("  }")
    parts.append("}")
    return "\n".join(parts)
