"""Phase 6 — Longitudinal clinical intelligence across encounters."""

from __future__ import annotations

import json
import sqlite3
from typing import Any

from clinical_knowledge_platform.reasoning.engine import load_session


def patient_key_for_session(db: sqlite3.Connection, session_id: int) -> str:
    row = db.execute("SELECT patient_label FROM cre_session WHERE id=?", (session_id,)).fetchone()
    if not row:
        raise ValueError("Session not found")
    return (row["patient_label"] or f"session-{session_id}").strip()


def ingest_session_into_memory(db: sqlite3.Connection, session_id: int) -> dict:
    loaded = load_session(db, session_id)
    if not loaded:
        raise ValueError("Session not found")
    row, ebs = loaded
    patient_key = (row.get("patient_label") or f"session-{session_id}").strip()

    mem = db.execute("SELECT * FROM ckp_longitudinal_memory WHERE patient_key=?", (patient_key,)).fetchone()
    timelines = {
        "disease": [],
        "procedure": [],
        "medication": [],
        "investigation": [],
        "symptom": [],
    }
    if mem:
        timelines = json.loads(mem["timelines_json"] or "{}") or timelines

    def push(kind: str, code: str, label: str | None, polarity: str | None, value: str | None, at: str | None):
        timelines.setdefault(kind, []).append(
            {
                "code": code,
                "label": label or code,
                "polarity": polarity,
                "value": value,
                "session_id": session_id,
                "at": at,
            }
        )
        db.execute(
            """INSERT INTO ckp_longitudinal_event
               (patient_key, session_id, event_kind, event_code, label, polarity, value, occurred_at, body_json)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (patient_key, session_id, kind, code, label, polarity, value, at, "{}"),
        )

    for p in ebs.get("presenting_problems") or []:
        push("symptom", p.get("code"), p.get("label"), "present", None, ebs.get("updated_at"))
    for d in ebs.get("differential") or []:
        if d.get("status") == "excluded":
            continue
        if d.get("confidence") in ("established", "very_strong", "strong", "moderate"):
            push("disease", d.get("code"), d.get("label"), d.get("status"), d.get("confidence"), ebs.get("updated_at"))
    for f in ebs.get("findings_ledger") or []:
        kind = f.get("kind") or "finding"
        bucket = {
            "investigation_order": "investigation",
            "investigation_result": "investigation",
            "drug": "medication",
            "procedure": "procedure",
            "symptom": "symptom",
        }.get(kind, kind if kind in timelines else "investigation")
        if bucket not in timelines:
            timelines[bucket] = []
        push(bucket, f.get("code"), f.get("code"), f.get("polarity"), f.get("value"), f.get("at"))

    # Progression / response / recurrence heuristics from multi-session history
    prior_sessions = db.execute(
        "SELECT id, ebs_json, updated_at FROM cre_session WHERE patient_label=? AND id<>? ORDER BY id",
        (patient_key, session_id),
    ).fetchall()
    summary = {
        "last_session_id": session_id,
        "encounter_count": 1 + len(prior_sessions),
        "patterns": [],
        "progression": [],
        "treatment_response": [],
        "recurrence": [],
        "trends": [],
        "risk_evolution": [],
    }
    if mem:
        old = json.loads(mem["summary_json"] or "{}")
        summary["patterns"] = old.get("patterns") or []

    # Recurrence: same disease code in prior + current
    current_dx = {d.get("code") for d in ebs.get("differential") or [] if d.get("status") != "excluded"}
    for ps in prior_sessions:
        try:
            pebs = json.loads(ps["ebs_json"] or "{}")
        except json.JSONDecodeError:
            continue
        prior_dx = {d.get("code") for d in pebs.get("differential") or [] if d.get("status") != "excluded"}
        for code in current_dx & prior_dx:
            summary["recurrence"].append({"code": code, "prior_session_id": ps["id"], "current_session_id": session_id})
            summary["patterns"].append({"kind": "recurrent_diagnosis", "code": code})

    # Clinical delta vs most recent prior
    delta: dict[str, Any] = {"new_findings": [], "resolved_findings": [], "confidence_changes": []}
    prior_id = None
    if prior_sessions:
        prior = prior_sessions[-1]
        prior_id = prior["id"]
        pebs = json.loads(prior["ebs_json"] or "{}")
        prior_codes = {(f.get("code"), f.get("polarity")) for f in pebs.get("findings_ledger") or []}
        curr_codes = {(f.get("code"), f.get("polarity")) for f in ebs.get("findings_ledger") or []}
        for item in curr_codes - prior_codes:
            delta["new_findings"].append({"code": item[0], "polarity": item[1]})
        for item in prior_codes - curr_codes:
            delta["resolved_findings"].append({"code": item[0], "polarity": item[1]})
        prior_diff = {d.get("code"): d.get("confidence") for d in pebs.get("differential") or []}
        for d in ebs.get("differential") or []:
            if d.get("code") in prior_diff and prior_diff[d.get("code")] != d.get("confidence"):
                delta["confidence_changes"].append(
                    {"code": d.get("code"), "from": prior_diff[d.get("code")], "to": d.get("confidence")}
                )
        summary["progression"] = delta["confidence_changes"]
        summary["trends"] = [
            {"kind": "finding_delta", "new": len(delta["new_findings"]), "resolved": len(delta["resolved_findings"])}
        ]
        db.execute(
            """INSERT INTO ckp_encounter_compare (patient_key, current_session_id, prior_session_id, delta_json)
               VALUES (?,?,?,?)""",
            (patient_key, session_id, prior_id, json.dumps(delta, ensure_ascii=False)),
        )

    # Baseline: first encounter snapshot
    baseline = {
        "first_session_id": prior_sessions[0]["id"] if prior_sessions else session_id,
        "presenting_problems": (json.loads(prior_sessions[0]["ebs_json"]) if prior_sessions else ebs).get("presenting_problems")
        if prior_sessions
        else ebs.get("presenting_problems"),
    }
    if prior_sessions:
        try:
            baseline["presenting_problems"] = json.loads(prior_sessions[0]["ebs_json"] or "{}").get("presenting_problems")
        except json.JSONDecodeError:
            pass

    # Registry membership hints from disease codes
    registries = [{"code": f"reg.{c}", "disease": c} for c in sorted(current_dx)]
    risk = {
        "active_pathways": ebs.get("active_pathways") or [],
        "red_flags": ebs.get("red_flags") or [],
        "updated_at": ebs.get("updated_at"),
    }
    summary["risk_evolution"].append(risk)

    # Follow-up intelligence
    summary["follow_up_intelligence"] = ebs.get("follow_up_recommendations") or ebs.get("plan_edits") or {}

    payload = (
        json.dumps(summary, ensure_ascii=False),
        json.dumps(timelines, ensure_ascii=False),
        json.dumps(registries, ensure_ascii=False),
        json.dumps(risk, ensure_ascii=False),
        json.dumps(baseline, ensure_ascii=False),
    )
    if mem:
        db.execute(
            """UPDATE ckp_longitudinal_memory SET summary_json=?, timelines_json=?, registries_json=?,
               risk_json=?, baseline_json=?, updated_at=datetime('now') WHERE patient_key=?""",
            (*payload, patient_key),
        )
    else:
        db.execute(
            """INSERT INTO ckp_longitudinal_memory
               (patient_key, summary_json, timelines_json, registries_json, risk_json, baseline_json)
               VALUES (?,?,?,?,?,?)""",
            (patient_key, *payload),
        )
    db.commit()
    return get_memory(db, patient_key)


def get_memory(db: sqlite3.Connection, patient_key: str) -> dict | None:
    row = db.execute("SELECT * FROM ckp_longitudinal_memory WHERE patient_key=?", (patient_key,)).fetchone()
    if not row:
        return None
    d = dict(row)
    for k in ("summary_json", "timelines_json", "registries_json", "risk_json", "baseline_json"):
        key = k.replace("_json", "")
        d[key] = json.loads(d.pop(k) or ("{}" if "registries" not in k else "[]"))
    return d


def list_events(db: sqlite3.Connection, patient_key: str, limit: int = 200) -> list[dict]:
    return [dict(r) for r in db.execute(
        "SELECT * FROM ckp_longitudinal_event WHERE patient_key=? ORDER BY id DESC LIMIT ?",
        (patient_key, limit),
    ).fetchall()]


def latest_compare(db: sqlite3.Connection, patient_key: str) -> dict | None:
    row = db.execute(
        "SELECT * FROM ckp_encounter_compare WHERE patient_key=? ORDER BY id DESC LIMIT 1",
        (patient_key,),
    ).fetchone()
    if not row:
        return None
    d = dict(row)
    d["delta"] = json.loads(d.pop("delta_json") or "{}")
    return d
