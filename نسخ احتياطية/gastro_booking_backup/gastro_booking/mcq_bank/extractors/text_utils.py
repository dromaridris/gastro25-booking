"""
Generic text-cleanup helpers shared across extractors. Kept independent of
any single content type since flashcards/summaries/etc. will hit the same
running-header/footer and line-wrap noise problems.
"""
import re
from collections import Counter

SOFT_HYPHEN = "\u0002"

# Some PDFs encode bullet/checkbox glyphs as raw C0 control characters
# (e.g. \u0007 BEL) via custom font glyph mapping. These are invisible but
# break downstream regexes expecting the real character right after a
# number/letter. Strip all C0 controls except \n and \t.
CONTROL_CHAR_RE = re.compile(r"[\x00\x01\x03-\x08\x0b\x0c\x0e-\x1f]")


def strip_control_characters(text: str) -> str:
    return CONTROL_CHAR_RE.sub("", text)

STRUCTURAL_MARKER_RE = re.compile(
    r"^(Question\s+\d+|Chapter\s+\d+|QUESTIONS|ANSWERS|\d+\.\s*[A-E]?\.?)$",
    re.IGNORECASE,
)


def normalize_line_endings(raw_text: str) -> str:
    """Handles CRLF, bare CR, and bare LF sources uniformly."""
    return raw_text.replace("\r\n", "\n").replace("\r", "\n")


def _templatize(line: str) -> str:
    """Collapse trailing/embedded digit runs so 'Book Title 42' and
    'Book Title 108' normalize to the same template - catches footers whose
    only variation is the page number."""
    return re.sub(r"\d+", "#", line)


def detect_running_noise_lines(raw_text: str, min_repeats=8, max_len=90, min_len=15):
    """
    Generic running header/footer detector. Two signals combined:
    1. Exact-line repeats at roughly regular intervals (static boilerplate).
    2. Templated repeats (digits collapsed to '#') at regular intervals -
       catches footers like "Book Title 42" / "Book Title 108" where only
       the page number changes.
    Regularity (not raw frequency) is the key signal, because legitimate
    structural markers like "Question 48" can also recur several times
    across a book (once per chapter) without being page furniture.
    min_len/min_repeats are deliberately conservative - medical text is full
    of short numeric lines (lab values, doses) that can coincidentally
    repeat; false negatives here are far cheaper than accidentally eating
    real clinical content.
    Returns a set of exact line strings to strip.
    """
    lines = raw_text.split("\n")
    exact_positions, template_positions, template_examples = {}, {}, {}
    for i, line in enumerate(lines):
        s = line.strip()
        if not s or not (min_len <= len(s) <= max_len) or not any(c.isdigit() for c in s):
            continue
        if STRUCTURAL_MARKER_RE.match(s):
            continue
        exact_positions.setdefault(s, []).append(i)
        tmpl = _templatize(s)
        template_positions.setdefault(tmpl, []).append(i)
        template_examples.setdefault(tmpl, set()).add(s)

    def is_regular(idxs, min_count):
        if len(idxs) < min_count:
            return False
        gaps = [idxs[k + 1] - idxs[k] for k in range(len(idxs) - 1)]
        mean_gap = sum(gaps) / len(gaps)
        if mean_gap <= 0:
            return False
        variance = sum((g - mean_gap) ** 2 for g in gaps) / len(gaps)
        return (variance ** 0.5) / mean_gap <= 0.35

    noise = set()
    for line, idxs in exact_positions.items():
        if is_regular(idxs, min_repeats):
            noise.add(line)

    for tmpl, idxs in template_positions.items():
        if is_regular(idxs, min_repeats) and len(template_examples[tmpl]) >= 3:
            noise.update(template_examples[tmpl])

    return noise


def strip_noise_lines(raw_text: str, noise_lines: set) -> str:
    if not noise_lines:
        return raw_text
    kept = [l for l in raw_text.split("\n") if l.strip() not in noise_lines]
    return "\n".join(kept)


def clean_prose(lines) -> str:
    """Join wrapped lines into prose, rejoin soft-hyphen word breaks, collapse whitespace."""
    joined = " ".join(l.strip() for l in lines if l.strip())
    joined = joined.replace(SOFT_HYPHEN + " ", "").replace(SOFT_HYPHEN, "")
    joined = re.sub(r"\s+", " ", joined).strip()
    return joined


def preprocess_book_text(raw_text: str) -> str:
    """Full pipeline: strip stray control-character glyph artifacts,
    normalize line endings, strip detected running noise lines. Run this
    once on a freshly-ingested book before any chapter splitting or
    extraction happens."""
    text = strip_control_characters(raw_text)
    text = normalize_line_endings(text)
    noise = detect_running_noise_lines(text)
    text = strip_noise_lines(text, noise)
    return text
