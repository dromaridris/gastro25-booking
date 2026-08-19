"""Differential diagnosis engine — KL-backed priors and weight rules."""

from __future__ import annotations

from gi_platform.decision_support.constants import (
    CONSIDERATION_LOW,
    CONSIDERATION_MODERATE,
    CONSIDERATION_STRONG,
    DISPLAY_CONSIDERATION,
)
from gi_platform.decision_support.context import AssessmentContext, DifferentialItem
from gi_platform.decision_support.knowledge_accessor import CdsKnowledgeAccessor
from gi_platform.decision_support.variable_resolver import answer_matches


def _normalize(value: str) -> str:
    return (value or "").strip().lower()


def compute_weights(context: AssessmentContext, accessor: CdsKnowledgeAccessor) -> dict[str, float]:
    complaint = context.complaint_code
    weights: dict[str, float] = {}

    for prior in accessor.differential_priors(complaint):
        code = prior.attributes.get("diagnosis_code")
        if code:
            weights[code] = float(prior.attributes.get("prior_weight", 0))

    for rule in accessor.weight_rules(complaint):
        code = rule.attributes.get("diagnosis_code")
        if code:
            weights.setdefault(code, 0.0)

    for rule in accessor.weight_rules(complaint):
        q = rule.attributes.get("question_code")
        expected = rule.attributes.get("answer_match")
        code = rule.attributes.get("diagnosis_code")
        delta = float(rule.attributes.get("weight_delta", 0))
        if not q or not code or expected is None:
            continue
        if answer_matches(context, q, expected):
            weights[code] = weights.get(code, 0.0) + delta

    return weights


def _weight_to_consideration(weight: float, max_weight: float) -> str:
    if weight <= 0 or max_weight <= 0:
        return CONSIDERATION_LOW
    ratio = weight / max_weight
    if ratio >= 0.75:
        return CONSIDERATION_STRONG
    if ratio >= 0.4:
        return CONSIDERATION_MODERATE
    return CONSIDERATION_LOW


def build_differential(
    context: AssessmentContext,
    accessor: CdsKnowledgeAccessor,
) -> list[DifferentialItem]:
    raw = compute_weights(context, accessor)
    if not raw:
        return []

    max_w = max(raw.values())
    items: list[DifferentialItem] = []
    for code, weight in sorted(raw.items(), key=lambda x: x[1], reverse=True):
        if weight <= 0 and max_w > 0:
            continue
        dx = accessor.disease(code)
        level = _weight_to_consideration(weight, max_w)
        items.append(
            DifferentialItem(
                diagnosis_stable_id=dx.stable_id if dx else code,
                diagnosis_code=code,
                name=dx.title if dx else code,
                consideration_level=level,
                consideration_label=DISPLAY_CONSIDERATION[level],
            )
        )
    return items[:12]


def top_diagnosis_codes(context: AssessmentContext, accessor: CdsKnowledgeAccessor, limit: int = 5) -> list[str]:
    raw = compute_weights(context, accessor)
    ranked = sorted(((k, v) for k, v in raw.items() if v > 0), key=lambda x: x[1], reverse=True)
    return [code for code, _ in ranked[:limit]]
