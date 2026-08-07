"""CKP repository — specialty-agnostic CRUD over entities, relationships, releases."""

from __future__ import annotations

import json
import sqlite3
from typing import Any

from clinical_knowledge_platform import (
    ENTITY_TYPES,
    LIFECYCLE_STATES,
    RELATIONSHIP_TYPES,
    REL_DEFAULT_STRENGTH,
)


def _j(obj: Any) -> str:
    return json.dumps(obj if obj is not None else {}, ensure_ascii=False)


def _loads(text: str | None, default: Any = None) -> Any:
    if not text:
        return {} if default is None else default
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {} if default is None else default


def _row_entity(r: sqlite3.Row | None) -> dict | None:
    if r is None:
        return None
    d = dict(r)
    d["synonyms"] = _loads(d.pop("synonyms_json", "[]"), [])
    d["body"] = _loads(d.pop("body_json", "{}"), {})
    return d


def _row_rel(r: sqlite3.Row | None) -> dict | None:
    if r is None:
        return None
    d = dict(r)
    d["context"] = _loads(d.pop("context_json", "{}"), {})
    d["effect"] = _loads(d.pop("effect_json", "{}"), {})
    return d


def audit(db: sqlite3.Connection, action: str, kind: str, code: str | None, detail: dict | None = None, actor_id: int | None = None) -> None:
    db.execute(
        "INSERT INTO ckp_audit_log (action, object_kind, object_code, detail_json, actor_id) VALUES (?,?,?,?,?)",
        (action, kind, code, _j(detail or {}), actor_id),
    )


# ----- Domains -----

def upsert_domain(db: sqlite3.Connection, *, code: str, label: str, scope_note: str = "", body: dict | None = None, status: str = "active") -> int:
    row = db.execute("SELECT id, revision FROM ckp_domain WHERE code=?", (code,)).fetchone()
    body = body or {}
    if row:
        rev = int(row["revision"]) + 1
        db.execute(
            "UPDATE ckp_domain SET label=?, scope_note=?, status=?, revision=?, body_json=?, updated_at=datetime('now') WHERE id=?",
            (label, scope_note, status, rev, _j(body), row["id"]),
        )
        audit(db, "update", "domain", code, {"revision": rev})
        return int(row["id"])
    cur = db.execute(
        "INSERT INTO ckp_domain (code, label, scope_note, status, body_json) VALUES (?,?,?,?,?)",
        (code, label, scope_note, status, _j(body)),
    )
    audit(db, "create", "domain", code, {})
    return int(cur.lastrowid)


def get_domain(db: sqlite3.Connection, code: str) -> dict | None:
    r = db.execute("SELECT * FROM ckp_domain WHERE code=?", (code,)).fetchone()
    if not r:
        return None
    d = dict(r)
    d["body"] = _loads(d.pop("body_json", "{}"), {})
    return d


def list_domains(db: sqlite3.Connection) -> list[dict]:
    rows = db.execute("SELECT * FROM ckp_domain ORDER BY label").fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["body"] = _loads(d.pop("body_json", "{}"), {})
        out.append(d)
    return out


# ----- Entities -----

def upsert_entity(
    db: sqlite3.Connection,
    *,
    code: str,
    entity_type: str,
    label: str,
    domain_code: str | None = None,
    synonyms: list | None = None,
    body: dict | None = None,
    lifecycle: str = "active",
    actor_id: int | None = None,
    change_note: str = "",
) -> int:
    if entity_type not in ENTITY_TYPES:
        raise ValueError(f"Unknown entity_type: {entity_type}")
    if lifecycle not in LIFECYCLE_STATES:
        raise ValueError(f"Unknown lifecycle: {lifecycle}")
    domain_id = None
    if domain_code:
        d = get_domain(db, domain_code)
        if not d:
            raise ValueError(f"Unknown domain: {domain_code}")
        domain_id = d["id"]
    synonyms = synonyms or []
    body = body or {}
    row = db.execute("SELECT id, revision FROM ckp_entity WHERE code=?", (code,)).fetchone()
    if row:
        rev = int(row["revision"]) + 1
        db.execute(
            """UPDATE ckp_entity SET entity_type=?, label=?, domain_id=?, lifecycle=?, revision=?,
               synonyms_json=?, body_json=?, updated_at=datetime('now') WHERE id=?""",
            (entity_type, label, domain_id, lifecycle, rev, _j(synonyms), _j(body), row["id"]),
        )
        eid = int(row["id"])
    else:
        cur = db.execute(
            """INSERT INTO ckp_entity (code, entity_type, label, domain_id, lifecycle, synonyms_json, body_json)
               VALUES (?,?,?,?,?,?,?)""",
            (code, entity_type, label, domain_id, lifecycle, _j(synonyms), _j(body)),
        )
        eid = int(cur.lastrowid)
        rev = 1
    snap = {
        "code": code,
        "entity_type": entity_type,
        "label": label,
        "domain_id": domain_id,
        "lifecycle": lifecycle,
        "revision": rev,
        "synonyms": synonyms,
        "body": body,
    }
    db.execute(
        "INSERT OR REPLACE INTO ckp_entity_version (entity_id, revision, snapshot_json, changed_by, change_note) VALUES (?,?,?,?,?)",
        (eid, rev, _j(snap), actor_id, change_note),
    )
    audit(db, "upsert", "entity", code, {"revision": rev, "entity_type": entity_type}, actor_id)
    return eid


def get_entity(db: sqlite3.Connection, code: str) -> dict | None:
    return _row_entity(db.execute("SELECT * FROM ckp_entity WHERE code=?", (code,)).fetchone())


def list_entities(
    db: sqlite3.Connection,
    *,
    entity_type: str | None = None,
    domain_code: str | None = None,
    lifecycle: str | None = "active",
) -> list[dict]:
    sql = "SELECT e.* FROM ckp_entity e"
    args: list[Any] = []
    wh: list[str] = []
    if domain_code:
        sql += " LEFT JOIN ckp_domain d ON d.id=e.domain_id"
        wh.append("d.code=?")
        args.append(domain_code)
    if entity_type:
        wh.append("e.entity_type=?")
        args.append(entity_type)
    if lifecycle:
        wh.append("e.lifecycle=?")
        args.append(lifecycle)
    if wh:
        sql += " WHERE " + " AND ".join(wh)
    sql += " ORDER BY e.entity_type, e.label"
    return [_row_entity(r) for r in db.execute(sql, args).fetchall()]  # type: ignore[misc]


def deprecate_entity(db: sqlite3.Connection, code: str, *, superseded_by: str | None = None, actor_id: int | None = None) -> None:
    db.execute(
        "UPDATE ckp_entity SET lifecycle='deprecated', superseded_by_code=?, updated_at=datetime('now') WHERE code=?",
        (superseded_by, code),
    )
    audit(db, "deprecate", "entity", code, {"superseded_by": superseded_by}, actor_id)


# ----- Relationships -----

def normalize_rel_type(rel_type: str) -> str:
    if rel_type == "activates_pathway":
        return "activates"
    return rel_type


def upsert_relationship(
    db: sqlite3.Connection,
    *,
    rel_type: str,
    source_code: str,
    target_code: str,
    strength: str | None = None,
    context: dict | None = None,
    effect: dict | None = None,
    lifecycle: str = "active",
    guideline_assertion_code: str | None = None,
    actor_id: int | None = None,
    change_note: str = "",
) -> int:
    raw = rel_type
    rel_type = normalize_rel_type(rel_type)
    if raw not in RELATIONSHIP_TYPES and rel_type not in RELATIONSHIP_TYPES:
        raise ValueError(f"Unknown relationship type: {raw}")
    if not get_entity(db, source_code):
        raise ValueError(f"Unknown source entity: {source_code}")
    if rel_type != "bound_by" and not get_entity(db, target_code):
        raise ValueError(f"Unknown target entity: {target_code}")
    strength = strength or REL_DEFAULT_STRENGTH.get(rel_type)
    context = context or {}
    effect = effect or {}
    row = db.execute(
        "SELECT id, revision FROM ckp_relationship WHERE rel_type=? AND source_code=? AND target_code=?",
        (rel_type, source_code, target_code),
    ).fetchone()
    if row:
        rev = int(row["revision"]) + 1
        db.execute(
            """UPDATE ckp_relationship SET strength=?, context_json=?, effect_json=?, lifecycle=?, revision=?,
               guideline_assertion_code=?, updated_at=datetime('now') WHERE id=?""",
            (strength, _j(context), _j(effect), lifecycle, rev, guideline_assertion_code, row["id"]),
        )
        rid = int(row["id"])
    else:
        cur = db.execute(
            """INSERT INTO ckp_relationship
               (rel_type, source_code, target_code, strength, context_json, effect_json, lifecycle, guideline_assertion_code)
               VALUES (?,?,?,?,?,?,?,?)""",
            (rel_type, source_code, target_code, strength, _j(context), _j(effect), lifecycle, guideline_assertion_code),
        )
        rid = int(cur.lastrowid)
        rev = 1
    snap = {
        "rel_type": rel_type,
        "source_code": source_code,
        "target_code": target_code,
        "strength": strength,
        "context": context,
        "effect": effect,
        "lifecycle": lifecycle,
        "revision": rev,
        "guideline_assertion_code": guideline_assertion_code,
    }
    db.execute(
        "INSERT OR REPLACE INTO ckp_relationship_version (relationship_id, revision, snapshot_json, changed_by, change_note) VALUES (?,?,?,?,?)",
        (rid, rev, _j(snap), actor_id, change_note),
    )
    audit(db, "upsert", "relationship", f"{rel_type}:{source_code}->{target_code}", {"revision": rev}, actor_id)
    return rid


def list_relationships(
    db: sqlite3.Connection,
    *,
    source_code: str | None = None,
    target_code: str | None = None,
    rel_type: str | None = None,
    lifecycle: str | None = "active",
) -> list[dict]:
    wh: list[str] = []
    args: list[Any] = []
    if source_code:
        wh.append("source_code=?")
        args.append(source_code)
    if target_code:
        wh.append("target_code=?")
        args.append(target_code)
    if rel_type:
        wh.append("rel_type=?")
        args.append(normalize_rel_type(rel_type))
    if lifecycle:
        wh.append("lifecycle=?")
        args.append(lifecycle)
    sql = "SELECT * FROM ckp_relationship"
    if wh:
        sql += " WHERE " + " AND ".join(wh)
    sql += " ORDER BY rel_type, source_code, target_code"
    return [_row_rel(r) for r in db.execute(sql, args).fetchall()]  # type: ignore[misc]


def graph_for_release(db: sqlite3.Connection, release_id: int | None = None) -> dict:
    """Load active entities+relationships for reasoning. Release pins membership when published."""
    entities = {e["code"]: e for e in list_entities(db, lifecycle="active")}
    rels = list_relationships(db, lifecycle="active")
    if release_id:
        members = db.execute(
            "SELECT member_kind, member_code FROM ckp_release_member WHERE release_id=?",
            (release_id,),
        ).fetchall()
        if members:
            ent_codes = {m["member_code"] for m in members if m["member_kind"] == "entity"}
            rel_keys = {m["member_code"] for m in members if m["member_kind"] == "relationship"}
            if ent_codes:
                entities = {c: e for c, e in entities.items() if c in ent_codes}
            if rel_keys:
                rels = [r for r in rels if f"{r['rel_type']}:{r['source_code']}->{r['target_code']}" in rel_keys]
    return {"entities": entities, "relationships": rels, "release_id": release_id}


# ----- Guidelines -----

def upsert_guideline_work(db: sqlite3.Connection, *, code: str, society: str, title: str, year: int | None = None, edition: str = "", scope_note: str = "", body: dict | None = None) -> int:
    body = body or {}
    row = db.execute("SELECT id FROM ckp_guideline_work WHERE code=?", (code,)).fetchone()
    if row:
        db.execute(
            "UPDATE ckp_guideline_work SET society=?, title=?, year=?, edition=?, scope_note=?, body_json=?, updated_at=datetime('now') WHERE id=?",
            (society, title, year, edition, scope_note, _j(body), row["id"]),
        )
        return int(row["id"])
    cur = db.execute(
        "INSERT INTO ckp_guideline_work (code, society, title, year, edition, scope_note, body_json) VALUES (?,?,?,?,?,?,?)",
        (code, society, title, year, edition, scope_note, _j(body)),
    )
    return int(cur.lastrowid)


def upsert_guideline_assertion(
    db: sqlite3.Connection,
    *,
    code: str,
    work_code: str,
    statement: str,
    strength: str = "",
    direction: str = "recommend",
    evidence_grade: str = "",
    applies_to: list | None = None,
    lifecycle: str = "active",
    supersedes_code: str | None = None,
    body: dict | None = None,
) -> int:
    applies_to = applies_to or []
    body = body or {}
    row = db.execute("SELECT id, revision FROM ckp_guideline_assertion WHERE code=?", (code,)).fetchone()
    if row:
        rev = int(row["revision"]) + 1
        db.execute(
            """UPDATE ckp_guideline_assertion SET work_code=?, statement=?, strength=?, direction=?, evidence_grade=?,
               applies_to_json=?, lifecycle=?, revision=?, supersedes_code=?, body_json=?, updated_at=datetime('now') WHERE id=?""",
            (work_code, statement, strength, direction, evidence_grade, _j(applies_to), lifecycle, rev, supersedes_code, _j(body), row["id"]),
        )
        return int(row["id"])
    cur = db.execute(
        """INSERT INTO ckp_guideline_assertion
           (code, work_code, statement, strength, direction, evidence_grade, applies_to_json, lifecycle, supersedes_code, body_json)
           VALUES (?,?,?,?,?,?,?,?,?,?)""",
        (code, work_code, statement, strength, direction, evidence_grade, _j(applies_to), lifecycle, supersedes_code, _j(body)),
    )
    return int(cur.lastrowid)


def list_guideline_assertions(db: sqlite3.Connection, *, lifecycle: str | None = "active") -> list[dict]:
    sql = "SELECT * FROM ckp_guideline_assertion"
    args: list[Any] = []
    if lifecycle:
        sql += " WHERE lifecycle=?"
        args.append(lifecycle)
    sql += " ORDER BY code"
    out = []
    for r in db.execute(sql, args).fetchall():
        d = dict(r)
        d["applies_to"] = _loads(d.pop("applies_to_json", "[]"), [])
        d["body"] = _loads(d.pop("body_json", "{}"), {})
        out.append(d)
    return out


def create_release(db: sqlite3.Connection, *, code: str, label: str, notes: str = "", actor_id: int | None = None) -> int:
    cur = db.execute(
        "INSERT INTO ckp_knowledge_release (code, label, status, notes, created_by) VALUES (?,?,?,?,?)",
        (code, label, "draft", notes, actor_id),
    )
    audit(db, "create", "release", code, {}, actor_id)
    return int(cur.lastrowid)


def publish_release(db: sqlite3.Connection, release_id: int, *, actor_id: int | None = None) -> dict:
    """Snapshot all active entities + relationships into release members."""
    rel = db.execute("SELECT * FROM ckp_knowledge_release WHERE id=?", (release_id,)).fetchone()
    if not rel:
        raise ValueError("Release not found")
    db.execute("DELETE FROM ckp_release_member WHERE release_id=?", (release_id,))
    for e in list_entities(db, lifecycle="active"):
        db.execute(
            "INSERT INTO ckp_release_member (release_id, member_kind, member_code, member_revision) VALUES (?,?,?,?)",
            (release_id, "entity", e["code"], e["revision"]),
        )
    for r in list_relationships(db, lifecycle="active"):
        key = f"{r['rel_type']}:{r['source_code']}->{r['target_code']}"
        db.execute(
            "INSERT INTO ckp_release_member (release_id, member_kind, member_code, member_revision) VALUES (?,?,?,?)",
            (release_id, "relationship", key, r["revision"]),
        )
    for a in list_guideline_assertions(db, lifecycle="active"):
        db.execute(
            "INSERT INTO ckp_release_member (release_id, member_kind, member_code, member_revision) VALUES (?,?,?,?)",
            (release_id, "guideline_assertion", a["code"], a["revision"]),
        )
    db.execute(
        "UPDATE ckp_knowledge_release SET status='published', published_at=datetime('now'), updated_at=datetime('now') WHERE id=?",
        (release_id,),
    )
    audit(db, "publish", "release", rel["code"], {"release_id": release_id}, actor_id)
    out = get_release(db, release_id)
    if not out:
        raise ValueError("Release missing after publish")
    return out


def get_release(db: sqlite3.Connection, release_id: int) -> dict | None:
    r = db.execute("SELECT * FROM ckp_knowledge_release WHERE id=?", (release_id,)).fetchone()
    return dict(r) if r else None


def get_release_by_code(db: sqlite3.Connection, code: str) -> dict | None:
    r = db.execute("SELECT * FROM ckp_knowledge_release WHERE code=?", (code,)).fetchone()
    return dict(r) if r else None


def list_releases(db: sqlite3.Connection) -> list[dict]:
    return [dict(r) for r in db.execute("SELECT * FROM ckp_knowledge_release ORDER BY id DESC").fetchall()]


def latest_published_release(db: sqlite3.Connection) -> dict | None:
    r = db.execute(
        "SELECT * FROM ckp_knowledge_release WHERE status='published' ORDER BY published_at DESC, id DESC LIMIT 1"
    ).fetchone()
    return dict(r) if r else None
