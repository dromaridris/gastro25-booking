"""Education engine — teach-mode + passive coaching during history."""

from __future__ import annotations

from typing import Any

from clinical_intelligence import knowledge_loader as kl


def teaching_points(
    complaint_code: str,
    *,
    matched_patterns: set[str] | None = None,
    present_signs: set[str] | None = None,
    diagnosis_codes: set[str] | None = None,
) -> dict[str, Any]:
    pack = kl.load_education_rules(complaint_code)
    if not pack:
        return {"available": False, "modules": [], "message": "No education pack for complaint."}

    matched_patterns = matched_patterns or set()
    present_signs = present_signs or set()
    diagnosis_codes = diagnosis_codes or set()
    modules_out = []

    for mod in pack.get("modules") or []:
        trigger = mod.get("trigger") or {}
        show = False
        if trigger.get("always"):
            show = True
        if any(s in present_signs for s in (trigger.get("any_sign_present") or [])):
            show = True
        if any(p in matched_patterns for p in (trigger.get("any_pattern") or [])):
            show = True
        if any(d in diagnosis_codes for d in (trigger.get("any_diagnosis") or [])):
            show = True
        linked = set(mod.get("linked_diagnoses") or [])
        if linked & diagnosis_codes:
            show = True
        if not show:
            continue
        modules_out.append(
            {
                "id": mod.get("id"),
                "title": mod.get("title"),
                "points": mod.get("points") or [],
                "linked_questions": mod.get("linked_questions") or [],
                "linked_diagnoses": mod.get("linked_diagnoses") or [],
            }
        )

    return {
        "available": True,
        "modules": modules_out,
        "teach_mode": True,
        "disclaimer": "Teaching points from knowledge packs — for learning, not orders.",
    }


def _norm(s: Any) -> str:
    return str(s or "").strip().lower()


def _answer_triggers_hit(pack: dict, answers: dict[str, Any]) -> list[dict]:
    """Match answer_triggers in education pack (passive unlocks while interviewing)."""
    hits = []
    for rule in pack.get("answer_triggers") or []:
        qid = rule.get("question_id")
        if not qid:
            continue
        got = _norm(answers.get(qid))
        if not got:
            continue
        want_any = [_norm(x) for x in (rule.get("answer_contains_any") or [])]
        want_exact = [_norm(x) for x in (rule.get("answer_in") or [])]
        ok = False
        if want_exact and got in want_exact:
            ok = True
        if want_any and any(w in got for w in want_any if w):
            ok = True
        if not want_exact and not want_any and got in {"yes", "y", "true", "1"}:
            ok = True
        if ok:
            hits.append(rule)
    return hits


def coach_panel(
    complaint_code: str,
    *,
    focus_qid: str | None,
    answers: list[dict] | dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Passive-learning sidebar for the focused history question."""
    pack = kl.load_education_rules(complaint_code) or {}
    if isinstance(answers, list):
        amap = {a["question_id"]: a.get("answer_text") for a in answers if not a.get("skipped")}
    else:
        amap = dict(answers or {})

    coaching = (pack.get("question_coaching") or {}).get(focus_qid or "") or None
    focus_modules = []
    for mod in pack.get("modules") or []:
        linked = set(mod.get("linked_questions") or [])
        trigger = mod.get("trigger") or {}
        if focus_qid and focus_qid in linked:
            focus_modules.append(
                {"id": mod.get("id"), "title": mod.get("title"), "points": mod.get("points") or []}
            )
        elif trigger.get("always") and not focus_qid:
            focus_modules.append(
                {"id": mod.get("id"), "title": mod.get("title"), "points": mod.get("points") or []}
            )

    unlocked = []
    for rule in _answer_triggers_hit(pack, amap):
        unlocked.append(
            {
                "id": rule.get("id"),
                "title": rule.get("title"),
                "points": rule.get("points") or [],
                "from_question": rule.get("question_id"),
            }
        )

    # Always-on framing (first always module), short
    framing = None
    for mod in pack.get("modules") or []:
        if (mod.get("trigger") or {}).get("always"):
            framing = {
                "title": mod.get("title"),
                "points": (mod.get("points") or [])[:3],
            }
            break

    library = kl.load_question_library()
    q = library.get(focus_qid or "") or {}

    return {
        "available": bool(pack),
        "focus_qid": focus_qid,
        "focus_prompt": q.get("prompt"),
        "bates_domain": q.get("bates_domain"),
        "coaching": coaching,
        "focus_modules": focus_modules,
        "unlocked": unlocked,
        "framing": framing,
        "mode": "passive_learning",
        "disclaimer": "Learn while you ask — educational hints only, not clinical orders.",
    }
