"""Phase 4 — Clinical documentation from EBS only (no independent reasoning)."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from typing import Any

from clinical_knowledge_platform.reasoning.engine import load_session

# Document types required by platform contract
DOCUMENT_TYPES = (
    "hpi",
    "chief_complaint",
    "relevant_pmh",
    "medications",
    "allergies",
    "exam_notes",
    "ix_summary",
    "assessment_narrative",
    "plan_narrative",
    "soap",
    "admission",
    "progress",
    "procedure",
    "consultation",
    "discharge_summary",
    "referral_letter",
    "follow_up_note",
    "patient_journey",
)


def ebs_fingerprint(ebs: dict) -> str:
    payload = json.dumps(
        {
            "findings": ebs.get("findings_ledger") or [],
            "problems": ebs.get("presenting_problems") or [],
            "diff": ebs.get("differential") or [],
            "mgmt": ebs.get("management_recommendations") or [],
            "narrative": ebs.get("narrative_draft") or "",
        },
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]


def _findings(ebs: dict, *, kinds: set[str] | None = None, polarity: str | None = None, source: str | None = None) -> list[dict]:
    out = []
    for f in ebs.get("findings_ledger") or []:
        if kinds and f.get("kind") not in kinds:
            continue
        if polarity and f.get("polarity") != polarity:
            continue
        if source and f.get("source") != source:
            continue
        out.append(f)
    return out


def draft_from_ebs(ebs: dict, doc_type: str) -> tuple[str, dict]:
    """Pure mapping EBS → narrative + structured. Physician remains final author."""
    if doc_type not in DOCUMENT_TYPES:
        raise ValueError(f"Unknown document type: {doc_type}")

    problems = ebs.get("presenting_problems") or []
    labels = ", ".join(p.get("label") or p.get("code") for p in problems) or "unspecified presenting problem(s)"
    narrative = (ebs.get("narrative_draft") or "").strip()
    diff = ebs.get("differential") or []
    mgmt = ebs.get("management_recommendations") or []
    exam = _findings(ebs, source="exam")
    ix_orders = _findings(ebs, kinds={"investigation_order"})
    ix_results = _findings(ebs, kinds={"investigation_result"})
    plan_edits = ebs.get("plan_edits") or {}
    summary_edits = ebs.get("summary_edits") or {}

    structured: dict[str, Any] = {
        "doc_type": doc_type,
        "presenting_problems": problems,
        "differential": diff[:10],
        "management": mgmt,
        "source": "ebs",
    }

    if doc_type == "chief_complaint":
        body = f"Chief complaint: {labels}."
        structured["chief_complaint"] = labels
    elif doc_type == "hpi":
        body = narrative or f"History of present illness draft for {labels}."
        structured["hpi"] = body
    elif doc_type == "relevant_pmh":
        rf = [f for f in ebs.get("findings_ledger") or [] if "known" in (f.get("code") or "").lower() or f.get("kind") == "risk_factor"]
        body = "Relevant past medical / risk context from encounter findings:\n" + (
            "\n".join(f"- {f.get('code')} ({f.get('polarity')})" for f in rf) or "- None captured in EBS yet."
        )
        structured["pmh_items"] = rf
    elif doc_type == "medications":
        meds = [f for f in ebs.get("findings_ledger") or [] if (f.get("kind") == "drug") or "nsaid" in (f.get("code") or "").lower()]
        body = "Medications / exposures noted in EBS:\n" + (
            "\n".join(f"- {f.get('code')}: {f.get('value') or f.get('polarity')}" for f in meds) or "- None recorded."
        )
        structured["medications"] = meds
    elif doc_type == "allergies":
        al = [f for f in ebs.get("findings_ledger") or [] if "allerg" in (f.get("code") or "").lower()]
        body = "Allergies from EBS:\n" + (
            "\n".join(f"- {f.get('code')}" for f in al) or "- Not yet captured in this encounter."
        )
        structured["allergies"] = al
    elif doc_type == "exam_notes":
        body = "Examination findings:\n" + (
            "\n".join(f"- {f.get('code')}: {f.get('polarity')}" + (f" ({f.get('value')})" if f.get("value") else "") for f in exam)
            or "- No exam findings recorded."
        )
        structured["exam"] = exam
    elif doc_type == "ix_summary":
        lines = ["Investigations ordered:"]
        lines += [f"- {f.get('code')}" for f in ix_orders] or ["- None"]
        lines.append("Results recorded:")
        lines += [f"- {f.get('code')}: {f.get('polarity')}" + (f" = {f.get('value')}" if f.get("value") else "") for f in ix_results] or ["- None"]
        body = "\n".join(lines)
        structured["orders"] = ix_orders
        structured["results"] = ix_results
    elif doc_type == "assessment_narrative":
        top = ", ".join(f"{d.get('label')} ({d.get('confidence')})" for d in diff[:5] if d.get("status") != "excluded")
        body = summary_edits.get("assessment_note") or (
            (narrative + "\n\n" if narrative else "")
            + f"Assessment (knowledge-ranked differential from EBS): {top or 'insufficient data'}."
        )
        structured["assessment"] = top
    elif doc_type == "plan_narrative":
        plan_bits = [m.get("label") or m.get("code") for m in mgmt]
        body = plan_edits.get("plan_text") or (
            "Plan (from EBS management recommendations):\n"
            + ("\n".join(f"- {b}" for b in plan_bits) or "- No management edges active yet.")
            + ("\n\nFollow-up: " + (plan_edits.get("follow_up_text") or "as clinically indicated."))
        )
        structured["plan_items"] = plan_bits
    elif doc_type == "soap":
        s = f"S: {labels}. {narrative}".strip()
        o = "O: Exam — " + (", ".join(f"{f.get('code')}={f.get('polarity')}" for f in exam) or "not recorded") + "; Ix — " + (
            ", ".join(f.get("code") for f in ix_results) or "pending/none"
        )
        a = "A: " + (", ".join(f"{d.get('label')} ({d.get('confidence')})" for d in diff[:4] if d.get("status") != "excluded") or "differential forming")
        p = "P: " + (", ".join(m.get("label") or m.get("code") for m in mgmt) or "continue evaluation")
        body = "\n".join([s, o, a, p])
        structured["soap"] = {"S": s, "O": o, "A": a, "P": p}
    elif doc_type == "admission":
        body = (
            f"Admission note draft\nReason: {labels}\n\n"
            f"{narrative}\n\n"
            f"Working concerns: "
            + (", ".join(d.get("label") for d in diff[:3] if d.get("status") != "excluded") or "TBD")
            + "\nPlan: "
            + (", ".join(m.get("label") or m.get("code") for m in mgmt) or "TBD")
        )
    elif doc_type == "progress":
        body = f"Progress note\nInterval: based on current EBS at {ebs.get('updated_at')}.\n{narrative or 'No narrative draft yet.'}"
    elif doc_type == "procedure":
        procs = [f for f in ebs.get("findings_ledger") or [] if f.get("kind") in ("procedure", "investigation_order") and "egd" in (f.get("code") or "").lower()]
        body = "Procedure note draft (from EGS orders/findings):\n" + (
            "\n".join(f"- {f.get('code')}" for f in procs) or "- No procedure-linked orders in EBS."
        )
        structured["procedures"] = procs
    elif doc_type == "consultation":
        body = (
            f"Consultation request draft\nQuestion: evaluation of {labels}\n\n"
            f"Summary: {narrative or 'See structured history.'}\n"
            f"Differential: "
            + (", ".join(d.get("label") for d in diff[:5] if d.get("status") != "excluded") or "forming")
        )
    elif doc_type == "discharge_summary":
        body = (
            f"Discharge summary draft\nAdmission reason: {labels}\n\n"
            f"Course: {narrative or 'See encounter.'}\n"
            f"Discharge diagnoses (working): "
            + (", ".join(d.get('label') for d in diff[:3] if d.get('status') != 'excluded') or 'TBD')
            + "\nDischarge plan: "
            + (plan_edits.get("plan_text") or ", ".join(m.get("label") or m.get("code") for m in mgmt) or "TBD")
        )
    elif doc_type == "referral_letter":
        body = (
            f"Referral letter draft\nDear colleague,\n\nI am referring this patient for further evaluation of {labels}.\n\n"
            f"{narrative or ''}\n\nThank you for your opinion.\n"
        )
    elif doc_type == "follow_up_note":
        fu = ebs.get("follow_up_recommendations") or []
        body = "Follow-up note draft\n" + (
            "\n".join(f"- {x.get('label') or x}" for x in fu)
            or (plan_edits.get("follow_up_text") or "- Follow-up as clinically indicated.")
        )
        structured["follow_up"] = fu
    elif doc_type == "patient_journey":
        events = []
        for f in ebs.get("findings_ledger") or []:
            events.append(f"{f.get('at')}: {f.get('source')} · {f.get('code')}={f.get('polarity')}")
        body = "Patient journey (this encounter)\n" + ("\n".join(events) or "No findings yet.")
        structured["events"] = events
    else:
        body = narrative or f"Draft for {doc_type}"

    return body, structured


def _audit(db: sqlite3.Connection, document_id: int, action: str, detail: dict | None = None, actor_id: int | None = None) -> None:
    db.execute(
        "INSERT INTO ckp_document_audit (document_id, action, detail_json, actor_id) VALUES (?,?,?,?)",
        (document_id, action, json.dumps(detail or {}, ensure_ascii=False), actor_id),
    )


def create_or_regen_document(
    db: sqlite3.Connection,
    *,
    session_id: int,
    doc_type: str,
    actor_id: int | None = None,
    force_regen: bool = False,
) -> dict:
    loaded = load_session(db, session_id)
    if not loaded:
        raise ValueError("Session not found")
    row, ebs = loaded
    patient_key = (row.get("patient_label") or f"session-{session_id}").strip()
    body, structured = draft_from_ebs(ebs, doc_type)
    fp = ebs_fingerprint(ebs)
    existing = db.execute(
        "SELECT * FROM ckp_document WHERE session_id=? AND doc_type=? ORDER BY id DESC LIMIT 1",
        (session_id, doc_type),
    ).fetchone()

    if existing and existing["status"] == "final" and not force_regen:
        return dict(existing)

    if existing and existing["status"] != "final":
        new_ver = int(existing["version"]) + 1
        db.execute(
            """UPDATE ckp_document SET body_text=?, structured_json=?, ebs_fingerprint=?, version=?,
               updated_at=datetime('now'), authored_by=? WHERE id=?""",
            (body, json.dumps(structured, ensure_ascii=False), fp, new_ver, actor_id, existing["id"]),
        )
        db.execute(
            """INSERT INTO ckp_document_version (document_id, version, body_text, structured_json, change_note, changed_by)
               VALUES (?,?,?,?,?,?)""",
            (existing["id"], new_ver, body, json.dumps(structured, ensure_ascii=False), "regen_from_ebs", actor_id),
        )
        _audit(db, existing["id"], "regen", {"fingerprint": fp}, actor_id)
        db.commit()
        return dict(db.execute("SELECT * FROM ckp_document WHERE id=?", (existing["id"],)).fetchone())

    cur = db.execute(
        """INSERT INTO ckp_document
           (session_id, patient_key, doc_type, title, status, body_text, structured_json, ebs_fingerprint, version, authored_by)
           VALUES (?,?,?,?,?,?,?,?,?,?)""",
        (
            session_id,
            patient_key,
            doc_type,
            doc_type.replace("_", " ").title(),
            "draft",
            body,
            json.dumps(structured, ensure_ascii=False),
            fp,
            1,
            actor_id,
        ),
    )
    doc_id = int(cur.lastrowid)
    db.execute(
        """INSERT INTO ckp_document_version (document_id, version, body_text, structured_json, change_note, changed_by)
           VALUES (?,?,?,?,?,?)""",
        (doc_id, 1, body, json.dumps(structured, ensure_ascii=False), "auto_draft", actor_id),
    )
    _audit(db, doc_id, "create_draft", {"fingerprint": fp}, actor_id)
    db.commit()
    return dict(db.execute("SELECT * FROM ckp_document WHERE id=?", (doc_id,)).fetchone())


def edit_document(
    db: sqlite3.Connection,
    document_id: int,
    *,
    body_text: str,
    actor_id: int | None = None,
    change_note: str = "manual_edit",
) -> dict:
    row = db.execute("SELECT * FROM ckp_document WHERE id=?", (document_id,)).fetchone()
    if not row:
        raise ValueError("Document not found")
    if row["status"] == "final":
        raise ValueError("Finalized documents cannot be edited; create a new version via amend workflow")
    new_ver = int(row["version"]) + 1
    structured = row["structured_json"] or "{}"
    db.execute(
        """UPDATE ckp_document SET body_text=?, version=?, updated_at=datetime('now'), authored_by=? WHERE id=?""",
        (body_text, new_ver, actor_id, document_id),
    )
    db.execute(
        """INSERT INTO ckp_document_version (document_id, version, body_text, structured_json, change_note, changed_by)
           VALUES (?,?,?,?,?,?)""",
        (document_id, new_ver, body_text, structured, change_note, actor_id),
    )
    _audit(db, document_id, "manual_edit", {"version": new_ver}, actor_id)
    db.commit()
    return dict(db.execute("SELECT * FROM ckp_document WHERE id=?", (document_id,)).fetchone())


def finalize_document(db: sqlite3.Connection, document_id: int, *, actor_id: int | None = None) -> dict:
    db.execute(
        """UPDATE ckp_document SET status='final', finalized_by=?, finalized_at=datetime('now'), updated_at=datetime('now')
           WHERE id=?""",
        (actor_id, document_id),
    )
    _audit(db, document_id, "finalize", {}, actor_id)
    db.commit()
    return dict(db.execute("SELECT * FROM ckp_document WHERE id=?", (document_id,)).fetchone())


def list_documents(db: sqlite3.Connection, session_id: int) -> list[dict]:
    return [dict(r) for r in db.execute(
        "SELECT * FROM ckp_document WHERE session_id=? ORDER BY doc_type, id",
        (session_id,),
    ).fetchall()]


def version_history(db: sqlite3.Connection, document_id: int) -> list[dict]:
    return [dict(r) for r in db.execute(
        "SELECT * FROM ckp_document_version WHERE document_id=? ORDER BY version DESC",
        (document_id,),
    ).fetchall()]


def audit_trail(db: sqlite3.Connection, document_id: int) -> list[dict]:
    return [dict(r) for r in db.execute(
        "SELECT * FROM ckp_document_audit WHERE document_id=? ORDER BY id DESC",
        (document_id,),
    ).fetchall()]
