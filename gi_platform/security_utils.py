"""Shared security helpers for URL sanitization and related checks."""
from __future__ import annotations

from urllib.parse import urlparse


def sanitize_link_url(url: str | None) -> str:
    """Allow only relative site paths or http(s)/mailto links.

    Blocks javascript:, data:, vbscript:, and protocol-relative //evil.com.
    """
    raw = (url or '').strip()
    if not raw:
        return ''
    lower = raw.lower()
    if lower.startswith(('javascript:', 'data:', 'vbscript:')):
        return ''
    if raw.startswith('/') and not raw.startswith('//'):
        return raw
    parsed = urlparse(raw)
    if parsed.scheme in ('http', 'https', 'mailto') and (parsed.netloc or parsed.scheme == 'mailto'):
        return raw
    return ''
