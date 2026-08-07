"""
Gastro25 Core Services — QR Service
--------------------------------------
Generic QR helper for procedure reports.
"""

from __future__ import annotations

import base64
import io
import logging
from urllib.parse import quote

logger = logging.getLogger(__name__)


def generate_data_uri(url, box_size=6, border=2):
    """Return a base64 data: URI for a QR code, or None if generation fails."""
    try:
        import qrcode

        qr = qrcode.QRCode(box_size=box_size, border=border)
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color='black', back_color='white')
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        encoded = base64.b64encode(buf.getvalue()).decode('ascii')
        return f'data:image/png;base64,{encoded}'
    except ImportError:
        logger.warning(
            'QR code library missing — run: pip install "qrcode[pil]" Pillow'
        )
        return None
    except Exception:
        logger.exception('QR code generation failed for url=%s', url)
        return None


def generate_fallback_url(url, size: int = 120) -> str:
    """Online fallback when the qrcode package is unavailable (print img src)."""
    return (
        'https://api.qrserver.com/v1/create-qr-code/'
        f'?size={size}x{size}&data={quote(url, safe="")}'
    )


def generate_for_print(url, box_size=6, border=2, fallback_size: int = 120) -> dict:
    """Return data URI and/or fallback URL so print always can show a QR when possible."""
    data_uri = generate_data_uri(url, box_size=box_size, border=border)
    return {
        'data_uri': data_uri,
        'fallback_url': None if data_uri else generate_fallback_url(url, fallback_size),
    }
