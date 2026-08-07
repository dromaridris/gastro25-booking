"""PDF and text extraction for Knowledge Library imports — native text + optional OCR."""

from __future__ import annotations

import os
import re


def extract_document_text(path: str, *, max_chars: int = 120_000) -> dict:
    """
    Extract text from PDF or plain-text upload.

    Returns dict: text, method (txt|pypdf|ocr|none), pages, char_count, excerpt, ocr_available.
    """
    if not path or not os.path.isfile(path):
        return _empty('none', ocr_available=_ocr_available())

    low = path.lower()
    if low.endswith('.txt') or low.endswith('.json'):
        try:
            with open(path, encoding='utf-8', errors='replace') as fh:
                text = fh.read(max_chars + 1)
        except OSError:
            return _empty('none', ocr_available=_ocr_available())
        if len(text) > max_chars:
            text = text[:max_chars]
        return _pack(text, 'txt', pages=1, ocr_available=_ocr_available())

    if not low.endswith('.pdf'):
        return _empty('none', ocr_available=_ocr_available())

    native = _extract_pypdf(path, max_chars=max_chars)
    method = 'pypdf' if native.strip() else 'none'
    text = native

    if len(native.strip()) < 80:
        ocr_text = _extract_ocr(path, max_chars=max_chars)
        if len(ocr_text.strip()) > len(native.strip()):
            text = ocr_text
            method = 'ocr'

    if len(text) > max_chars:
        text = text[:max_chars]
    return _pack(text, method, pages=_pdf_page_count(path), ocr_available=_ocr_available())


def _empty(method: str, *, ocr_available: bool) -> dict:
    return {
        'text': '',
        'method': method,
        'pages': 0,
        'char_count': 0,
        'excerpt': '',
        'ocr_available': ocr_available,
    }


def _pack(text: str, method: str, *, pages: int, ocr_available: bool) -> dict:
    cleaned = re.sub(r'\s+', ' ', (text or '').strip())
    excerpt = cleaned[:600] + ('…' if len(cleaned) > 600 else '')
    return {
        'text': text or '',
        'method': method if cleaned else 'none',
        'pages': pages,
        'char_count': len(text or ''),
        'excerpt': excerpt,
        'ocr_available': ocr_available,
    }


def _extract_pypdf(path: str, *, max_chars: int) -> str:
    try:
        from pypdf import PdfReader
    except ImportError:
        try:
            from PyPDF2 import PdfReader  # type: ignore
        except ImportError:
            return ''
    try:
        reader = PdfReader(path)
        parts: list[str] = []
        total = 0
        for page in reader.pages:
            chunk = page.extract_text() or ''
            parts.append(chunk)
            total += len(chunk)
            if total >= max_chars:
                break
        return '\n\n'.join(parts)
    except Exception:
        return ''


def _pdf_page_count(path: str) -> int:
    try:
        from pypdf import PdfReader
    except ImportError:
        try:
            from PyPDF2 import PdfReader  # type: ignore
        except ImportError:
            return 0
    try:
        return len(PdfReader(path).pages)
    except Exception:
        return 0


def _ocr_available() -> bool:
    try:
        import pytesseract  # noqa: F401
        from pdf2image import convert_from_path  # noqa: F401
        return True
    except ImportError:
        return False


def _extract_ocr(path: str, *, max_chars: int, max_pages: int = 8) -> str:
    if not _ocr_available():
        return ''
    try:
        import pytesseract
        from pdf2image import convert_from_path
    except ImportError:
        return ''
    try:
        images = convert_from_path(path, first_page=1, last_page=max_pages, dpi=200)
    except Exception:
        return ''
    parts: list[str] = []
    total = 0
    for img in images:
        try:
            chunk = pytesseract.image_to_string(img) or ''
        except Exception:
            chunk = ''
        parts.append(chunk)
        total += len(chunk)
        if total >= max_chars:
            break
    return '\n\n'.join(parts)
