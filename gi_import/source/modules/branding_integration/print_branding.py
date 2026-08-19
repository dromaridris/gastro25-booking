"""Shared print and PDF branding styles."""

from __future__ import annotations

from app.modules.branding.theme_engine import _contrast_text


def build_print_css(primary: str, secondary: str, accent: str) -> str:
    nav_text = _contrast_text(primary)
    return f"""
.gi-print-body {{
    color: var(--gi-color-text, {primary});
    background: #fff;
}}
.gi-print-header {{
    border-bottom: 2px solid var(--gi-color-primary, {primary});
    padding-bottom: 0.75rem;
    margin-bottom: 1.25rem;
}}
.gi-print-header-logos img {{
    max-height: 52px;
    width: auto;
    object-fit: contain;
    margin-right: 0.75rem;
}}
.gi-print-hospital {{
    font-size: 1.15rem;
    font-weight: 700;
    color: var(--gi-color-primary, {primary});
}}
.gi-print-dept {{
    color: var(--gi-color-secondary, {secondary});
    font-size: 0.95rem;
}}
.gi-print-section h3 {{
    font-size: 1rem;
    border-bottom: 1px solid var(--gi-color-card-border, #ccc);
    color: var(--gi-color-primary, {primary});
    padding-bottom: 0.25rem;
}}
.gi-print-footer {{
    margin-top: 2rem;
    padding-top: 0.75rem;
    border-top: 1px solid var(--gi-color-card-border, #ddd);
    font-size: 0.75rem;
    color: var(--gi-color-muted, #666);
    text-align: center;
}}
.gi-print-footer-platform {{
    opacity: 0.65;
    font-size: 0.7rem;
}}
.gi-print-footer-platform img {{
    height: 18px;
    vertical-align: middle;
    margin-left: 0.25rem;
}}
@media print {{
    .no-print {{ display: none !important; }}
    body {{ font-size: 11pt; }}
    .gi-print-body {{ background: #fff; }}
}}
"""
