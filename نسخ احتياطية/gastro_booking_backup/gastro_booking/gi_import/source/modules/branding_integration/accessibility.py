"""WCAG AA contrast validation for hospital branding colours."""

from __future__ import annotations

from dataclasses import dataclass


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    hex_color = hex_color.lstrip("#")
    return int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)


def _relative_luminance(r: int, g: int, b: int) -> float:
    def channel(c: int) -> float:
        s = c / 255
        return s / 12.92 if s <= 0.03928 else ((s + 0.055) / 1.055) ** 2.4

    return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)


def contrast_ratio(foreground: str, background: str) -> float:
    l1 = _relative_luminance(*_hex_to_rgb(foreground))
    l2 = _relative_luminance(*_hex_to_rgb(background))
    lighter, darker = (max(l1, l2), min(l1, l2))
    return (lighter + 0.05) / (darker + 0.05)


def meets_wcag_aa(ratio: float, *, large_text: bool = False) -> bool:
    return ratio >= (3.0 if large_text else 4.5)


@dataclass(frozen=True)
class ContrastWarning:
    label: str
    ratio: float
    required: float
    foreground: str
    background: str


def validate_branding_contrast(
    primary: str,
    secondary: str,
    accent: str,
    *,
    nav_text: str = "#ffffff",
    surface: str = "#ffffff",
    text: str = "#1a2332",
) -> list[ContrastWarning]:
    """Return accessibility warnings for branding colour pairs."""
    checks = [
        ("Primary on white (buttons)", primary, surface),
        ("White text on primary (navigation)", nav_text, primary),
        ("Body text on white", text, surface),
        ("Accent links on white", accent, surface),
        ("Secondary on white", secondary, surface),
    ]
    warnings: list[ContrastWarning] = []
    for label, fg, bg in checks:
        ratio = contrast_ratio(fg, bg)
        required = 4.5
        if not meets_wcag_aa(ratio):
            warnings.append(
                ContrastWarning(label=label, ratio=round(ratio, 2), required=required, foreground=fg, background=bg)
            )
    return warnings
