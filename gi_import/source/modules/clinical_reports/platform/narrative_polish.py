"""Post-generation narrative polish — vocabulary labels and list formatting."""

import re

from app.modules.clinical_reports.vocabulary import vocabulary_code_label_map

_EMPTY_DETAIL_SUFFIXES = ("; —", "; --", ". —", ". --")


def apply_vocabulary_narrative_polish(sections: dict[str, str]) -> dict[str, str]:
    """Replace vocabulary codes with display labels in generated narrative sections."""
    code_labels = vocabulary_code_label_map()
    return {
        section_key: _polish_narrative_text(text or "", code_labels)
        for section_key, text in sections.items()
    }


def _polish_narrative_text(text: str, code_labels: dict[str, str]) -> str:
    if not text.strip():
        return text
    for code, label in sorted(code_labels.items(), key=lambda item: -len(item[0])):
        spaced = code.replace("_", " ")
        text = re.sub(rf"\b{re.escape(code)}\b", label, text)
        if spaced != code:
            text = re.sub(rf"\b{re.escape(spaced)}\b", label, text, flags=re.IGNORECASE)
    lines = []
    for line in text.split("\n"):
        for suffix in _EMPTY_DETAIL_SUFFIXES:
            if line.rstrip().endswith(suffix):
                line = line.rstrip()[: -len(suffix)]
        lines.append(line)
    return "\n".join(lines)
