"""Clinical Decision Support service — public entry point."""

from __future__ import annotations

from app.modules.decision_support.context import AssessmentContext, AssessmentResult
from app.modules.decision_support.knowledge_accessor import CdsKnowledgeAccessor
from app.modules.decision_support.orchestrator import DecisionSupportOrchestrator
from app.modules.knowledge_library.interfaces import KnowledgeProvider
from app.modules.knowledge_library.provider_factory import get_knowledge_provider


class DecisionSupportService:
    """
    Deterministic clinical reasoning over Knowledge Library content.

    No LLMs. No hardcoded diseases. Provider-agnostic.
    """

    def __init__(self, provider: KnowledgeProvider | None = None):
        self._provider = provider or get_knowledge_provider()

    def assess(self, context: AssessmentContext) -> AssessmentResult:
        accessor = CdsKnowledgeAccessor(self._provider)
        return DecisionSupportOrchestrator(accessor).assess(context)

    def assess_for_report(self, context: AssessmentContext) -> AssessmentResult:
        """Medico-legal safe output — teaching insights stripped."""
        result = self.assess(context)
        result.teaching = []
        return result


_service: DecisionSupportService | None = None


def get_decision_support_service() -> DecisionSupportService:
    global _service
    if _service is None:
        _service = DecisionSupportService()
    return _service


def set_decision_support_service(service: DecisionSupportService) -> None:
    global _service
    _service = service
