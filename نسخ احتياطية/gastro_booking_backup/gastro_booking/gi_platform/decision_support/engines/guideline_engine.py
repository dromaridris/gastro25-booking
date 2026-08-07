"""Guideline support — concise recommendations from Knowledge Library."""

from __future__ import annotations

from gi_platform.decision_support.constants import CONSIDERATION_STRONG
from gi_platform.decision_support.context import AssessmentContext, GuidelineRecommendation
from gi_platform.decision_support.engines.differential_engine import build_differential
from gi_platform.decision_support.knowledge_accessor import CdsKnowledgeAccessor


def _concise_summary(guideline) -> str:
    if guideline.summary:
        text = guideline.summary.strip()
    elif guideline.body:
        text = guideline.body.strip()
    else:
        return guideline.title
    if len(text) > 280:
        return text[:277].rstrip() + "..."
    return text


def recommend_guidelines(
    context: AssessmentContext,
    accessor: CdsKnowledgeAccessor,
) -> list[GuidelineRecommendation]:
    differential = build_differential(context, accessor)
    strong = [d.diagnosis_code for d in differential if d.consideration_level == CONSIDERATION_STRONG]
    if context.confirmed_diagnosis_code:
        strong = [context.confirmed_diagnosis_code]

    seen: set[str] = set()
    out: list[GuidelineRecommendation] = []
    for dx_code in strong[:3]:
        for g in accessor.guidelines_for_diagnosis(dx_code):
            if g.stable_id in seen:
                continue
            seen.add(g.stable_id)
            refs = accessor.references_for_object(g.stable_id)
            out.append(
                GuidelineRecommendation(
                    stable_id=g.stable_id,
                    topic_key=g.topic_key or g.stable_id,
                    title=g.title,
                    summary=_concise_summary(g),
                    full_reference_stable_id=refs[0].stable_id if refs else None,
                )
            )
    return out
