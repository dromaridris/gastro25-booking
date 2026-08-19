"""Research engine — hypotheses / knowledge gaps from encounters and pack coverage."""

from __future__ import annotations

import json
import sqlite3
from typing import Any

from clinical_intelligence import knowledge_loader as kl


def analyze_gaps(
    complaint_code: str,
    *,
    scoring: dict | None = None,
    urgency_flag: str | None = None,
    answered_count: int = 0,
) -> dict[str, Any]:
    pack = kl.load_research_rules()
    if not pack:
        return {"available": False, "entries": [], "question_bank": []}

    entries = []
    for gap in pack.get("gap_checks") or []:
        when = gap.get("when")
        hit = False
        if when == "exam_template_missing" and not kl.load_exam_template(complaint_code):
            hit = True
        elif when == "reasoning_pack_missing" and not kl.load_reasoning_rules(complaint_code):
            hit = True
        elif when == "max_pattern_confidence_below":
            threshold = float(gap.get("threshold") or 0.45)
            patterns = (scoring or {}).get("pattern_scores") or []
            best = max((p.get("capped_confidence", p.get("confidence", 0)) or 0 for p in patterns), default=0)
            if answered_count >= 8 and best < threshold:
                hit = True
        elif when == "urgency_emergency" and urgency_flag == "emergency":
            hit = True

        if hit:
            title = gap.get("title")
            hyp = (gap.get("hypothesis_template") or "").format(complaint_code=complaint_code)
            entries.append(
                {
                    "id": gap.get("id"),
                    "kind": gap.get("kind"),
                    "priority": gap.get("priority"),
                    "title": title,
                    "hypothesis": hyp,
                }
            )

    qbank = [
        q
        for q in pack.get("question_bank") or []
        if complaint_code in (q.get("applies_to_complaints") or [complaint_code])
        or not q.get("applies_to_complaints")
    ]
    return {"available": True, "entries": entries, "question_bank": qbank}


def save_research_item(
    db: sqlite3.Connection,
    *,
    encounter_id: int | None,
    title: str,
    hypothesis: str,
    kind: str = "hypothesis",
    payload: dict | None = None,
    created_by: int | None = None,
) -> dict:
    cur = db.execute(
        """
        INSERT INTO ci_research_item
            (encounter_id, kind, title, hypothesis, payload_json, status, created_by, created_at)
        VALUES (?, ?, ?, ?, ?, 'open', ?, datetime('now'))
        """,
        (
            encounter_id,
            kind,
            title,
            hypothesis,
            json.dumps(payload or {}, ensure_ascii=False),
            created_by,
        ),
    )
    db.commit()
    row = db.execute("SELECT * FROM ci_research_item WHERE id = ?", (cur.lastrowid,)).fetchone()
    return dict(row)


def list_research_items(
    db: sqlite3.Connection,
    *,
    encounter_id: int | None = None,
    limit: int = 40,
) -> list[dict]:
    if encounter_id is not None:
        rows = db.execute(
            """
            SELECT * FROM ci_research_item
            WHERE encounter_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (encounter_id, limit),
        ).fetchall()
    else:
        rows = db.execute(
            """
            SELECT * FROM ci_research_item
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]
