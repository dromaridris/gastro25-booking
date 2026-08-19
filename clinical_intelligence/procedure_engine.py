"""Procedure engine — indications/prep/risks from dictionary + complaint procedure rules."""

from __future__ import annotations

from typing import Any

from clinical_intelligence import knowledge_loader as kl
from clinical_intelligence.conditions import eval_group
from clinical_intelligence.modules import gi_overlay


def suggest_procedures(
    complaint_code: str,
    *,
    answers: dict[str, Any],
    exam: dict[str, Any],
    matched_patterns: set[str] | None = None,
) -> dict[str, Any]:
    rules = kl.load_procedure_rules(complaint_code)
    procedures = kl.load_procedure_index()
    if not rules:
        return {
            "available": False,
            "entries": [],
            "message": "No procedure rule pack for this complaint.",
        }

    matched_patterns = matched_patterns or set()
    entries = []
    for sug in rules.get("suggestions") or []:
        when = sug.get("when") or {}
        if not eval_group(when, answers=answers, exam=exam, matched_patterns=matched_patterns):
            continue
        code = sug.get("procedure_code")
        meta = procedures.get(code, {"code": code, "label": code})
        row = {
            "id": sug.get("id"),
            "procedure_code": code,
            "label": meta.get("label", code),
            "urgency": sug.get("urgency"),
            "indications": sug.get("indications") or [],
            "prep": sug.get("prep") or [],
            "risks": sug.get("risks") or [],
            "gi_booking_hint": sug.get("gi_booking_hint"),
            "status": meta.get("status"),
        }
        # Light GI endoscopy hook
        if sug.get("gi_booking_hint"):
            row["gi_overlay"] = {
                "booking_procedure_hint": sug["gi_booking_hint"],
                "hint": "Use existing endoscopy booking/report modules when scheduling.",
            }
            # Map to IX overlay if EGD/colonoscopy
            if code == "PR_egd":
                row["related_investigation"] = "IX_upper_endoscopy"
            elif code == "PR_colonoscopy":
                row["related_investigation"] = "IX_colonoscopy"
        entries.append(row)

    urgency_rank = {"emergency": 0, "urgent": 1, "elective_to_urgent": 2, "elective": 3}
    entries.sort(key=lambda r: urgency_rank.get(r.get("urgency") or "", 9))
    return {
        "available": True,
        "entries": entries,
        "gi_note": gi_overlay.GI_ENDOSCOPY_LINKS,
        "disclaimer": "Procedure suggestions are knowledge-driven indications — not a booking order.",
    }
