"""Knowledge integrity validation — specialty-agnostic."""

from __future__ import annotations

import sqlite3
from typing import Any

from clinical_knowledge_platform import ENTITY_TYPES, RELATIONSHIP_TYPES
from clinical_knowledge_platform.repository import (
    list_entities,
    list_relationships,
    normalize_rel_type,
)


def validate_knowledge(db: sqlite3.Connection) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []

    entities = {e["code"]: e for e in list_entities(db, lifecycle=None)}
    active = {c: e for c, e in entities.items() if e["lifecycle"] == "active"}
    rels = list_relationships(db, lifecycle=None)

    for code, e in entities.items():
        if e["entity_type"] not in ENTITY_TYPES:
            errors.append(f"Entity {code}: invalid type {e['entity_type']}")
        if not (e.get("label") or "").strip():
            errors.append(f"Entity {code}: missing label")

    for r in rels:
        rt = normalize_rel_type(r["rel_type"])
        if rt not in RELATIONSHIP_TYPES and r["rel_type"] not in RELATIONSHIP_TYPES:
            errors.append(f"Rel {r['id']}: invalid type {r['rel_type']}")
        if r["source_code"] not in entities:
            errors.append(f"Rel {r['id']}: orphan source {r['source_code']}")
        if r["rel_type"] != "bound_by" and r["target_code"] not in entities:
            errors.append(f"Rel {r['id']}: orphan target {r['target_code']}")
        if r["lifecycle"] == "active":
            if r["source_code"] not in active:
                warnings.append(f"Active rel uses non-active source {r['source_code']}")
            if r["rel_type"] != "bound_by" and r["target_code"] not in active:
                warnings.append(f"Active rel uses non-active target {r['target_code']}")

    # Circular supersedes detection (simple)
    supersede = {
        r["source_code"]: r["target_code"]
        for r in rels
        if r["rel_type"] == "supersedes" and r["lifecycle"] == "active"
    }
    for start in supersede:
        seen = set()
        cur = start
        while cur in supersede:
            if cur in seen:
                errors.append(f"Circular supersedes involving {start}")
                break
            seen.add(cur)
            cur = supersede[cur]

    # Diseases without any inbound suggests/supports from symptoms — warning only
    diseases = [c for c, e in active.items() if e["entity_type"] == "disease"]
    inbound = set()
    for r in rels:
        if r["lifecycle"] != "active":
            continue
        if r["rel_type"] in ("suggests", "supports", "strongly_supports") and r["target_code"] in diseases:
            inbound.add(r["target_code"])
    for d in diseases:
        if d not in inbound:
            warnings.append(f"Disease {d} has no inbound suggests/supports from knowledge graph")

    return {
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
        "counts": {
            "entities_active": len(active),
            "entities_total": len(entities),
            "relationships_active": sum(1 for r in rels if r["lifecycle"] == "active"),
            "diseases": len(diseases),
        },
    }
