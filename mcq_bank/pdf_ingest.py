"""
Handles turning an uploaded file (real binary PDF, or a plain-text file
someone saved with a .pdf extension) into extractable text.

Extraction uses PyMuPDF as the primary method - it's pure Python (installed
via `pip install`, no external binary/tool needed), so it works identically
on Windows, macOS, and Linux with zero extra setup. pypdf is a second
fallback, and the system `pdftotext` CLI (if present) is a last resort for
environments that already have Poppler installed.
"""
import subprocess


def _looks_like_pdf_binary(filepath: str) -> bool:
    with open(filepath, "rb") as f:
        header = f.read(5)
    return header.startswith(b"%PDF-")


def _extract_with_pymupdf(filepath: str) -> str:
    import fitz  # PyMuPDF
    doc = fitz.open(filepath)
    try:
        return "\n".join(page.get_text("text") for page in doc)
    finally:
        doc.close()


def _extract_with_pypdf(filepath: str) -> str:
    from pypdf import PdfReader
    reader = PdfReader(filepath)
    return "\n".join((page.extract_text() or "") for page in reader.pages)


def _extract_with_pdftotext_cli(filepath: str) -> str:
    result = subprocess.run(
        ["pdftotext", "-layout", filepath, "-"],
        capture_output=True, timeout=600,
    )
    if result.returncode != 0:
        raise RuntimeError(f"pdftotext failed: {result.stderr.decode(errors='replace')[:500]}")
    return result.stdout.decode("utf-8", errors="replace")


def extract_text_from_file(filepath: str) -> str:
    """Returns plain text extracted from a real PDF binary, trying each
    method in order until one succeeds. Falls back to reading the file
    directly as text for non-PDF uploads (e.g. a .txt saved as .pdf)."""
    if not _looks_like_pdf_binary(filepath):
        with open(filepath, "r", encoding="utf-8", errors="replace", newline="") as f:
            return f.read()

    errors = []
    for name, fn in (
        ("PyMuPDF", _extract_with_pymupdf),
        ("pypdf", _extract_with_pypdf),
        ("pdftotext (system tool)", _extract_with_pdftotext_cli),
    ):
        try:
            text = fn(filepath)
            if text and text.strip():
                return text
            errors.append(f"{name}: extracted empty text")
        except Exception as e:
            errors.append(f"{name}: {e}")

    raise RuntimeError(
        "Could not extract text from this PDF with any available method. "
        "It may be a scanned/image-only PDF requiring OCR. Details: " + " | ".join(errors)
    )
