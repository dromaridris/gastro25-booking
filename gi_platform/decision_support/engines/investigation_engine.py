"""Investigation support — baseline, advanced with escalation gates, duplicate avoidance."""

from __future__ import annotations

from gi_platform.decision_support.constants import (
    CONSIDERATION_LOW,
    CONSIDERATION_MODERATE,
    CONSIDERATION_STRONG,
    TIER_ADVANCED,
    TIER_BASELINE,
)
from gi_platform.decision_support.context import AssessmentContext, DifferentialItem, InvestigationRecommendation
from gi_platform.decision_support.engines.differential_engine import build_differential, top_diagnosis_codes
from gi_platform.decision_support.knowledge_accessor import CdsKnowledgeAccessor
from gi_platform.decision_support.variable_resolver import condition_met

DEFAULT_MIN_QUESTIONS_BEFORE_ESCALATION = 3


def _lab_already_present(
    investigation_code: str,
    accessor: CdsKnowledgeAccessor,
    context: AssessmentContext,
) -> tuple[bool, str | None]:
    inv = accessor.investigation(investigation_code)
    lab_code = None
    if inv:
        lab_code = inv.attributes.get("maps_to_lab_code")
    if not lab_code and investigation_code.startswith("lab."):
        lab_code = investigation_code
    if not lab_code or lab_code not in context.lab_values:
        return False, None

    flag = str(context.lab_values[lab_code])
    if flag.lower() == "normal":
        return True, f"Recent {lab_code} already normal — reconsider if clinically indicated."
    return False, f"Recent {lab_code} was {flag} — interpret in clinical context."


def _consideration_for(
    diagnosis_code: str,
    differential: list[DifferentialItem],
) -> str | None:
    for item in differential:
        if item.diagnosis_code == diagnosis_code:
            return item.consideration_level
    return None


def _advanced_escalation_allowed(
    context: AssessmentContext,
    rule_attrs: dict,
    diagnosis_code: str,
    differential: list[DifferentialItem],
) -> bool:
    if context.confirmed_diagnosis_code:
        return True

    escalation = rule_attrs.get("escalation_condition")
    if escalation and condition_met(context, escalation):
        return True

    min_answered = int(rule_attrs.get("min_questions_before_escalation", DEFAULT_MIN_QUESTIONS_BEFORE_ESCALATION))
    if len(context.answers) < min_answered:
        return False

    level = _consideration_for(diagnosis_code, differential)
    if level is None:
        return False
    if level == CONSIDERATION_LOW:
        return False
    if level in (CONSIDERATION_STRONG, CONSIDERATION_MODERATE):
        return True

    required = rule_attrs.get("required_consideration")
    if required and level != required:
        return False
    return level != CONSIDERATION_LOW


def _build_item(
    rule,
    tier: str,
    accessor: CdsKnowledgeAccessor,
    context: AssessmentContext,
    diagnosis_code: str | None = None,
) -> InvestigationRecommendation:
    inv_code = rule.attributes.get("investigation_code") or rule.stable_id
    skip, note = _lab_already_present(inv_code, accessor, context)
    return InvestigationRecommendation(
        investigation_stable_id=rule.stable_id,
        investigation_code=inv_code,
        tier=tier,
        reason=rule.attributes.get("reason") or rule.summary,
        linked_diagnosis_code=diagnosis_code or rule.attributes.get("diagnosis_code"),
        skip_suggested=skip,
        context_note=note,
    )


def recommend_investigations(
    context: AssessmentContext,
    accessor: CdsKnowledgeAccessor,
    differential: list[DifferentialItem] | None = None,
) -> list[InvestigationRecommendation]:
    complaint = context.complaint_code
    if differential is None:
        differential = build_differential(context, accessor)

    out: list[InvestigationRecommendation] = []
    seen: set[str] = set()

    for rule in accessor.baseline_investigations(complaint):
        inv_code = rule.attributes.get("investigation_code") or rule.stable_id
        if inv_code in seen:
            continue
        seen.add(inv_code)
        item = _build_item(rule, TIER_BASELINE, accessor, context)
        if not item.skip_suggested or item.context_note:
            out.append(item)

    dx_codes = (
        [context.confirmed_diagnosis_code]
        if context.confirmed_diagnosis_code
        else top_diagnosis_codes(context, accessor)
    )
    for dx in dx_codes:
        if not dx:
            continue
        for rule in accessor.advanced_investigations(complaint, dx):
            if not _advanced_escalation_allowed(context, rule.attributes, dx, differential):
                continue
            inv_code = rule.attributes.get("investigation_code") or rule.stable_id
            if inv_code in seen:
                continue
            seen.add(inv_code)
            out.append(_build_item(rule, TIER_ADVANCED, accessor, context, diagnosis_code=dx))

    return out
