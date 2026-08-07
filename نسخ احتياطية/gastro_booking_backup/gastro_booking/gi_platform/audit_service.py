"""Global GI audit trail — Blueprint §19–20."""

from __future__ import annotations

import json
from typing import Any


def log_event(db, *, action: str, entity_type: str, entity_id: int | str | None = None,
              user_id: int | None = None, details: dict | None = None) -> None:
    db.execute(
        """
        INSERT INTO gi_audit_event (action, entity_type, entity_id, user_id, details_json)
        VALUES (?, ?, ?, ?, ?)
        """,
        (action, entity_type, str(entity_id) if entity_id is not None else None,
         user_id, json.dumps(details or {})),
    )
    db.commit()


def list_events(db, *, entity_type: str | None = None, limit: int = 100) -> list:
    sql = "SELECT * FROM gi_audit_event WHERE 1=1"
    params: list[Any] = []
    if entity_type:
        sql += " AND entity_type = ?"
        params.append(entity_type)
    sql += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)
    return db.execute(sql, params).fetchall()
