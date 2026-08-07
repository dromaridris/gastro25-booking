"""Branching engine — activation conditions driven by prior answers and differential state."""

from __future__ import annotations

import json

from app.modules.clinical_history.intelligence.catalog_provider import get_catalog_provider
from app.modules.clinical_history.models import HistoryAnswer


def _normalize(value: str) -> str:
    return (value or "").strip().lower()


def answer_map(session_id: int) -> dict[str, str]:
    rows = HistoryAnswer.query.filter_by(session_id=session_id, is_archived=False).all()
    return {r.question_code: _normalize(r.answer_value) for r in rows}


def _check_clause(clause: dict, answers: dict[str, str]) -> bool:
    qcode = clause.get("q") or clause.get("question")
    expected = _normalize(clause.get("a") or clause.get("answer", ""))
    actual = answers.get(qcode)
    if actual is None:
        return False
    return actual == expected


def evaluate_activation_json(activation_json: str | None, answers: dict[str, str]) -> bool:
    if not activation_json:
        return True
    try:
        spec = json.loads(activation_json)
    except json.JSONDecodeError:
        return True

    all_clauses = spec.get("all", [])
    any_clauses = spec.get("any", [])
    not_clauses = spec.get("not", [])

    if all_clauses and not all(_check_clause(c, answers) for c in all_clauses):
        return False
    if any_clauses and not any(_check_clause(c, answers) for c in any_clauses):
        return False
    if not_clauses and any(_check_clause(c, answers) for c in not_clauses):
        return False
    return True


def evaluate_differential_gate(
    rule,
    differential: dict[str, float],
) -> bool:
    """Optional gates: show only when certain diagnoses are in contention."""
    if not rule.show_when_differential_includes:
        if not rule.hide_when_differential_below:
            return True
    top = sorted(differential.items(), key=lambda x: x[1], reverse=True)
    top_codes = [c for c, w in top[:5] if w > 0]

    if rule.show_when_differential_includes:
        targets = json.loads(rule.show_when_differential_includes)
        if not any(t in top_codes for t in targets):
            return False

    if rule.hide_when_differential_below:
        threshold = float(rule.hide_when_differential_below)
        gated = json.loads(rule.gate_diagnosis_codes_json or "[]")
        for code in gated:
            if differential.get(code, 0) >= threshold:
                return False
    return True


def evaluate_activation(
    rule,
    session_id: int,
    differential: dict[str, float] | None = None,
) -> bool:
    answers = answer_map(session_id)

    # Legacy parent fields (backward compatible)
    if rule.parent_question_code:
        parent_val = answers.get(rule.parent_question_code)
        if parent_val is None:
            return False
        if rule.parent_answer_required is not None:
            if parent_val != _normalize(rule.parent_answer_required):
                return False

    if not evaluate_activation_json(rule.activation_json, answers):
        return False

    if differential is not None:
        if not evaluate_differential_gate(rule, differential):
            return False

    return True


def get_visible_question_codes(
    complaint_code: str,
    session_id: int,
    differential: dict[str, float] | None = None,
) -> list[str]:
    provider = get_catalog_provider()
    rules = provider.question_rules_for_complaint(complaint_code)
    visible: list[str] = []
    for rule in rules:
        if evaluate_activation(rule, session_id, differential=differential):
            visible.append(rule.question_code)
    return visible
