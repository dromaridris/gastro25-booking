"""Teaching mode — trainee explanations (never for medico-legal output)."""

from __future__ import annotations

from app.modules.decision_support.constants import (
    CONSIDERATION_STRONG,
    DISPLAY_CONSIDERATION,
    PURPOSE_EXCLUDES,
)
from app.modules.decision_support.context import (
    AssessmentContext,
    AssessmentResult,
    TeachingInsight,
)
from app.modules.decision_support.engines.differential_engine import compute_weights
from app.modules.decision_support.knowledge_accessor import CdsKnowledgeAccessor
from app.modules.decision_support.variable_resolver import answer_matches


def build_teaching_insights(
    context: AssessmentContext,
    accessor: CdsKnowledgeAccessor,
    result: AssessmentResult,
) -> list[TeachingInsight]:
    if not context.teaching_mode:
        return []

    insights: list[TeachingInsight] = []

    weights = compute_weights(context, accessor)
    for dx in result.differential[:5]:
        if dx.consideration_level == CONSIDERATION_STRONG:
            insights.append(
                TeachingInsight(
                    category="differential",
                    message=(
                        f"{dx.name} is {DISPLAY_CONSIDERATION[dx.consideration_level].lower()} "
                        f"based on priors and supporting answers (internal weight {weights.get(dx.diagnosis_code, 0):.1f})."
                    ),
                    related_codes=[dx.diagnosis_code],
                )
            )

    for rule in accessor.weight_rules(context.complaint_code):
        q = rule.attributes.get("question_code")
        expected = rule.attributes.get("answer_match")
        dx = rule.attributes.get("diagnosis_code")
        delta = float(rule.attributes.get("weight_delta", 0))
        if not q or not dx or expected is None:
            continue
        if answer_matches(context, q, expected) and delta < 0:
            dx_obj = accessor.disease(dx)
            name = dx_obj.title if dx_obj else dx
            insights.append(
                TeachingInsight(
                    category="exclusion",
                    message=f'Answer "{expected}" to {q} reduced weight for {name}.',
                    related_codes=[dx, q],
                )
            )

    for inv in result.investigations:
        if inv.skip_suggested:
            continue
        insights.append(
            TeachingInsight(
                category="investigation",
                message=inv.reason or f"{inv.investigation_code} recommended for this presentation.",
                related_codes=[inv.investigation_code],
            )
        )

    for g in result.guidelines:
        insights.append(
            TeachingInsight(
                category="guideline",
                message=f"Guideline '{g.title}' supports current management considerations.",
                related_codes=[g.stable_id],
            )
        )

    for q in result.next_questions:
        if q.purpose == PURPOSE_EXCLUDES:
            insights.append(
                TeachingInsight(
                    category="history",
                    message=q.rationale or f"Next question ({q.question_code}) helps exclude competing diagnoses.",
                    related_codes=[q.question_code],
                )
            )

    return insights
