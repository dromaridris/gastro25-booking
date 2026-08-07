"""Evidence / versioning — knowledge version, provenance, cache invalidation."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any

from clinical_intelligence import knowledge_loader as kl


def get_evidence_registry() -> dict[str, Any]:
    path = kl.knowledge_path("evidence", "registry.json")
    if not path.is_file():
        return {
            "knowledge_version": "unknown",
            "provenance": {},
            "message": "evidence/registry.json missing",
        }
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def knowledge_version_info() -> dict[str, Any]:
    reg = get_evidence_registry()
    manifest = kl.load_manifest()
    return {
        "knowledge_version": reg.get("knowledge_version"),
        "registry_revision": reg.get("revision"),
        "manifest_revision": manifest.get("revision"),
        "manifest_phase": manifest.get("phase"),
        "built_at": reg.get("built_at"),
        "provenance": reg.get("provenance") or {},
        "reload_policy": reg.get("reload_policy") or {},
    }


def reload_knowledge(*, db: sqlite3.Connection | None = None, reason: str = "manual") -> dict[str, Any]:
    """Invalidate in-process caches and optionally log reload event."""
    kl.clear_knowledge_cache()
    info = knowledge_version_info()
    event = {
        "at": datetime.now(timezone.utc).isoformat(),
        "reason": reason,
        "knowledge_version": info.get("knowledge_version"),
    }
    if db is not None:
        db.execute(
            """
            INSERT INTO ci_knowledge_event (event_type, payload_json, created_at)
            VALUES ('reload', ?, datetime('now'))
            """,
            (json.dumps(event, ensure_ascii=False),),
        )
        db.commit()
    return {"ok": True, "event": event, "version": info}


def record_import_event(db: sqlite3.Connection, *, result: dict[str, Any], user_id: int | None = None) -> None:
    db.execute(
        """
        INSERT INTO ci_knowledge_event (event_type, payload_json, created_by, created_at)
        VALUES ('import', ?, ?, datetime('now'))
        """,
        (json.dumps(result, ensure_ascii=False), user_id),
    )
    db.commit()


def list_knowledge_events(db: sqlite3.Connection, *, limit: int = 30) -> list[dict]:
    rows = db.execute(
        """
        SELECT id, event_type, payload_json, created_by, created_at
        FROM ci_knowledge_event
        ORDER BY id DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        try:
            d["payload"] = json.loads(d.get("payload_json") or "{}")
        except json.JSONDecodeError:
            d["payload"] = {}
        out.append(d)
    return out
