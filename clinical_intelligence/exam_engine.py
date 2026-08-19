"""Physical Examination Engine — Phase 5.

Guides exam systems/findings from clinical_knowledge/templates/exam/.
"""

from __future__ import annotations

from typing import Any

from clinical_intelligence import knowledge_loader as kl


def exam_plan(complaint_code: str) -> dict[str, Any]:
    template = kl.load_exam_template(complaint_code)
    if not template:
        return {
            "complaint_code": complaint_code,
            "available": False,
            "message": "No exam template for this complaint yet.",
            "systems": [],
            "priority_findings": [],
        }
    signs = kl.load_sign_index()
    systems = []
    for sys in template.get("systems", []):
        findings = []
        for code in sys.get("finding_ids") or []:
            meta = signs.get(code, {"code": code, "label": code})
            findings.append(
                {
                    "code": code,
                    "label": meta.get("label", code),
                    "notes": meta.get("notes"),
                }
            )
        systems.append(
            {
                "key": sys.get("key"),
                "title": sys.get("title"),
                "checklist": sys.get("checklist") or [],
                "findings": findings,
            }
        )
    priority = []
    for code in template.get("priority_findings") or []:
        meta = signs.get(code, {"code": code, "label": code})
        priority.append({"code": code, "label": meta.get("label", code)})
    return {
        "complaint_code": complaint_code,
        "available": True,
        "name": template.get("name"),
        "systems": systems,
        "priority_findings": priority,
        "template": template,
    }


def exam_status_summary(plan: dict, findings: list[dict]) -> dict[str, Any]:
    by_code = {f["sign_code"]: f for f in findings if f.get("sign_code")}
    present = [f for f in findings if f.get("status") == "present"]
    absent = [f for f in findings if f.get("status") == "absent"]
    planned_codes = []
    for sys in plan.get("systems") or []:
        for finding in sys.get("findings") or []:
            planned_codes.append(finding["code"])
    missing = [c for c in planned_codes if c not in by_code or by_code[c].get("status") == "not_examined"]
    return {
        "documented": len(present) + len(absent),
        "present_count": len(present),
        "absent_count": len(absent),
        "missing_priority": [
            p for p in (plan.get("priority_findings") or []) if p["code"] in missing
        ],
        "present": present,
        "by_code": {k: v.get("status") for k, v in by_code.items()},
    }
