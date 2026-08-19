"""WeasyPrint PDF generation with active hospital branding."""

from __future__ import annotations

from flask import render_template


def render_html_to_pdf(html: str) -> bytes:
    try:
        from weasyprint import HTML
    except ImportError as exc:
        raise RuntimeError("WeasyPrint is not available in this environment.") from exc
    return HTML(string=html, base_url=".").write_pdf()


def render_template_to_pdf(template_name: str, **context) -> bytes:
    html = render_template(template_name, **context)
    return render_html_to_pdf(html)
