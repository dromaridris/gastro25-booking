"""Load clinical_knowledge JSON packs (no hardcoded medical content)."""

from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parent.parent
KNOWLEDGE_ROOT = Path(os.environ.get("CLINICAL_KNOWLEDGE_ROOT", str(_ROOT / "clinical_knowledge")))


def _read_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def knowledge_path(*parts: str) -> Path:
    return KNOWLEDGE_ROOT.joinpath(*parts)


@lru_cache(maxsize=1)
def load_manifest() -> dict:
    return _read_json(knowledge_path("manifest.json"))


@lru_cache(maxsize=1)
def load_question_library() -> dict[str, dict]:
    data = _read_json(knowledge_path("questions", "library.json"))
    return {q["id"]: q for q in data.get("questions", [])}


@lru_cache(maxsize=1)
def load_complaint_index() -> list[dict]:
    data = _read_json(knowledge_path("packs", "complaints", "_index.json"))
    return list(data.get("complaints", []))


def complaint_code_to_slug(complaint_code: str) -> str:
    code = (complaint_code or "").strip()
    if code.startswith("CC_"):
        return code[3:]
    return code


@lru_cache(maxsize=64)
def load_history_template(complaint_code: str) -> dict | None:
    slug = complaint_code_to_slug(complaint_code)
    path = knowledge_path("templates", "history", f"{slug}.json")
    if not path.is_file():
        return None
    return _read_json(path)


@lru_cache(maxsize=64)
def load_exam_template(complaint_code: str) -> dict | None:
    slug = complaint_code_to_slug(complaint_code)
    path = knowledge_path("templates", "exam", f"{slug}.json")
    if not path.is_file():
        return None
    return _read_json(path)


def _load_rule_pack(kind: str, complaint_code: str) -> dict | None:
    slug = complaint_code_to_slug(complaint_code)
    path = knowledge_path("rules", kind, f"{slug}.json")
    if not path.is_file():
        return None
    return _read_json(path)


@lru_cache(maxsize=64)
def load_history_branching(complaint_code: str) -> dict | None:
    return _load_rule_pack("history_branching", complaint_code)


@lru_cache(maxsize=64)
def load_reasoning_rules(complaint_code: str) -> dict | None:
    return _load_rule_pack("reasoning", complaint_code)


@lru_cache(maxsize=64)
def load_investigation_rules(complaint_code: str) -> dict | None:
    return _load_rule_pack("investigation", complaint_code)


@lru_cache(maxsize=64)
def load_management_rules(complaint_code: str) -> dict | None:
    return _load_rule_pack("management", complaint_code)


@lru_cache(maxsize=64)
def load_interpretation_rules(complaint_code: str) -> dict | None:
    return _load_rule_pack("interpretation", complaint_code)


@lru_cache(maxsize=64)
def load_procedure_rules(complaint_code: str) -> dict | None:
    return _load_rule_pack("procedures", complaint_code)


@lru_cache(maxsize=64)
def load_scoring_rules(complaint_code: str) -> dict | None:
    return _load_rule_pack("scoring", complaint_code)


@lru_cache(maxsize=64)
def load_education_rules(complaint_code: str) -> dict | None:
    return _load_rule_pack("education", complaint_code)


@lru_cache(maxsize=1)
def load_research_rules() -> dict | None:
    path = knowledge_path("rules", "research", "knowledge_gaps.json")
    if not path.is_file():
        return None
    return _read_json(path)


@lru_cache(maxsize=1)
def load_sign_index() -> dict[str, dict]:
    signs = _read_json(knowledge_path("dictionary", "signs.json"))
    return {s["code"]: s for s in signs}


@lru_cache(maxsize=1)
def load_investigation_index() -> dict[str, dict]:
    items = _read_json(knowledge_path("dictionary", "investigations.json"))
    return {i["code"]: i for i in items}


@lru_cache(maxsize=1)
def load_procedure_index() -> dict[str, dict]:
    items = _read_json(knowledge_path("dictionary", "procedures.json"))
    return {i["code"]: i for i in items}


def clear_knowledge_cache() -> None:
    load_manifest.cache_clear()
    load_question_library.cache_clear()
    load_complaint_index.cache_clear()
    load_history_template.cache_clear()
    load_exam_template.cache_clear()
    load_history_branching.cache_clear()
    load_reasoning_rules.cache_clear()
    load_investigation_rules.cache_clear()
    load_management_rules.cache_clear()
    load_interpretation_rules.cache_clear()
    load_procedure_rules.cache_clear()
    load_scoring_rules.cache_clear()
    load_education_rules.cache_clear()
    load_research_rules.cache_clear()
    load_sign_index.cache_clear()
    load_investigation_index.cache_clear()
    load_procedure_index.cache_clear()
