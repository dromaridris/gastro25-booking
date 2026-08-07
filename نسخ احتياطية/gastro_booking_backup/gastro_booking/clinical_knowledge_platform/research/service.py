"""Phase 7 — Research & learning platform (independent UX; may read clinical data)."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from typing import Any


def _audit(db: sqlite3.Connection, action: str, object_kind: str | None = None, object_id: int | None = None, detail: dict | None = None, actor_id: int | None = None) -> None:
    db.execute(
        "INSERT INTO ckp_research_audit (action, object_kind, object_id, detail_json, actor_id) VALUES (?,?,?,?,?)",
        (action, object_kind, object_id, json.dumps(detail or {}, ensure_ascii=False), actor_id),
    )


def deidentify_token(patient_key: str, salt: str = "ckp-research") -> str:
    return hashlib.sha256(f"{salt}:{patient_key}".encode("utf-8")).hexdigest()[:16]


def create_registry(
    db: sqlite3.Connection,
    *,
    code: str,
    label: str,
    description: str = "",
    variables: list | None = None,
    inclusion: dict | None = None,
    exclusion: dict | None = None,
    actor_id: int | None = None,
) -> dict:
    cur = db.execute(
        """INSERT INTO ckp_research_registry
           (code, label, description, variables_json, inclusion_json, exclusion_json, created_by)
           VALUES (?,?,?,?,?,?,?)""",
        (
            code,
            label,
            description,
            json.dumps(variables or [], ensure_ascii=False),
            json.dumps(inclusion or {}, ensure_ascii=False),
            json.dumps(exclusion or {}, ensure_ascii=False),
            actor_id,
        ),
    )
    rid = int(cur.lastrowid)
    _audit(db, "create_registry", "registry", rid, {"code": code}, actor_id)
    db.commit()
    return get_registry(db, rid)


def get_registry(db: sqlite3.Connection, registry_id: int) -> dict | None:
    row = db.execute("SELECT * FROM ckp_research_registry WHERE id=?", (registry_id,)).fetchone()
    if not row:
        return None
    d = dict(row)
    d["variables"] = json.loads(d.pop("variables_json") or "[]")
    d["inclusion"] = json.loads(d.pop("inclusion_json") or "{}")
    d["exclusion"] = json.loads(d.pop("exclusion_json") or "{}")
    return d


def list_registries(db: sqlite3.Connection) -> list[dict]:
    return [dict(r) for r in db.execute("SELECT id, code, label, version, status, created_at FROM ckp_research_registry ORDER BY id DESC").fetchall()]


def bump_registry_version(db: sqlite3.Connection, registry_id: int, actor_id: int | None = None) -> dict:
    db.execute(
        "UPDATE ckp_research_registry SET version=version+1, updated_at=datetime('now') WHERE id=?",
        (registry_id,),
    )
    _audit(db, "version_bump", "registry", registry_id, {}, actor_id)
    db.commit()
    return get_registry(db, registry_id)


def create_cohort(db: sqlite3.Connection, *, registry_id: int, code: str, label: str, criteria: dict | None = None) -> dict:
    cur = db.execute(
        "INSERT INTO ckp_research_cohort (registry_id, code, label, criteria_json) VALUES (?,?,?,?)",
        (registry_id, code, label, json.dumps(criteria or {}, ensure_ascii=False)),
    )
    db.commit()
    return dict(db.execute("SELECT * FROM ckp_research_cohort WHERE id=?", (cur.lastrowid,)).fetchone())


def extract_variables_from_memory(memory: dict, variables: list[dict]) -> dict:
    """Pull requested variables from longitudinal memory / timelines — no invented clinical logic."""
    out: dict[str, Any] = {}
    timelines = memory.get("timelines") or {}
    summary = memory.get("summary") or {}
    for v in variables:
        key = v.get("key") or v.get("code")
        source = v.get("source") or "timelines.disease"
        if source.startswith("timelines."):
            bucket = source.split(".", 1)[1]
            items = timelines.get(bucket) or []
            out[key] = [i.get("code") for i in items]
        elif source == "summary.encounter_count":
            out[key] = summary.get("encounter_count")
        elif source == "risk":
            out[key] = memory.get("risk")
        else:
            out[key] = None
            out[f"{key}__missing"] = True
    return out


def enroll_from_longitudinal(
    db: sqlite3.Connection,
    *,
    cohort_id: int,
    patient_key: str,
    registry_variables: list | None = None,
) -> dict:
    from clinical_knowledge_platform.longitudinal import service as long_svc

    memory = long_svc.get_memory(db, patient_key)
    if not memory:
        raise ValueError("No longitudinal memory for patient — ingest an encounter first")
    extracted = extract_variables_from_memory(memory, registry_variables or [])
    token = deidentify_token(patient_key)
    try:
        cur = db.execute(
            """INSERT INTO ckp_research_member (cohort_id, patient_key, extracted_json, deid_token)
               VALUES (?,?,?,?)""",
            (cohort_id, patient_key, json.dumps(extracted, ensure_ascii=False), token),
        )
    except sqlite3.IntegrityError:
        db.execute(
            "UPDATE ckp_research_member SET extracted_json=?, deid_token=? WHERE cohort_id=? AND patient_key=?",
            (json.dumps(extracted, ensure_ascii=False), token, cohort_id, patient_key),
        )
        row = db.execute(
            "SELECT * FROM ckp_research_member WHERE cohort_id=? AND patient_key=?",
            (cohort_id, patient_key),
        ).fetchone()
        db.commit()
        return dict(row)
    count = db.execute("SELECT COUNT(*) AS c FROM ckp_research_member WHERE cohort_id=?", (cohort_id,)).fetchone()["c"]
    db.execute("UPDATE ckp_research_cohort SET member_count=? WHERE id=?", (count, cohort_id))
    _audit(db, "enroll_member", "cohort", cohort_id, {"patient_key": patient_key})
    db.commit()
    return dict(db.execute("SELECT * FROM ckp_research_member WHERE id=?", (cur.lastrowid,)).fetchone())


def create_study(db: sqlite3.Connection, *, code: str, title: str, registry_id: int | None, design: dict | None = None) -> dict:
    cur = db.execute(
        "INSERT INTO ckp_research_study (code, title, registry_id, design_json) VALUES (?,?,?,?)",
        (code, title, registry_id, json.dumps(design or {}, ensure_ascii=False)),
    )
    _audit(db, "create_study", "study", int(cur.lastrowid), {"code": code})
    db.commit()
    return dict(db.execute("SELECT * FROM ckp_research_study WHERE id=?", (cur.lastrowid,)).fetchone())


def data_quality_report(db: sqlite3.Connection, cohort_id: int) -> dict:
    members = [dict(r) for r in db.execute("SELECT * FROM ckp_research_member WHERE cohort_id=?", (cohort_id,)).fetchall()]
    missing_counts: dict[str, int] = {}
    for m in members:
        extracted = json.loads(m.get("extracted_json") or "{}")
        for k, v in extracted.items():
            if k.endswith("__missing") or v is None or v == []:
                base = k.replace("__missing", "")
                missing_counts[base] = missing_counts.get(base, 0) + 1
    return {
        "cohort_id": cohort_id,
        "n": len(members),
        "missing_counts": missing_counts,
        "completeness": 1.0 - (sum(missing_counts.values()) / max(1, len(members) * max(1, len(missing_counts)))) if members else 0.0,
    }


def survival_support_table(db: sqlite3.Connection, cohort_id: int) -> list[dict]:
    """Minimal TTE support: event from outcome_json if present."""
    rows = []
    for m in db.execute("SELECT * FROM ckp_research_member WHERE cohort_id=?", (cohort_id,)).fetchall():
        outcome = json.loads(m["outcome_json"] or "{}")
        rows.append(
            {
                "deid_token": m["deid_token"],
                "time": outcome.get("time"),
                "event": outcome.get("event"),
                "censored": outcome.get("censored"),
            }
        )
    return rows


def export_dataset(
    db: sqlite3.Connection,
    *,
    cohort_id: int,
    study_id: int | None = None,
    registry_id: int | None = None,
    deidentified: bool = True,
    actor_id: int | None = None,
) -> dict:
    members = [dict(r) for r in db.execute("SELECT * FROM ckp_research_member WHERE cohort_id=?", (cohort_id,)).fetchall()]
    payload = []
    for m in members:
        row = {
            "id": m["deid_token"] if deidentified else m["patient_key"],
            "extracted": json.loads(m["extracted_json"] or "{}"),
            "outcome": json.loads(m["outcome_json"] or "{}"),
        }
        payload.append(row)
    text = json.dumps({"cohort_id": cohort_id, "rows": payload}, ensure_ascii=False, indent=2)
    cur = db.execute(
        """INSERT INTO ckp_research_export (study_id, registry_id, export_kind, path_or_payload, deidentified, audit_json, created_by)
           VALUES (?,?,?,?,?,?,?)""",
        (
            study_id,
            registry_id,
            "json_dataset",
            text,
            1 if deidentified else 0,
            json.dumps({"n": len(payload)}, ensure_ascii=False),
            actor_id,
        ),
    )
    _audit(db, "export", "cohort", cohort_id, {"export_id": cur.lastrowid, "deidentified": deidentified}, actor_id)
    db.commit()
    return {"export_id": int(cur.lastrowid), "n": len(payload), "deidentified": deidentified}


def dashboard_stats(db: sqlite3.Connection) -> dict:
    return {
        "registries": db.execute("SELECT COUNT(*) AS c FROM ckp_research_registry").fetchone()["c"],
        "cohorts": db.execute("SELECT COUNT(*) AS c FROM ckp_research_cohort").fetchone()["c"],
        "members": db.execute("SELECT COUNT(*) AS c FROM ckp_research_member").fetchone()["c"],
        "studies": db.execute("SELECT COUNT(*) AS c FROM ckp_research_study").fetchone()["c"],
        "exports": db.execute("SELECT COUNT(*) AS c FROM ckp_research_export").fetchone()["c"],
    }
