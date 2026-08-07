"""SQLite Knowledge Library service — Gastro25 authoritative runtime."""

from __future__ import annotations

import json
from typing import Any


def list_objects(db, *, status: str | None = None, object_type: str | None = None,
                 q: str | None = None, limit: int = 100) -> list[dict]:
    sql = "SELECT * FROM gi_knowledge_object WHERE 1=1"
    params: list[Any] = []
    if status:
        sql += " AND status = ?"
        params.append(status)
    if object_type:
        sql += " AND object_type = ?"
        params.append(object_type)
    if q:
        sql += " AND (title LIKE ? OR summary LIKE ? OR slug LIKE ?)"
        like = f"%{q}%"
        params.extend([like, like, like])
    sql += " ORDER BY updated_at DESC LIMIT ?"
    params.append(limit)
    return db.execute(sql, params).fetchall()


def get_object(db, object_id: int):
    return db.execute(
        "SELECT * FROM gi_knowledge_object WHERE id = ?", (object_id,)
    ).fetchone()


def get_object_by_slug(db, slug: str):
    return db.execute(
        "SELECT * FROM gi_knowledge_object WHERE slug = ?", (slug,)
    ).fetchone()


def create_object(db, *, slug: str, title: str, object_type: str = 'concept',
                  summary: str = '', body: dict | None = None, created_by: int | None = None,
                  status: str = 'draft') -> int:
    cur = db.execute(
        """
        INSERT INTO gi_knowledge_object
        (slug, title, object_type, summary, body_json, created_by, status)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (slug, title, object_type, summary, json.dumps(body or {}), created_by, status),
    )
    db.commit()
    return cur.lastrowid


def update_object_status(db, object_id: int, status: str) -> None:
    db.execute(
        "UPDATE gi_knowledge_object SET status = ?, updated_at = datetime('now') WHERE id = ?",
        (status, object_id),
    )
    if status == 'published':
        db.execute(
            "UPDATE gi_knowledge_object SET published_at = datetime('now') WHERE id = ?",
            (object_id,),
        )
    db.commit()


def list_links(db, object_id: int) -> list[dict]:
    return db.execute(
        """
        SELECT l.*, t.title AS target_title, t.slug AS target_slug, t.object_type AS target_type
        FROM gi_knowledge_link l
        JOIN gi_knowledge_object t ON t.id = l.target_id
        WHERE l.source_id = ?
        """,
        (object_id,),
    ).fetchall()


def add_link(db, source_id: int, target_id: int, link_type: str) -> None:
    db.execute(
        "INSERT INTO gi_knowledge_link (source_id, target_id, link_type) VALUES (?, ?, ?)",
        (source_id, target_id, link_type),
    )
    db.commit()


def request_activation(db, object_id: int, requested_by: int | None, notes: str = '') -> int:
    cur = db.execute(
        """
        INSERT INTO gi_knowledge_activation (object_id, requested_by, notes)
        VALUES (?, ?, ?)
        """,
        (object_id, requested_by, notes),
    )
    db.commit()
    return cur.lastrowid


def list_pending_reviews(db) -> list[dict]:
    return db.execute(
        "SELECT * FROM gi_knowledge_object WHERE status = 'review' ORDER BY updated_at DESC"
    ).fetchall()


def list_pending_activations(db) -> list[dict]:
    return db.execute(
        """
        SELECT a.*, o.title, o.slug
        FROM gi_knowledge_activation a
        JOIN gi_knowledge_object o ON o.id = a.object_id
        WHERE a.status = 'pending'
        ORDER BY a.created_at DESC
        """
    ).fetchall()


def resolve_activation(db, activation_id: int, *, approved: bool,
                       resolved_by: int | None = None, notes: str = '') -> None:
    status = 'approved' if approved else 'rejected'
    row = db.execute(
        "SELECT * FROM gi_knowledge_activation WHERE id = ?", (activation_id,)
    ).fetchone()
    if not row:
        return
    db.execute(
        """
        UPDATE gi_knowledge_activation
        SET status = ?, notes = COALESCE(NULLIF(?, ''), notes), resolved_at = datetime('now')
        WHERE id = ?
        """,
        (status, notes, activation_id),
    )
    if approved:
        update_object_status(db, row['object_id'], 'published')
    db.commit()


def approve_review(db, object_id: int) -> None:
    update_object_status(db, object_id, 'published')


def registry_stats(db) -> dict:
    rows = db.execute(
        """
        SELECT status, object_type, COUNT(*) AS c
        FROM gi_knowledge_object GROUP BY status, object_type
        """
    ).fetchall()
    by_status: dict[str, int] = {}
    by_type: dict[str, int] = {}
    total = 0
    for r in rows:
        total += r['c']
        by_status[r['status']] = by_status.get(r['status'], 0) + r['c']
        by_type[r['object_type']] = by_type.get(r['object_type'], 0) + r['c']
    pending_activation = db.execute(
        "SELECT COUNT(*) AS c FROM gi_knowledge_activation WHERE status = 'pending'"
    ).fetchone()['c']
    pending_review = db.execute(
        "SELECT COUNT(*) AS c FROM gi_knowledge_object WHERE status = 'review'"
    ).fetchone()['c']
    return {
        'total': total,
        'by_status': by_status,
        'by_type': by_type,
        'pending_activation': pending_activation,
        'pending_review': pending_review,
    }


def list_provenance(db, object_id: int) -> list[dict]:
    return db.execute(
        """
        SELECT * FROM gi_knowledge_provenance
        WHERE object_id = ?
        ORDER BY created_at DESC
        """,
        (object_id,),
    ).fetchall()


def add_provenance(db, object_id: int, *, source_type: str = 'manual',
                   source_filename: str = '', import_job_id: int | None = None,
                   author: str = '', grade_level: str = '', notes: str = '') -> None:
    db.execute(
        """
        INSERT INTO gi_knowledge_provenance
        (object_id, source_type, source_filename, import_job_id, author, grade_level, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (object_id, source_type, source_filename, import_job_id, author, grade_level, notes),
    )
    db.commit()


def delete_object(db, object_id: int) -> bool:
    """Permanently remove a knowledge object and related rows (admin/HOD only)."""
    obj = get_object(db, object_id)
    if not obj:
        return False
    db.execute(
        "DELETE FROM gi_knowledge_link WHERE source_id = ? OR target_id = ?",
        (object_id, object_id),
    )
    db.execute("DELETE FROM gi_knowledge_activation WHERE object_id = ?", (object_id,))
    db.execute("DELETE FROM gi_knowledge_provenance WHERE object_id = ?", (object_id,))
    db.execute("DELETE FROM gi_knowledge_object WHERE id = ?", (object_id,))
    db.commit()
    return True


def search_knowledge(db, q: str, limit: int = 20) -> list[dict]:
    like = f"%{q}%"
    return db.execute(
        """
        SELECT id, slug, title, object_type, status, summary
        FROM gi_knowledge_object
        WHERE title LIKE ? OR summary LIKE ? OR slug LIKE ?
        ORDER BY
            CASE status WHEN 'published' THEN 0 ELSE 1 END,
            title
        LIMIT ?
        """,
        (like, like, like, limit),
    ).fetchall()
