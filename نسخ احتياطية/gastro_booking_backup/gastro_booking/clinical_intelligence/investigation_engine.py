"""Investigation framework — names/urgency from JSON (no interpretation)."""

from __future__ import annotations

from typing import Any

from clinical_intelligence import knowledge_loader as kl
from clinical_intelligence.conditions import eval_group


def suggest_investigations(
    complaint_code: str,
    *,
    answers: dict[str, Any],
    exam: dict[str, Any],
    matched_patterns: set[str] | None = None,
) -> dict[str, Any]:
    rules = kl.load_investigation_rules(complaint_code)
    if not rules:
        return {"available": False, "bundles": [], "entries": []}

    matched_patterns = matched_patterns or set()
    ix_index = kl.load_investigation_index()
    bundles_out = []
    by_code: dict[str, dict] = {}

    for bundle in rules.get("bundles") or []:
        when = bundle.get("when") or {}
        if not eval_group(when, answers=answers, exam=exam, matched_patterns=matched_patterns):
            continue
        codes = bundle.get("investigations") or []
        resolved = []
        for code in codes:
            meta = ix_index.get(code, {"code": code, "label": code})
            row = {
                "code": code,
                "label": meta.get("label", code),
                "category": meta.get("category"),
                "urgency": bundle.get("urgency", "routine"),
                "bundle_id": bundle.get("id"),
            }
            resolved.append(row)
            prev = by_code.get(code)
            urgency_rank = {"emergency": 0, "urgent": 1, "routine": 2, "elective": 3}
            if not prev or urgency_rank.get(row["urgency"], 9) < urgency_rank.get(prev["urgency"], 9):
                by_code[code] = row
        bundles_out.append(
            {
                "id": bundle.get("id"),
                "label": bundle.get("label"),
                "urgency": bundle.get("urgency"),
                "referral_hint": bundle.get("referral_hint"),
                "investigations": resolved,
            }
        )

    ordered = sorted(
        by_code.values(),
        key=lambda r: ({"emergency": 0, "urgent": 1, "routine": 2}.get(r["urgency"], 9), r["label"]),
    )
    return {"available": True, "bundles": bundles_out, "entries": ordered}
