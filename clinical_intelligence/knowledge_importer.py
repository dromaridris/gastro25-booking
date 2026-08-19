"""Knowledge Importer — validate JSON packs against schemas; optional install into clinical_knowledge."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from clinical_intelligence import knowledge_loader as kl
from clinical_intelligence.schema_validate import validate_against_schema


KIND_SCHEMA = {
    "history_template": "history_template.schema.json",
    "shared_question": "shared_question.schema.json",
    "dictionary_entity": "dictionary_entity.schema.json",
}


def _load_schema(name: str) -> dict:
    path = kl.knowledge_path("schemas", name)
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def detect_kind(data: Any, filename: str = "") -> str | None:
    if isinstance(data, dict):
        if "complaint_code" in data and "sections" in data:
            return "history_template"
        if "questions" in data and isinstance(data["questions"], list):
            return "question_library"
        if data.get("id", "").startswith("Q") and "prompt" in data:
            return "shared_question"
        if "entity_type" in data and "code" in data:
            return "dictionary_entity"
        if "systems" in data and "complaint_code" in data:
            return "exam_template"
        if "patterns" in data or "bundles" in data or "interpretations" in data:
            return "rule_pack"
        if "knowledge_version" in data:
            return "evidence_registry"
    if isinstance(data, list) and data and isinstance(data[0], dict) and "entity_type" in data[0]:
        return "dictionary_pack"
    lower = filename.lower()
    if "history" in lower:
        return "history_template"
    if "library" in lower:
        return "question_library"
    return None


def validate_pack(data: Any, *, kind: str | None = None, filename: str = "") -> dict[str, Any]:
    kind = kind or detect_kind(data, filename)
    errors: list[str] = []
    warnings: list[str] = []

    if not kind:
        return {"ok": False, "kind": None, "errors": ["Could not detect pack kind"], "warnings": []}

    if kind == "history_template":
        schema = _load_schema(KIND_SCHEMA["history_template"])
        errors.extend(validate_against_schema(data, schema))
        library = kl.load_question_library()
        missing = []
        for section in data.get("sections") or []:
            for qid in section.get("question_ids") or []:
                if qid not in library:
                    missing.append(qid)
        if missing:
            errors.append(f"Unknown question refs: {', '.join(sorted(set(missing)))}")
    elif kind == "shared_question":
        schema = _load_schema(KIND_SCHEMA["shared_question"])
        errors.extend(validate_against_schema(data, schema))
    elif kind == "question_library":
        schema = _load_schema(KIND_SCHEMA["shared_question"])
        for i, q in enumerate(data.get("questions") or []):
            errors.extend(validate_against_schema(q, schema, path=f"$.questions[{i}]"))
    elif kind == "dictionary_entity":
        schema = _load_schema(KIND_SCHEMA["dictionary_entity"])
        errors.extend(validate_against_schema(data, schema))
    elif kind == "dictionary_pack":
        schema = _load_schema(KIND_SCHEMA["dictionary_entity"])
        for i, ent in enumerate(data):
            errors.extend(validate_against_schema(ent, schema, path=f"$[{i}]"))
    elif kind in {"exam_template", "rule_pack", "evidence_registry"}:
        if not isinstance(data, dict):
            errors.append("Expected object")
        elif kind == "exam_template" and "systems" not in data:
            errors.append("exam_template requires systems[]")
        elif kind == "rule_pack" and not any(
            k in data for k in ("patterns", "bundles", "interpretations", "suggestions", "modules", "actions", "skip_rules")
        ):
            warnings.append("rule_pack has no recognized top-level rule keys")
    else:
        warnings.append(f"No strict schema for kind={kind}; structural checks only")

    return {
        "ok": len(errors) == 0,
        "kind": kind,
        "errors": errors,
        "warnings": warnings,
    }


def validate_file(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"ok": False, "path": str(path), "errors": [str(exc)], "warnings": [], "kind": None}
    result = validate_pack(data, filename=path.name)
    result["path"] = str(path)
    result["data"] = data
    return result


def install_pack(
    source_path: Path,
    *,
    dest_relative: str,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Copy a validated pack into clinical_knowledge under dest_relative."""
    result = validate_file(source_path)
    if not result["ok"]:
        return {**result, "installed": False, "dry_run": dry_run}

    dest = kl.knowledge_path(*dest_relative.replace("\\", "/").split("/"))
    if dry_run:
        return {
            "ok": True,
            "installed": False,
            "dry_run": True,
            "dest": str(dest),
            "kind": result["kind"],
            "warnings": result.get("warnings") or [],
        }

    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_path, dest)
    kl.clear_knowledge_cache()
    return {
        "ok": True,
        "installed": True,
        "dry_run": False,
        "dest": str(dest),
        "kind": result["kind"],
        "warnings": result.get("warnings") or [],
    }


def validate_tree(root: Path | None = None) -> dict[str, Any]:
    """Validate core published packs under clinical_knowledge."""
    root = root or kl.KNOWLEDGE_ROOT
    reports = []
    targets = [
        root / "questions" / "library.json",
        *sorted((root / "templates" / "history").glob("*.json")),
    ]
    for path in targets:
        if path.is_file():
            r = validate_file(path)
            reports.append({k: r[k] for k in ("path", "ok", "kind", "errors", "warnings") if k in r})
    ok = all(r["ok"] for r in reports) if reports else False
    return {"ok": ok, "count": len(reports), "reports": reports}
