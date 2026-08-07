"""KnowledgeService — platform facade for all knowledge consumers."""

from __future__ import annotations

from app.modules.knowledge_library.domain import GuidanceSnippet, KnowledgeObject
from app.modules.knowledge_library.provider_factory import get_knowledge_provider


class KnowledgeService:
    """
    Single entry point for clinical engines, teaching mode, and future AI modules.

    Depends only on KnowledgeProvider — never on storage location or format.
    """

    def __init__(self, provider=None):
        self._provider = provider

    @property
    def provider(self):
        if self._provider is None:
            from app.modules.knowledge_library.models import seed_default_provider_registration_if_empty

            seed_default_provider_registration_if_empty()
        return self._provider or get_knowledge_provider()

    def health_check(self) -> bool:
        return self.provider.health_check()

    def get_object(self, stable_id: str, version_sequence: int | None = None) -> KnowledgeObject | None:
        return self.provider.repository.get(stable_id, version_sequence)

    def get_published(self, stable_id: str) -> KnowledgeObject | None:
        return self.provider.repository.get_published(stable_id)

    def list_versions(self, stable_id: str) -> list[KnowledgeObject]:
        return self.provider.repository.list_versions(stable_id)

    def find_by_topic_key(self, topic_key: str) -> list[KnowledgeObject]:
        return self.provider.repository.find_by_topic_key(topic_key, status="published")

    def fetch_guidance(self, topic_key: str, context: dict | None = None) -> list[dict]:
        """
        Teaching / management / guideline excerpts keyed by stable topic keys.

        Returns bridge-compatible dicts — same shape used by clinical_history.knowledge_bridge.
        """
        _ = context
        snippets: list[dict] = []
        for obj in self.find_by_topic_key(topic_key):
            snippets.append(self._to_guidance_dict(obj))
        if not snippets:
            for obj in self.provider.management.find_by_topic_key(topic_key):
                snippets.append(self._to_guidance_dict(obj))
        return snippets

    def fetch_suggested_history_questions(self, complaint_code: str, differential: dict) -> list[str]:
        """Optional KL-driven supplemental question stable IDs."""
        _ = differential
        rows = self.provider.repository.list_by_type(
            "history_question", status="published", limit=2000
        )
        return [
            obj.stable_id
            for obj in rows
            if obj.attributes.get("complaint_code") == complaint_code
        ]

    def _to_guidance_dict(self, obj: KnowledgeObject) -> dict:
        return GuidanceSnippet(
            topic_key=obj.topic_key or obj.stable_id,
            title=obj.title,
            body=obj.body or obj.summary or "",
            source_provider=self.provider.provider_key,
            stable_id=obj.stable_id,
            version_label=obj.version.version_label,
        ).__dict__


_service: KnowledgeService | None = None


def get_knowledge_service() -> KnowledgeService:
    global _service
    if _service is None:
        _service = KnowledgeService()
    return _service


def set_knowledge_service(service: KnowledgeService) -> None:
    global _service
    _service = service
