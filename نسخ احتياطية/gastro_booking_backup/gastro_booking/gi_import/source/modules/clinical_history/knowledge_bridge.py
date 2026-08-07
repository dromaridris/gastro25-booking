"""Knowledge Library bridge — delegates to KnowledgeService (Sprint 5A-KL).

Clinical history engines continue to read catalogue rules through CatalogProvider.
Guideline and teaching prose is fetched only via stable topic keys through this bridge.
"""

from __future__ import annotations

from app.modules.knowledge_library.services import get_knowledge_service


def fetch_guidance(topic_key: str, context: dict | None = None) -> list[dict]:
    return get_knowledge_service().fetch_guidance(topic_key, context)


def fetch_suggested_history_questions(complaint_code: str, differential: dict) -> list[str]:
    return get_knowledge_service().fetch_suggested_history_questions(complaint_code, differential)
