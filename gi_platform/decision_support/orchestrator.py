"""Decision Support orchestrator — runs all CDS engines in sequence."""

from __future__ import annotations

from gi_platform.decision_support.context import AssessmentContext, AssessmentResult
from gi_platform.decision_support.engines.adaptive_history_engine import recommend_next_questions
from gi_platform.decision_support.engines.differential_engine import build_differential
from gi_platform.decision_support.engines.guideline_engine import recommend_guidelines
from gi_platform.decision_support.engines.investigation_engine import recommend_investigations
from gi_platform.decision_support.engines.red_flag_engine import detect_red_flags
from gi_platform.decision_support.engines.score_engine import calculate_scores
from gi_platform.decision_support.engines.teaching_engine import build_teaching_insights
from gi_platform.decision_support.knowledge_accessor import CdsKnowledgeAccessor


class DecisionSupportOrchestrator:
    def __init__(self, accessor: CdsKnowledgeAccessor):
        self._accessor = accessor

    def assess(self, context: AssessmentContext) -> AssessmentResult:
        result = AssessmentResult(provider_key=self._accessor.provider_key)
        result.next_questions = recommend_next_questions(context, self._accessor)
        result.differential = build_differential(context, self._accessor)
        result.investigations = recommend_investigations(
            context, self._accessor, differential=result.differential,
        )
        result.scores = calculate_scores(context, self._accessor)
        result.red_flags = detect_red_flags(context, self._accessor)
        result.guidelines = recommend_guidelines(context, self._accessor)
        result.teaching = build_teaching_insights(context, self._accessor, result)
        return result
