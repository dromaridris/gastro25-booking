"""Condition evaluator — Sprint 3D Structured Field Framework."""

from app.modules.clinical_reports.fields.payload import StructuredPayload
from app.modules.clinical_reports.fields.schema_types import Condition


def evaluate_condition(condition: Condition | None, payload: StructuredPayload) -> bool:
    if condition is None:
        return True
    if condition.when == "and":
        return all(evaluate_condition(c, payload) for c in condition.conditions)
    if condition.when == "or":
        return any(evaluate_condition(c, payload) for c in condition.conditions)
    if condition.when == "not":
        if not condition.conditions:
            return True
        return not evaluate_condition(condition.conditions[0], payload)
    if condition.when == "field" and condition.field_id:
        value = payload.get_field(condition.field_id)
        return _compare(value, condition.operator, condition.value)
    return True


def _compare(value, operator: str, expected) -> bool:
    if operator == "equals":
        return value == expected
    if operator == "not_equals":
        return value != expected
    if operator == "in":
        if isinstance(expected, (list, tuple, set)):
            return value in expected
        return value == expected
    if operator == "not_in":
        if isinstance(expected, (list, tuple, set)):
            return value not in expected
        return value != expected
    if operator == "empty":
        return _is_empty(value)
    if operator == "not_empty":
        return not _is_empty(value)
    return False


def _is_empty(value) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, (list, dict)):
        return len(value) == 0
    return False
