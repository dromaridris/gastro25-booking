"""Phase 5 — Clinical Decision Support (advisory only, specialty-agnostic)."""

from __future__ import annotations

import json
import sqlite3
from typing import Any

from clinical_knowledge_platform import repository as repo
from clinical_knowledge_platform.reasoning.engine import ClinicalReasoningEngine, load_engine, load_session


def _hyp_support(h: dict) -> tuple[list, list]:
    return list(h.get("support") or []), list(h.get("against") or [])


def build_cds_bundle(engine: ClinicalReasoningEngine, ebs: dict) -> list[dict[str, Any]]:
    """Derive advisory recommendations from EBS + KG. Never invent medical facts."""
    alerts: list[dict[str, Any]] = []

    # Differential explanation
    for d in (ebs.get("differential") or [])[:8]:
        if d.get("status") == "excluded":
            continue
        hyp = (ebs.get("hypotheses") or {}).get(d.get("code")) or d
        support, against = _hyp_support(hyp)
        alerts.append(
            {
                "alert_kind": "differential_explanation",
                "severity": "info",
                "title": f"Differential: {d.get('label')}",
                "explanation": f"Ranked {d.get('confidence')} (score {d.get('score')}) from knowledge relationships.",
                "supporting": support,
                "contradictory": against,
                "guideline_source": None,
                "confidence": d.get("confidence"),
                "body": {"disease_code": d.get("code"), "status": d.get("status")},
            }
        )

    # Investigation recommendations
    for ix in ebs.get("investigation_recommendations") or []:
        alerts.append(
            {
                "alert_kind": "investigation_recommendation",
                "severity": "info",
                "title": f"Consider investigation: {ix.get('label') or ix.get('code')}",
                "explanation": ix.get("rationale") or "Suggested by investigated_by edges for active hypotheses.",
                "supporting": ix.get("support") or [{"code": ix.get("for_disease")}],
                "contradictory": ix.get("against") or [],
                "guideline_source": ix.get("guideline"),
                "confidence": ix.get("priority") or "moderate",
                "body": ix,
            }
        )

    # Lab/imaging interpretation hooks (findings already in ledger)
    for f in ebs.get("findings_ledger") or []:
        if f.get("kind") != "investigation_result":
            continue
        ent = engine.entity(f.get("code") or "")
        related = engine.rels(source=f.get("code"))
        support = [{"rel": r["rel_type"], "target": r["target_code"]} for r in related if r["rel_type"] in (
            "supports", "strongly_supports", "confirms", "suggests"
        )]
        against = [{"rel": r["rel_type"], "target": r["target_code"]} for r in related if r["rel_type"] in (
            "argues_against", "strongly_argues_against", "excludes", "refutes"
        )]
        alerts.append(
            {
                "alert_kind": "ix_interpretation_hook",
                "severity": "info",
                "title": f"Interpretation hook: {ent['label'] if ent else f.get('code')}",
                "explanation": "Knowledge edges from this investigation finding; clinician interpretation required.",
                "supporting": support,
                "contradictory": against,
                "guideline_source": None,
                "confidence": "moderate" if support else "weak",
                "body": {"finding": f},
            }
        )

    # Guideline recommendations via bound_by
    for d in ebs.get("differential") or []:
        if d.get("status") == "excluded":
            continue
        for r in engine.rels(source=d.get("code"), rel_type="bound_by"):
            ga = engine.entity(r["target_code"])
            alerts.append(
                {
                    "alert_kind": "guideline_recommendation",
                    "severity": "info",
                    "title": f"Guideline link: {ga['label'] if ga else r['target_code']}",
                    "explanation": (ga or {}).get("body", {}).get("statement") if isinstance((ga or {}).get("body"), dict) else (
                        ga["label"] if ga else "Bound guideline assertion"
                    ),
                    "supporting": [{"disease": d.get("code")}],
                    "contradictory": [],
                    "guideline_source": r["target_code"],
                    "confidence": r.get("strength") or "moderate",
                    "body": {"relationship": r},
                }
            )
    for pw in ebs.get("active_pathways") or []:
        code = pw.get("code") if isinstance(pw, dict) else pw
        for r in engine.rels(source=code, rel_type="bound_by"):
            alerts.append(
                {
                    "alert_kind": "guideline_recommendation",
                    "severity": "warning",
                    "title": f"Pathway guideline: {r['target_code']}",
                    "explanation": "Active pathway is bound to a guideline assertion in the knowledge release.",
                    "supporting": [{"pathway": code}],
                    "contradictory": [],
                    "guideline_source": r["target_code"],
                    "confidence": "strong",
                    "body": {"pathway": pw, "relationship": r},
                }
            )

    # Management
    for m in ebs.get("management_recommendations") or []:
        alerts.append(
            {
                "alert_kind": "management_recommendation",
                "severity": "info",
                "title": f"Management: {m.get('label') or m.get('code')}",
                "explanation": m.get("rationale") or "From managed_by knowledge edges.",
                "supporting": m.get("support") or [],
                "contradictory": m.get("against") or [],
                "guideline_source": m.get("guideline"),
                "confidence": m.get("priority") or "moderate",
                "body": m,
            }
        )

    # Drug safety: contraindicates edges involving drugs in findings
    drug_codes = {
        f.get("code")
        for f in ebs.get("findings_ledger") or []
        if f.get("kind") == "drug" or (engine.entity(f.get("code") or "") or {}).get("entity_type") == "drug"
    }
    # Also HQ_nsaid etc mapped loosely via entity type drug / risk
    for code in list(drug_codes):
        for r in engine.rels(source=code, rel_type="contraindicates"):
            alerts.append(
                {
                    "alert_kind": "drug_safety",
                    "severity": "warning",
                    "title": f"Contraindication: {code} → {r['target_code']}",
                    "explanation": "Knowledge graph contraindicates relationship.",
                    "supporting": [{"rel": "contraindicates", "source": code, "target": r["target_code"]}],
                    "contradictory": [],
                    "guideline_source": r.get("guideline_assertion_code"),
                    "confidence": r.get("strength") or "strong",
                    "body": r,
                }
            )
        # Duplicate therapy / interactions stubs from associated_with between drugs
        for r in engine.rels(source=code, rel_type="associated_with"):
            tgt = engine.entity(r["target_code"])
            if tgt and tgt.get("entity_type") == "drug" and r["target_code"] in drug_codes:
                alerts.append(
                    {
                        "alert_kind": "drug_interaction",
                        "severity": "warning",
                        "title": f"Possible interaction / duplicate therapy: {code} & {r['target_code']}",
                        "explanation": "Both agents present; associated_with edge in knowledge graph.",
                        "supporting": [r],
                        "contradictory": [],
                        "guideline_source": None,
                        "confidence": "weak",
                        "body": r,
                    }
                )

    # Dose reminders — if management drug entity has body.dose_reminder
    for m in ebs.get("management_recommendations") or []:
        ent = engine.entity(m.get("code") or "")
        body = (ent or {}).get("body") or {}
        if isinstance(body, dict) and body.get("dose_reminder"):
            alerts.append(
                {
                    "alert_kind": "dose_reminder",
                    "severity": "info",
                    "title": f"Dose reminder: {ent['label']}",
                    "explanation": body["dose_reminder"],
                    "supporting": [{"management": m.get("code")}],
                    "contradictory": [],
                    "guideline_source": body.get("guideline"),
                    "confidence": "moderate",
                    "body": body,
                }
            )

    # Preventive / vaccine / screening — education & follow_up_scheme entities linked
    for et in ("education", "follow_up_scheme"):
        for e in engine.entities.values():
            if e.get("entity_type") != et:
                continue
            # Only surface if managed_by from an active hypothesis
            for d in ebs.get("working_diagnoses") or ebs.get("differential") or []:
                if d.get("status") == "excluded":
                    continue
                if engine.rels(source=d.get("code"), target=e["code"], rel_type="managed_by"):
                    alerts.append(
                        {
                            "alert_kind": "preventive_reminder",
                            "severity": "info",
                            "title": f"Preventive / follow-up: {e['label']}",
                            "explanation": f"Linked via managed_by from {d.get('code')}.",
                            "supporting": [{"disease": d.get("code"), "item": e["code"]}],
                            "contradictory": [],
                            "guideline_source": None,
                            "confidence": "moderate",
                            "body": e,
                        }
                    )

    # Clinical scores — severity_classification / diagnostic_criteria entities
    for e in engine.entities.values():
        if e.get("entity_type") not in ("severity_classification", "diagnostic_criteria"):
            continue
        for r in engine.rels(source=e["code"]):
            if r["rel_type"] in ("confirms", "supports", "suggests") and any(
                d.get("code") == r["target_code"] for d in (ebs.get("differential") or [])
            ):
                alerts.append(
                    {
                        "alert_kind": "clinical_score",
                        "severity": "info",
                        "title": f"Score / criteria: {e['label']}",
                        "explanation": "Criteria entity in knowledge graph related to active differential.",
                        "supporting": [r],
                        "contradictory": [],
                        "guideline_source": None,
                        "confidence": "moderate",
                        "body": e,
                    }
                )

    # Order sets — bundle investigations for top disease
    for d in (ebs.get("differential") or [])[:2]:
        if d.get("status") == "excluded":
            continue
        ixs = [r["target_code"] for r in engine.rels(source=d.get("code"), rel_type="investigated_by")]
        if ixs:
            alerts.append(
                {
                    "alert_kind": "order_set",
                    "severity": "info",
                    "title": f"Order set for {d.get('label')}",
                    "explanation": "Investigations linked by investigated_by edges.",
                    "supporting": [{"disease": d.get("code"), "items": ixs}],
                    "contradictory": [],
                    "guideline_source": None,
                    "confidence": d.get("confidence"),
                    "body": {"items": ixs},
                }
            )

    # Care pathways + red flags + escalation
    for rf in ebs.get("red_flags") or []:
        alerts.append(
            {
                "alert_kind": "red_flag",
                "severity": "critical",
                "title": f"Red flag: {rf.get('label') or rf.get('code')}",
                "explanation": rf.get("detail") or "Triggered from knowledge pathway activation.",
                "supporting": [rf],
                "contradictory": [],
                "guideline_source": rf.get("guideline"),
                "confidence": "strong",
                "body": rf,
            }
        )
    for pw in ebs.get("active_pathways") or []:
        code = pw.get("code") if isinstance(pw, dict) else str(pw)
        ent = engine.entity(code)
        urgency = ((ent or {}).get("body") or {}).get("urgency") if ent else None
        alerts.append(
            {
                "alert_kind": "care_pathway",
                "severity": "critical" if urgency == "emergency" else "warning",
                "title": f"Care pathway: {(ent or {}).get('label') or code}",
                "explanation": "Active pathway from knowledge graph.",
                "supporting": [pw],
                "contradictory": [],
                "guideline_source": None,
                "confidence": "strong",
                "body": {"pathway": pw, "urgency": urgency},
            }
        )
        if urgency == "emergency":
            alerts.append(
                {
                    "alert_kind": "escalation",
                    "severity": "critical",
                    "title": f"Escalation suggested: {(ent or {}).get('label') or code}",
                    "explanation": "Emergency urgency on active pathway — advisory escalation only.",
                    "supporting": [pw],
                    "contradictory": [],
                    "guideline_source": None,
                    "confidence": "strong",
                    "body": {"pathway": code},
                }
            )

    return alerts


def refresh_cds_for_session(db: sqlite3.Connection, session_id: int) -> list[dict]:
    loaded = load_session(db, session_id)
    if not loaded:
        raise ValueError("Session not found")
    row, ebs = loaded
    engine = load_engine(db, row["release_id"])
    alerts = build_cds_bundle(engine, ebs)
    db.execute("UPDATE ckp_cds_alert SET status='superseded', updated_at=datetime('now') WHERE session_id=? AND status='active'", (session_id,))
    out = []
    for a in alerts:
        cur = db.execute(
            """INSERT INTO ckp_cds_alert
               (session_id, alert_kind, severity, title, explanation, supporting_json, contradictory_json,
                guideline_source, confidence, status, body_json)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (
                session_id,
                a["alert_kind"],
                a["severity"],
                a["title"],
                a.get("explanation"),
                json.dumps(a.get("supporting") or [], ensure_ascii=False),
                json.dumps(a.get("contradictory") or [], ensure_ascii=False),
                a.get("guideline_source"),
                a.get("confidence"),
                "active",
                json.dumps(a.get("body") or {}, ensure_ascii=False),
            ),
        )
        a["id"] = int(cur.lastrowid)
        out.append(a)
    db.commit()
    return out


def list_active_alerts(db: sqlite3.Connection, session_id: int) -> list[dict]:
    rows = db.execute(
        "SELECT * FROM ckp_cds_alert WHERE session_id=? AND status='active' ORDER BY CASE severity WHEN 'critical' THEN 0 WHEN 'warning' THEN 1 ELSE 2 END, id",
        (session_id,),
    ).fetchall()
    result = []
    for r in rows:
        d = dict(r)
        d["supporting"] = json.loads(d.pop("supporting_json") or "[]")
        d["contradictory"] = json.loads(d.pop("contradictory_json") or "[]")
        d["body"] = json.loads(d.pop("body_json") or "{}")
        result.append(d)
    return result
