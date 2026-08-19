"""Scoring engine — data-driven confidence from scoring + reasoning rule packs."""

from __future__ import annotations

from typing import Any

from clinical_intelligence import knowledge_loader as kl
from clinical_intelligence.conditions import eval_op
from clinical_intelligence.reasoning_engine import evaluate_patterns


def _band_for(score: float, bands: list[dict]) -> dict:
    for band in bands:
        if score <= float(band.get("max", 1.0)):
            return band
    return bands[-1] if bands else {"id": "unknown", "label": "Unknown"}


def score_encounter(
    complaint_code: str,
    answers: list[dict],
    findings: list[dict],
    *,
    reasoning: dict | None = None,
) -> dict[str, Any]:
    scoring = kl.load_scoring_rules(complaint_code)
    reasoning = reasoning or evaluate_patterns(complaint_code, answers, findings)

    if not scoring:
        # Fall back to reasoning confidence alone
        patterns = reasoning.get("patterns") or []
        best = max((p.get("confidence") or 0.0 for p in patterns), default=0.0)
        return {
            "available": bool(reasoning.get("available")),
            "source": "reasoning_fallback",
            "total_score": round(best, 3),
            "band": {"id": "fallback", "label": "Reasoning confidence only"},
            "components": {"best_pattern_confidence": best},
            "pattern_scores": patterns,
        }

    ans = {a["question_id"]: a.get("answer_text") for a in answers if not a.get("skipped")}
    exam = {f["sign_code"]: f.get("status") for f in findings if f.get("sign_code")}
    global_w = scoring.get("global") or {}
    completeness = scoring.get("completeness") or {}

    hist_keys = completeness.get("history_key_questions") or []
    exam_keys = completeness.get("exam_key_signs") or []
    hist_done = sum(1 for q in hist_keys if ans.get(q) not in (None, ""))
    exam_done = sum(1 for s in exam_keys if exam.get(s) in ("present", "absent"))
    hist_frac = (hist_done / len(hist_keys)) if hist_keys else 0.0
    exam_frac = (exam_done / len(exam_keys)) if exam_keys else 0.0

    patterns = reasoning.get("patterns") or []
    caps = scoring.get("pattern_score_caps") or {}
    capped = []
    best_pattern = 0.0
    for p in patterns:
        conf = float(p.get("confidence") or 0.0)
        if p.get("matched"):
            conf = max(conf, min(1.0, float(p.get("score") or 0) / max(float(p.get("required") or 1), 0.01)))
        cap = float(caps.get(p["id"], 1.0))
        val = min(conf, cap)
        capped.append({**p, "capped_confidence": round(val, 3)})
        if p.get("matched"):
            best_pattern = max(best_pattern, val)

    red_flag_hit = False
    template = kl.load_history_template(complaint_code) or {}
    for qid in template.get("red_flag_question_ids") or []:
        if eval_op(ans.get(qid), "truthy"):
            red_flag_hit = True
            break

    total = (
        float(global_w.get("history_completeness_weight", 0.25)) * hist_frac
        + float(global_w.get("exam_completeness_weight", 0.2)) * exam_frac
        + float(global_w.get("pattern_match_weight", 0.55)) * best_pattern
    )
    if red_flag_hit:
        total = min(float(global_w.get("max_total", 1.0)), total + float(global_w.get("red_flag_boost", 0.15)))
    total = min(float(global_w.get("max_total", 1.0)), total)
    band = _band_for(total, scoring.get("bands") or [])

    return {
        "available": True,
        "source": "scoring_pack",
        "total_score": round(total, 3),
        "band": band,
        "components": {
            "history_completeness": round(hist_frac, 3),
            "exam_completeness": round(exam_frac, 3),
            "best_pattern_confidence": round(best_pattern, 3),
            "red_flag_boost_applied": red_flag_hit,
        },
        "pattern_scores": capped,
        "disclaimer": "Scores support pattern confidence only — not a final diagnosis.",
    }
