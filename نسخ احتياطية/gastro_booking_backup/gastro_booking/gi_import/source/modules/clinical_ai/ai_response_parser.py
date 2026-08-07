"""Provider-independent AI response parsing."""

from __future__ import annotations

import re
from typing import Any

from .constants import (
    SECTION_BULLET_LIST,
    SECTION_NARRATIVE,
    SECTION_RECOMMENDATIONS,
    SECTION_REFERENCES,
    SECTION_STRUCTURED,
    SECTION_TABLE,
)
from .models import ParsedAIResponse, ParsedSection


_SECTION_PATTERN = re.compile(r"^([A-Z_]+):\s*$", re.MULTILINE)
_BULLET_PATTERN = re.compile(r"^\s*[-*•]\s+(.+)$", re.MULTILINE)


class AIResponseParser:
    """Parse narrative provider output into structured objects."""

    def parse(self, raw_text: str) -> ParsedAIResponse:
        if not raw_text or not raw_text.strip():
            return ParsedAIResponse(raw_text=raw_text or "")

        sections = self._split_sections(raw_text)
        parsed = ParsedAIResponse(raw_text=raw_text)

        for title, body in sections.items():
            key = title.upper()
            if key == "NARRATIVE":
                parsed.narrative = body.strip()
                parsed.sections.append(
                    ParsedSection(SECTION_NARRATIVE, title, body.strip())
                )
            elif key == "BULLETS":
                bullets = self._extract_bullets(body)
                parsed.bullet_lists.append(bullets)
                parsed.sections.append(ParsedSection(SECTION_BULLET_LIST, title, bullets))
            elif key == "TABLE":
                table = self._parse_table(body)
                parsed.tables.append(table)
                parsed.sections.append(ParsedSection(SECTION_TABLE, title, table))
            elif key == "RECOMMENDATIONS":
                items = self._extract_bullets(body) or [line.strip() for line in body.splitlines() if line.strip()]
                parsed.recommendations.extend(items)
                parsed.sections.append(ParsedSection(SECTION_RECOMMENDATIONS, title, items))
            elif key == "REFERENCES":
                refs = [line.strip() for line in body.splitlines() if line.strip()]
                parsed.references.extend(refs)
                parsed.sections.append(ParsedSection(SECTION_REFERENCES, title, refs))
            else:
                parsed.sections.append(ParsedSection(SECTION_STRUCTURED, title, body.strip()))

        if not parsed.narrative and not parsed.sections:
            parsed.narrative = raw_text.strip()
        return parsed

    def _split_sections(self, text: str) -> dict[str, str]:
        matches = list(_SECTION_PATTERN.finditer(text))
        if not matches:
            return {"NARRATIVE": text}
        result: dict[str, str] = {}
        for idx, match in enumerate(matches):
            title = match.group(1)
            start = match.end()
            end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
            result[title] = text[start:end].strip()
        return result

    def _extract_bullets(self, text: str) -> list[str]:
        bullets = _BULLET_PATTERN.findall(text)
        if bullets:
            return [b.strip() for b in bullets]
        return [line.strip() for line in text.splitlines() if line.strip()]

    def _parse_table(self, text: str) -> dict[str, Any]:
        rows = [line.strip() for line in text.splitlines() if line.strip()]
        if not rows:
            return {"headers": [], "rows": []}
        if "|" in rows[0]:
            headers = [c.strip() for c in rows[0].split("|") if c.strip()]
            body_rows = []
            for row in rows[1:]:
                if set(row.strip()) <= {"-", "|", " "}:
                    continue
                body_rows.append([c.strip() for c in row.split("|") if c.strip()])
            return {"headers": headers, "rows": body_rows}
        return {"headers": [], "rows": [[r] for r in rows]}
