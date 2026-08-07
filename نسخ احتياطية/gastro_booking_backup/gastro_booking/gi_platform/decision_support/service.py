"""Clinical Decision Support service — public entry point."""

from __future__ import annotations

from gi_platform.decision_support.context import AssessmentContext, AssessmentResult
from gi_platform.decision_support.knowledge_accessor import CdsKnowledgeAccessor
from gi_platform.decision_support.orchestrator import DecisionSupportOrchestrator


class DecisionSupportService:
    """Deterministic clinical reasoning over Knowledge Library content."""

    def __init__(self, db):
        self._db = db

    def assess(self, context: AssessmentContext) -> AssessmentResult:
        accessor = CdsKnowledgeAccessor(self._db)
        return DecisionSupportOrchestrator(accessor).assess(context)

    def assess_for_report(self, context: AssessmentContext) -> AssessmentResult:
        result = self.assess(context)
        result.teaching = []
        return result


def get_decision_support_service(db) -> DecisionSupportService:
    return DecisionSupportService(db)
