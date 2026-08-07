"""Shared condition evaluation for JSON rule packs."""

from __future__ import annotations

from typing import Any


def _normalize_boolish(value: Any) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"yes", "y", "true", "1", "present", "positive"}:
        return True
    if text in {"no", "n", "false", "0", "absent", "negative", "not_examined", ""}:
        return False
    return None


def eval_op(actual: Any, op: str, expected: Any = None) -> bool:
    op = (op or "eq").lower()
    if op == "eq":
        return str(actual).strip().lower() == str(expected).strip().lower()
    if op == "neq":
        return str(actual).strip().lower() != str(expected).strip().lower()
    if op == "in":
        values = expected if isinstance(expected, (list, tuple, set)) else [expected]
        return str(actual).strip().lower() in {str(v).strip().lower() for v in values}
    if op == "truthy":
        flag = _normalize_boolish(actual)
        return flag is True
    if op == "falsy":
        flag = _normalize_boolish(actual)
        return flag is False
    if op == "present":
        return str(actual).strip().lower() in {"present", "yes", "positive", "true", "1"}
    if op == "absent":
        return str(actual).strip().lower() in {"absent", "no", "negative", "false", "0"}
    if op == "answered":
        return actual is not None and str(actual).strip() != ""
    return False


def eval_condition(cond: dict, *, answers: dict[str, Any], exam: dict[str, Any], matched_patterns: set[str] | None = None) -> bool:
    """Evaluate a single condition dict used across branching / reasoning / ix / mgmt."""
    matched_patterns = matched_patterns or set()
    if "pattern_id" in cond and "question_id" not in cond and "sign_code" not in cond:
        return cond["pattern_id"] in matched_patterns
    if cond.get("always_if_complaint"):
        return True
    if cond.get("default_if_no_emergency"):
        return True  # caller filters emergencies

    kind = cond.get("kind")
    if kind == "exam" or "sign_code" in cond:
        sign = cond.get("sign_code")
        return eval_op(exam.get(sign), cond.get("op", "present"), cond.get("value"))
    if kind == "answer" or "question_id" in cond:
        qid = cond.get("question_id")
        return eval_op(answers.get(qid), cond.get("op", "eq"), cond.get("value"))
    return False


def eval_group(group: dict | None, *, answers: dict[str, Any], exam: dict[str, Any], matched_patterns: set[str] | None = None) -> bool:
    if not group:
        return True
    if "if_all" in group:
        return all(eval_condition(c, answers=answers, exam=exam, matched_patterns=matched_patterns) for c in group["if_all"])
    if "if_any" in group:
        return any(eval_condition(c, answers=answers, exam=exam, matched_patterns=matched_patterns) for c in group["if_any"])
    if "any" in group:
        return any(eval_condition(c, answers=answers, exam=exam, matched_patterns=matched_patterns) for c in group["any"])
    if "all" in group:
        return all(eval_condition(c, answers=answers, exam=exam, matched_patterns=matched_patterns) for c in group["all"])
    if "any_pattern" in group:
        return bool(set(group["any_pattern"]) & (matched_patterns or set()))
    # bare condition
    if any(k in group for k in ("question_id", "sign_code", "pattern_id", "kind", "always_if_complaint")):
        return eval_condition(group, answers=answers, exam=exam, matched_patterns=matched_patterns)
    return True
