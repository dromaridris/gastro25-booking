"""Resolve variable values from assessment context (answers, labs, demographics)."""

from __future__ import annotations

from typing import Any

from app.modules.decision_support.constants import (
    SOURCE_ANSWER,
    SOURCE_DEMOGRAPHIC,
    SOURCE_DIAGNOSIS,
    SOURCE_LAB,
)
from app.modules.decision_support.context import AssessmentContext


def _normalize(value: Any) -> str:
    return str(value or "").strip().lower()


def resolve_value(context: AssessmentContext, source_type: str, source_key: str) -> Any | None:
    if source_type == SOURCE_ANSWER:
        return context.answers.get(source_key)
    if source_type == SOURCE_LAB:
        return context.lab_values.get(source_key)
    if source_type == SOURCE_DEMOGRAPHIC:
        return context.demographics.get(source_key)
    if source_type == SOURCE_DIAGNOSIS:
        if source_key in context.existing_diagnoses:
            return source_key
        return None
    return None


def answer_matches(context: AssessmentContext, question_code: str, expected: str) -> bool:
    actual = context.answers.get(question_code)
    if actual is None:
        return False
    return _normalize(actual) == _normalize(expected)


def condition_met(context: AssessmentContext, condition: dict[str, Any]) -> bool:
    """Evaluate a structured condition from KL attributes."""
    if not condition:
        return True

    cond_type = condition.get("type", "answer")
    if cond_type == "answer":
        q = condition.get("question_code")
        expected = condition.get("answer")
        if not q or expected is None:
            return False
        return answer_matches(context, q, expected)

    if cond_type == "lab":
        key = condition.get("lab_code")
        op = condition.get("operator", "exists")
        val = context.lab_values.get(key) if key else None
        if op == "exists":
            return val is not None
        if op == "gte":
            return val is not None and float(val) >= float(condition.get("value", 0))
        if op == "lte":
            return val is not None and float(val) <= float(condition.get("value", 0))
        if op == "eq":
            return _normalize(val) == _normalize(condition.get("value"))
        if op == "flag":
            return _normalize(val) == _normalize(condition.get("value"))
        return False

    if cond_type == "demographic":
        key = condition.get("key")
        expected = condition.get("value")
        actual = context.demographics.get(key) if key else None
        if condition.get("operator") == "gte":
            return actual is not None and float(actual) >= float(expected)
        return _normalize(actual) == _normalize(expected)

    if cond_type == "diagnosis":
        code = condition.get("diagnosis_code")
        return code in context.existing_diagnoses if code else False

    if cond_type == "and":
        return all(condition_met(context, c) for c in condition.get("conditions", []))

    if cond_type == "or":
        return any(condition_met(context, c) for c in condition.get("conditions", []))

    return False
