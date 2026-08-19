"""Clinical Interview Driver — active, step-by-step history taking."""

from __future__ import annotations

from app.modules.decision_support.context import AssessmentContext, AssessmentResult, InterviewStepResult
from app.modules.decision_support.engines.adaptive_history_engine import (
    interview_has_pending_questions,
    recommend_next_questions,
)
from app.modules.decision_support.engines.branch_engine import active_branches
from app.modules.decision_support.engines.differential_engine import build_differential
from app.modules.decision_support.engines.guideline_engine import recommend_guidelines
from app.modules.decision_support.engines.investigation_engine import recommend_investigations
from app.modules.decision_support.engines.red_flag_engine import detect_red_flags
from app.modules.decision_support.engines.score_engine import calculate_scores
from app.modules.decision_support.engines.teaching_engine import build_teaching_insights
from app.modules.decision_support.knowledge_accessor import CdsKnowledgeAccessor
from app.modules.knowledge_library.interfaces import KnowledgeProvider
from app.modules.knowledge_library.provider_factory import get_knowledge_provider


class ClinicalInterviewDriver:
    """
    Active interview orchestrator — recalculates CDS after every physician answer.

    The physician may ignore any recommendation; the engine adapts continuously.
    """

    def __init__(self, provider: KnowledgeProvider | None = None):
        self._provider = provider or get_knowledge_provider()

    def _sync_answered(self, context: AssessmentContext) -> None:
        if not context.answered_question_codes:
            context.answered_question_codes = set(context.answers.keys())
        else:
            context.answered_question_codes.update(context.answers.keys())

    def advance(self, context: AssessmentContext) -> InterviewStepResult:
        """Recalculate full CDS state and determine the next highest-yield question."""
        self._sync_answered(context)
        accessor = CdsKnowledgeAccessor(self._provider)

        differential = build_differential(context, accessor)
        investigations = recommend_investigations(context, accessor, differential=differential)
        red_flags = detect_red_flags(context, accessor)
        scores = calculate_scores(context, accessor)
        guidelines = recommend_guidelines(context, accessor)
        branches = active_branches(context, accessor)
        next_questions = recommend_next_questions(context, accessor, batch_size=1)
        complete = not interview_has_pending_questions(context, accessor)

        assessment = AssessmentResult(
            next_questions=next_questions,
            differential=differential,
            investigations=investigations,
            scores=scores,
            red_flags=red_flags,
            guidelines=guidelines,
            provider_key=accessor.provider_key,
        )
        teaching = build_teaching_insights(context, accessor, assessment) if context.teaching_mode else []

        return InterviewStepResult(
            differential=differential,
            investigations=investigations,
            red_flags=red_flags,
            scores=scores,
            guidelines=guidelines,
            teaching=teaching,
            next_question=next_questions[0] if next_questions else None,
            interview_complete=complete,
            active_branches=branches,
            questions_answered=len(context.answered_question_codes),
            provider_key=accessor.provider_key,
        )

    def on_answer(
        self,
        context: AssessmentContext,
        question_code: str,
        answer: str,
    ) -> InterviewStepResult:
        """Apply one new answer and immediately recalculate the interview state."""
        context.answers[question_code] = answer.strip()
        self._sync_answered(context)
        context.answered_question_codes.add(question_code)
        return self.advance(context)

    def kl_drives_complaint(self, complaint_code: str) -> bool:
        """True when KL publishes CDS rules for this complaint."""
        accessor = CdsKnowledgeAccessor(self._provider)
        if accessor.differential_priors(complaint_code):
            return True
        if accessor.question_rules(complaint_code):
            return True
        return bool(accessor.baseline_investigations(complaint_code))
