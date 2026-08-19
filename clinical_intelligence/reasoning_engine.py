"""Reasoning Engine — data-driven patterns from JSON rule packs (no LLM diagnosis)."""

from __future__ import annotations

from typing import Any

from clinical_intelligence import knowledge_loader as kl
from clinical_intelligence.conditions import eval_op
from clinical_intelligence.history_engine import next_questions


def _answer_map(answers: list[dict]) -> dict[str, Any]:
    return {a["question_id"]: a.get("answer_text") for a in answers if not a.get("skipped")}


def _exam_map(findings: list[dict]) -> dict[str, Any]:
    return {f["sign_code"]: f.get("status") for f in findings if f.get("sign_code")}


def _criterion_hit(crit: dict, answers: dict, exam: dict) -> tuple[bool, float, str | None]:
    kind = crit.get("kind", "answer")
    weight = float(crit.get("weight") or 0)
    finding = crit.get("finding")
    if kind == "exam":
        ok = eval_op(exam.get(crit.get("sign_code")), crit.get("op", "present"), crit.get("value"))
    else:
        ok = eval_op(answers.get(crit.get("question_id")), crit.get("op", "eq"), crit.get("value"))
    return ok, (weight if ok else 0.0), (finding if ok else None)


def evaluate_patterns(complaint_code: str, answers: list[dict], findings: list[dict]) -> dict[str, Any]:
    rules = kl.load_reasoning_rules(complaint_code)
    if not rules:
        return {
            "available": False,
            "message": "No reasoning rule pack for this complaint.",
            "patterns": [],
            "diagnoses": [],
            "matched_pattern_ids": [],
            "missing_info": [],
            "next_questions": [],
            "next_exam": [],
            "next_investigations": [],
            "answered_count": 0,
            "min_history_answers_for_dx": 0,
            "dx_unlocked": False,
            "stop_rules": [],
        }

    ans = _answer_map(answers)
    exam = _exam_map(findings)
    min_answers = int(rules.get("min_history_answers_for_dx") or 0)
    min_conf = float(rules.get("min_confidence_to_list_dx") or 0.45)
    answered_n = len([v for v in ans.values() if v is not None and str(v).strip() != ""])

    pattern_rows = []
    matched_ids: set[str] = set()
    next_q: list[str] = []
    next_exam: list[str] = []
    next_ix: list[str] = []

    for pat in rules.get("patterns") or []:
        hits = []
        score = 0.0
        max_score = 0.0
        for crit in pat.get("criteria") or []:
            max_score += float(crit.get("weight") or 0)
            ok, w, finding = _criterion_hit(crit, ans, exam)
            if ok:
                score += w
                hits.append(finding or crit.get("finding") or crit.get("question_id") or crit.get("sign_code"))
        required = float(pat.get("weight_sum_required") or 1.0)
        confidence = (score / max_score) if max_score else 0.0
        matched = score >= required
        if matched:
            matched_ids.add(pat["id"])
        next_q.extend(pat.get("suggested_questions") or [])
        next_exam.extend(pat.get("suggested_exam") or [])
        next_ix.extend(pat.get("suggested_investigations") or [])
        pattern_rows.append(
            {
                "id": pat["id"],
                "label": pat.get("label"),
                "diagnosis_code": pat.get("diagnosis_code"),
                "diagnosis_label": pat.get("diagnosis_label"),
                "score": round(score, 2),
                "required": required,
                "confidence": round(confidence, 2),
                "matched": matched,
                "explain": hits,
            }
        )

    pattern_rows.sort(key=lambda r: (-r["confidence"], -r["score"]))

    diagnoses = []
    if answered_n >= min_answers:
        for row in pattern_rows:
            if row["matched"] and row["confidence"] >= min_conf:
                diagnoses.append(
                    {
                        "code": row["diagnosis_code"],
                        "label": row["diagnosis_label"],
                        "confidence": row["confidence"],
                        "pattern_id": row["id"],
                        "linked_findings": row["explain"],
                        "status": "suspect",
                    }
                )

    missing_info = []
    for rule in rules.get("missing_info_rules") or []:
        if "if_unanswered" in rule:
            need = [qid for qid in rule["if_unanswered"] if not ans.get(qid)]
            if need:
                missing_info.append({"id": rule["id"], "message": rule["message"], "next_questions": need})
                next_q.extend(need)
        if "if_unanswered_any" in rule:
            need = [qid for qid in rule["if_unanswered_any"] if not ans.get(qid)]
            if need:
                missing_info.append({"id": rule["id"], "message": rule["message"], "next_questions": need})
                next_q.extend(need)
        if "if_exam_missing_any" in rule:
            need = [
                code
                for code in rule["if_exam_missing_any"]
                if exam.get(code) in (None, "", "not_examined")
            ]
            if need:
                missing_info.append({"id": rule["id"], "message": rule["message"], "next_exam": need})
                next_exam.extend(need)

    # Prefer adaptive next from history engine for unanswered questions
    hist = next_questions(complaint_code, answers, limit=3)
    hist_next_ids = [q["id"] for q in hist.get("next") or []]

    def _unique(seq):
        seen = set()
        out = []
        for x in seq:
            if x and x not in seen:
                seen.add(x)
                out.append(x)
        return out

    library = kl.load_question_library()
    signs = kl.load_sign_index()
    ix_index = kl.load_investigation_index()

    return {
        "available": True,
        "answered_count": answered_n,
        "min_history_answers_for_dx": min_answers,
        "dx_unlocked": answered_n >= min_answers,
        "patterns": pattern_rows,
        "matched_pattern_ids": sorted(matched_ids),
        "diagnoses": diagnoses,
        "missing_info": missing_info,
        "next_questions": [
            {"id": qid, "prompt": library.get(qid, {}).get("prompt", qid)}
            for qid in _unique(hist_next_ids + next_q)[:8]
        ],
        "next_exam": [
            {"code": code, "label": signs.get(code, {}).get("label", code)}
            for code in _unique(next_exam)[:8]
        ],
        "next_investigations": [
            {"code": code, "label": ix_index.get(code, {}).get("label", code)}
            for code in _unique(next_ix)[:8]
        ],
        "stop_rules": hist.get("stop_rules") or [],
    }
