"""Adaptive history engine — recommend next highest-value clinical question."""

from __future__ import annotations

from app.modules.decision_support.constants import (
    PURPOSE_ALARM,
    PURPOSE_CONTEXTUAL,
    PURPOSE_EXCLUDES,
    PURPOSE_RISK,
    PURPOSE_SUPPORTS,
)
from app.modules.decision_support.context import AssessmentContext, QuestionRecommendation
from app.modules.decision_support.engines.branch_engine import active_branches, question_branch_visible
from app.modules.decision_support.engines.differential_engine import compute_weights, top_diagnosis_codes
from app.modules.decision_support.knowledge_accessor import CdsKnowledgeAccessor
from app.modules.decision_support.variable_resolver import condition_met


def _is_visible(rule_attrs: dict, context: AssessmentContext, accessor: CdsKnowledgeAccessor) -> bool:
    branch = rule_attrs.get("branch_code")
    if not question_branch_visible(branch, context, accessor):
        return False

    visible_if = rule_attrs.get("visible_if")
    if not visible_if:
        return True
    if isinstance(visible_if, list):
        return all(condition_met(context, c) for c in visible_if)
    return condition_met(context, visible_if)


def _discrimination_score(
    question_code: str,
    context: AssessmentContext,
    accessor: CdsKnowledgeAccessor,
    weights: dict[str, float],
) -> float:
    """
    Estimate how effectively a question separates competing diagnoses.

    Prefers questions whose answers boost one leading diagnosis while reducing another.
    """
    rules = [
        r for r in accessor.weight_rules(context.complaint_code)
        if r.attributes.get("question_code") == question_code
    ]
    if not rules:
        return 0.0

    ranked = sorted(weights.items(), key=lambda x: x[1], reverse=True)
    top_codes = [c for c, w in ranked[:5] if w > 0]
    if len(top_codes) < 2:
        return sum(abs(float(r.attributes.get("weight_delta", 0))) for r in rules)

    by_answer: dict[str, list[tuple[str, float]]] = {}
    for rule in rules:
        ans = str(rule.attributes.get("answer_match", ""))
        dx = rule.attributes.get("diagnosis_code")
        delta = float(rule.attributes.get("weight_delta", 0))
        if dx:
            by_answer.setdefault(ans, []).append((dx, delta))

    best = 0.0
    for effects in by_answer.values():
        boosted = {dx for dx, d in effects if d > 0 and dx in top_codes}
        reduced = {dx for dx, d in effects if d < 0 and dx in top_codes}
        magnitude = sum(abs(d) for _, d in effects)
        if boosted and reduced:
            best = max(best, magnitude)
        elif boosted and len(top_codes) > 1:
            best = max(best, magnitude * 0.75)
    return best


def _foundation_boost(
    rule_attrs: dict,
    context: AssessmentContext,
    accessor: CdsKnowledgeAccessor,
) -> float:
    """Boost questions that unlock interview branches — e.g. duration before malabsorption workup."""
    q_code = rule_attrs.get("question_code")
    for rule in accessor.branch_activation_rules(context.complaint_code):
        condition = rule.attributes.get("condition") or {}
        if condition.get("type") != "answer":
            continue
        if condition.get("question_code") != q_code:
            continue
        branch = rule.attributes.get("branch_code")
        if branch and branch not in active_branches(context, accessor):
            return 5.0
    if rule_attrs.get("interview_phase") == "foundation":
        return 3.0
    return 0.0


def _diagnostic_value(
    rule_attrs: dict,
    top_dx: list[str],
    discrimination: float,
    context: AssessmentContext,
    accessor: CdsKnowledgeAccessor,
) -> float:
    weight_rules = rule_attrs.get("_weight_rule_count", 0)
    value = float(weight_rules) * 0.5 if weight_rules else 0.1
    value += discrimination * 2.5

    targets = rule_attrs.get("target_diagnosis_codes") or []
    overlap = len(set(targets) & set(top_dx))
    value += overlap * 2.0

    purpose = rule_attrs.get("question_purpose", PURPOSE_CONTEXTUAL)
    if purpose in (PURPOSE_ALARM, PURPOSE_EXCLUDES):
        value += 1.5

    value *= float(rule_attrs.get("differential_priority", 1.0))
    value += _foundation_boost(rule_attrs, context, accessor)
    return value


def _purpose_hint(purpose: str, rationale: str | None) -> str:
    if purpose == PURPOSE_ALARM:
        return "Alarm feature — important to exclude serious pathology."
    if purpose == PURPOSE_EXCLUDES:
        return "Helps exclude competing diagnoses in the differential."
    if purpose == PURPOSE_SUPPORTS:
        return "Supports or weakens specific diagnoses under consideration."
    if purpose == PURPOSE_RISK:
        return "Identifies risk factors relevant to the presenting complaint."
    return rationale or "Clinically relevant to the presenting complaint."


def _eligible_questions(
    context: AssessmentContext,
    accessor: CdsKnowledgeAccessor,
) -> list[tuple[str, dict]]:
    answered = context.answered_question_codes or set(context.answers.keys())
    weight_rule_counts: dict[str, int] = {}
    for rule in accessor.weight_rules(context.complaint_code):
        q = rule.attributes.get("question_code")
        if q:
            weight_rule_counts[q] = weight_rule_counts.get(q, 0) + 1

    candidates: list[tuple[str, dict]] = []
    for rule in accessor.question_rules(context.complaint_code):
        attrs = dict(rule.attributes)
        q_code = attrs.get("question_code") or rule.stable_id
        if q_code in answered:
            continue
        if not _is_visible(attrs, context, accessor):
            continue
        attrs["_weight_rule_count"] = weight_rule_counts.get(q_code, 0)
        candidates.append((q_code, attrs))
    return candidates


def interview_has_pending_questions(
    context: AssessmentContext,
    accessor: CdsKnowledgeAccessor,
) -> bool:
    return bool(_eligible_questions(context, accessor))


def recommend_next_questions(
    context: AssessmentContext,
    accessor: CdsKnowledgeAccessor,
    batch_size: int = 1,
) -> list[QuestionRecommendation]:
    top_dx = top_diagnosis_codes(context, accessor)
    weights = compute_weights(context, accessor)
    candidates = _eligible_questions(context, accessor)

    scored: list[tuple[str, dict, float, bool]] = []
    for q_code, attrs in candidates:
        discrimination = _discrimination_score(q_code, context, accessor, weights)
        score = _diagnostic_value(attrs, top_dx, discrimination, context, accessor)
        unlocks = _foundation_boost(attrs, context, accessor) > 0
        scored.append((q_code, attrs, score, unlocks))

    scored.sort(key=lambda x: (not x[3], -x[2]))
    selected = scored[:batch_size]

    out: list[QuestionRecommendation] = []
    for q_code, attrs, score, _unlocks in selected:
        purpose = attrs.get("question_purpose", PURPOSE_CONTEXTUAL)
        prompt = attrs.get("prompt") or accessor.question_prompt(q_code)
        out.append(
            QuestionRecommendation(
                question_stable_id=attrs.get("stable_id", q_code),
                question_code=q_code,
                prompt=prompt,
                diagnostic_value=round(score, 2),
                purpose=purpose,
                rationale=_purpose_hint(purpose, attrs.get("clinical_rationale")),
            )
        )
    return out
