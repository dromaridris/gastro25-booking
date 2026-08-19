"""
Detects chapter boundaries in a preprocessed book text. Two strategies are
tried, in order; the first one that finds >=2 chapters wins. If neither
finds anything, the whole book is treated as a single chapter and flagged
low-confidence so an admin knows to review/adjust manually.
"""
import re


def _title_case(s):
    return re.sub(r"\s+", " ", s).strip()


DOT_LEADER_RE = re.compile(r"\.{4,}\s*\d+\s*$")  # ToC-style "Title.......123"


def _is_toc_entry(lines, after_line_i, window=4):
    """A real chapter heading is never immediately followed by a
    dot-leader/page-number line (that's Table-of-Contents formatting).
    Checked generically so it works on any book, not just this one."""
    for l in lines[after_line_i:after_line_i + window]:
        if DOT_LEADER_RE.search(l):
            return True
    return False


def split_by_explicit_chapter_headings(lines):
    """Strategy 1: explicit 'CHAPTER N' headings. Handles both the number
    on the same line ('CHAPTER 3', e.g. DDSEP) and the number on its own
    following line ('CHAPTER' / '3', e.g. Sleisenger-style layouts where
    the word and numeral are separate text runs in the PDF). Table-of-
    Contents entries that mimic this pattern (dot-leader + page number
    right after) are filtered out."""
    starts = []
    i = 0
    while i < len(lines):
        s = lines[i].strip()
        m_same_line = re.match(r"^CHAPTER\s+(\d+)\s*$", s, re.IGNORECASE)
        m_word_only = re.match(r"^CHAPTER\s*$", s, re.IGNORECASE)
        if m_same_line:
            num, number_line_i = int(m_same_line.group(1)), i
        elif m_word_only:
            # look at the next non-empty line for a bare number
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            if j < len(lines) and re.match(r"^\d+\s*$", lines[j].strip()):
                num, number_line_i = int(lines[j].strip()), j
            else:
                i += 1
                continue
        else:
            i += 1
            continue

        if not _is_toc_entry(lines, number_line_i + 1):
            starts.append((i, num, number_line_i))
        i = number_line_i + 1

    if len(starts) < 2:
        return None

    # Dedupe: a real book never repeats the same chapter number back-to-back.
    # A second identical-number match right after the first is almost always
    # a running-header repeat (e.g. right before that chapter's own ANSWERS
    # section), not a genuinely new chapter - keep only the first occurrence.
    deduped = [starts[0]]
    for s in starts[1:]:
        if s[1] != deduped[-1][1]:
            deduped.append(s)
    starts = deduped
    if len(starts) < 2:
        return None

    chapters = []
    for idx, (heading_line_i, num, number_line_i) in enumerate(starts):
        end = starts[idx + 1][0] if idx + 1 < len(starts) else len(lines)
        # title = the next non-empty line(s) right after the number, until a
        # blank run - capped short to avoid sweeping up author-byline lines
        title_lines = []
        for l in lines[number_line_i + 1:min(number_line_i + 4, end)]:
            s = l.strip()
            if not s:
                if title_lines:
                    break
                continue
            if re.match(r"^(Answers? ?& ?critiques?|Question\s+\d+|QUESTIONS?\s*$)", s, re.IGNORECASE):
                break
            title_lines.append(s)
            if len(title_lines) >= 2:
                break
        chapters.append({
            "number": num,
            "title": _title_case(" ".join(title_lines)) or f"Chapter {num}",
            "start_line": heading_line_i,
            "end_line": end,
        })
    return chapters


def split_by_questions_answers_sections(lines):
    """Strategy 2: repeated 'QUESTIONS' section headers mark the start of
    each chapter (e.g. Oxford Best-of-Five-style books, where each chapter
    is QUESTIONS...ANSWERS...)."""
    q_starts = []
    for i, line in enumerate(lines):
        if re.match(r"^\s*QUESTIONS\s*$", line.strip(), re.IGNORECASE):
            q_starts.append(i)
    if len(q_starts) < 2:
        return None

    chapters = []
    for idx, line_i in enumerate(q_starts):
        end = q_starts[idx + 1] if idx + 1 < len(q_starts) else len(lines)
        # title = nearest non-empty, non-numeric line(s) before this QUESTIONS marker
        title_lines = []
        for l in reversed(lines[max(0, line_i - 6):line_i]):
            s = l.strip()
            if not s:
                continue
            if re.match(r"^\d+$", s):
                continue
            title_lines.insert(0, s)
            if len(title_lines) >= 2:
                break
        chapters.append({
            "number": idx + 1,
            "title": _title_case(" ".join(title_lines)) or f"Chapter {idx + 1}",
            "start_line": line_i,
            "end_line": end,
        })
    return chapters


def detect_chapters(preprocessed_text: str):
    lines = preprocessed_text.split("\n")

    chapters = split_by_explicit_chapter_headings(lines)
    if chapters:
        return chapters, "explicit_chapter_headings"

    chapters = split_by_questions_answers_sections(lines)
    if chapters:
        return chapters, "questions_answers_sections"

    return [{
        "number": 1,
        "title": "Full document (chapter boundaries not detected)",
        "start_line": 0,
        "end_line": len(lines),
    }], "fallback_whole_document"


def get_chapter_text(preprocessed_text: str, chapter):
    lines = preprocessed_text.split("\n")
    return "\n".join(lines[chapter["start_line"]:chapter["end_line"]])
