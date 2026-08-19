"""Question selector — differential-driven progressive interview (one question at a time)."""

from __future__ import annotations

import json

from app.modules.clinical_history.intelligence.branching_engine import (
    answer_map,
    get_visible_question_codes,
)
from app.modules.clinical_history.intelligence.catalog_provider import get_catalog_provider
from app.modules.clinical_history.intelligence.differential_engine import compute_differential
from app.modules.clinical_history.models import ANSWER_TYPE_TEXT, HistoryAnswer

PURPOSE_ALARM = "alarm"
PURPOSE_EXCLUDES = "excludes"
PURPOSE_SUPPORTS = "supports"
PURPOSE_CONTEXTUAL = "contextual"
PURPOSE_RISK = "risk_factor"


def _is_required_for_completion(question) -> bool:
    """Free-text context questions are optional during the adaptive interview."""
    return getattr(question, "answer_type", None) != ANSWER_TYPE_TEXT


def _resolvable_pending_codes(complaint_code: str, session_id: int, pending_codes: list[str]) -> list[str]:
    provider = get_catalog_provider()
    resolved: list[str] = []
    for code in pending_codes:
        question = provider.get_question(code)
        if question is not None:
            resolved.append(code)
    return resolved


def _required_pending_codes(complaint_code: str, session_id: int) -> list[str]:
    differential = compute_differential(complaint_code, session_id)
    visible_codes = get_visible_question_codes(complaint_code, session_id, differential=differential)
    answered = {
        a.question_code
        for a in HistoryAnswer.query.filter_by(session_id=session_id, is_archived=False)
    }
    pending = [c for c in visible_codes if c not in answered]
    provider = get_catalog_provider()
    required: list[str] = []
    for code in pending:
        question = provider.get_question(code)
        if question is None:
            continue
        if _is_required_for_completion(question):
            required.append(code)
    return required


def _diagnostic_value(
    complaint_code: str,
    question_code: str,
    top_dx: list[str],
) -> float:
    """Score unanswered question by potential to narrow the differential."""
    provider = get_catalog_provider()
    rules = provider.weight_rules_for_question(complaint_code, question_code)
    if not rules:
        return 0.1

    value = sum(abs(r.weight_delta) for r in rules)

    rule = next(
        (r for r in provider.question_rules_for_complaint(complaint_code) if r.question_code == question_code),
        None,
    )
    if rule and rule.target_diagnosis_codes_json:
        targets = json.loads(rule.target_diagnosis_codes_json)
        overlap = len(set(targets) & set(top_dx))
        value += overlap * 2.0

    if rule and rule.question_purpose in (PURPOSE_ALARM, PURPOSE_EXCLUDES):
        value += 1.5

    value *= float(rule.differential_priority or 1.0) if rule else 1.0
    return value


def get_next_questions(
    complaint_code: str,
    session_id: int,
    batch_size: int = 1,
) -> list:
    """
    Return the highest-value unanswered questions for narrowing the differential.
    Default batch_size=1 — physician never sees the full questionnaire at once.
    """
    differential = compute_differential(complaint_code, session_id)
    visible_codes = get_visible_question_codes(complaint_code, session_id, differential=differential)

    answered = {
        a.question_code
        for a in HistoryAnswer.query.filter_by(session_id=session_id, is_archived=False)
    }
    pending_codes = [c for c in visible_codes if c not in answered]
    pending_codes = _resolvable_pending_codes(complaint_code, session_id, pending_codes)
    provider = get_catalog_provider()
    pending_codes = [
        c
        for c in pending_codes
        if _is_required_for_completion(provider.get_question(c))
    ]
    if not pending_codes:
        return []

    top_dx = sorted(differential.items(), key=lambda x: x[1], reverse=True)[:5]
    top_dx_codes = [c for c, w in top_dx if w > 0]

    scored = [
        (code, _diagnostic_value(complaint_code, code, top_dx_codes))
        for code in pending_codes
    ]
    scored.sort(key=lambda x: x[1], reverse=True)
    selected = [code for code, _ in scored[:batch_size]]

    questions = []
    for code in selected:
        q = provider.get_question(code)
        if q is not None:
            questions.append(q)
    order = {code: idx for idx, code in enumerate(selected)}
    return sorted(questions, key=lambda q: order.get(q.code, 999))


def question_purpose_hint(complaint_code: str, question_code: str, session_id: int) -> str:
    """Teaching-oriented hint shown during interview — why this question matters."""
    provider = get_catalog_provider()
    rule = next(
        (r for r in provider.question_rules_for_complaint(complaint_code) if r.question_code == question_code),
        None,
    )
    if not rule:
        return "Helps refine the differential diagnosis."

    purpose = rule.question_purpose or PURPOSE_CONTEXTUAL
    if purpose == PURPOSE_ALARM:
        return "Alarm feature — important to exclude serious pathology."
    if purpose == PURPOSE_EXCLUDES:
        return "Helps exclude competing diagnoses in the differential."
    if purpose == PURPOSE_SUPPORTS:
        return "Supports or weakens specific diagnoses under consideration."
    if purpose == PURPOSE_RISK:
        return "Identifies risk factors relevant to the presenting complaint."
    return rule.clinical_rationale or "Clinically relevant to the presenting complaint."


def interview_complete(complaint_code: str, session_id: int) -> bool:
    return len(_required_pending_codes(complaint_code, session_id)) == 0
