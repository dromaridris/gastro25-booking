"""Management framework — disposition/referral only (no drug prescriptions)."""

from __future__ import annotations

from typing import Any

from clinical_intelligence import knowledge_loader as kl
from clinical_intelligence.conditions import eval_group


def suggest_management(
    complaint_code: str,
    *,
    matched_patterns: set[str],
    answers: dict[str, Any] | None = None,
    exam: dict[str, Any] | None = None,
) -> dict[str, Any]:
    rules = kl.load_management_rules(complaint_code)
    if not rules:
        return {"available": False, "actions": []}

    answers = answers or {}
    exam = exam or {}
    actions_out = []
    has_emergency = False

    for action in rules.get("actions") or []:
        when = action.get("when") or {}
        if when.get("default_if_no_emergency"):
            continue  # handled after
        if eval_group(when, answers=answers, exam=exam, matched_patterns=matched_patterns):
            row = {
                "id": action.get("id"),
                "label": action.get("label"),
                "urgency": action.get("urgency"),
                "steps": action.get("steps") or [],
                "referral": action.get("referral"),
            }
            actions_out.append(row)
            if action.get("urgency") == "emergency":
                has_emergency = True

    if not has_emergency:
        for action in rules.get("actions") or []:
            when = action.get("when") or {}
            if when.get("default_if_no_emergency"):
                actions_out.append(
                    {
                        "id": action.get("id"),
                        "label": action.get("label"),
                        "urgency": action.get("urgency"),
                        "steps": action.get("steps") or [],
                        "referral": action.get("referral"),
                    }
                )

    urgency_rank = {"emergency": 0, "urgent": 1, "routine": 2}
    actions_out.sort(key=lambda a: urgency_rank.get(a.get("urgency"), 9))
    return {"available": True, "actions": actions_out, "has_emergency": has_emergency}
