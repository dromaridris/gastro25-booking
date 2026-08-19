"""Context Builder — collects structured data from existing modules via published interfaces."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from .constants import (
    ALL_CONTEXT_SOURCES,
    CONTEXT_CLINICAL_HISTORY,
    CONTEXT_CLINICAL_REGISTRY,
    CONTEXT_IMAGING,
    CONTEXT_KNOWLEDGE_OBJECTS,
    CONTEXT_LABORATORY,
    CONTEXT_PROCEDURES,
    CONTEXT_REPORTS,
    CONTEXT_RESEARCH,
)


ContextFetcher = Callable[..., Any]


@dataclass
class ContextRequest:
    patient_id: int | None = None
    encounter_id: int | None = None
    sources: list[str] = field(default_factory=list)
    topic_keys: list[str] = field(default_factory=list)
    object_types: list[str] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)


class ContextBuilder:
    """
    Requests only the information needed for a selected AI task.

    Integrates through callables / published services — does not modify source modules.
    """

    def __init__(self) -> None:
        self._fetchers: dict[str, ContextFetcher] = {}

    def register_fetcher(self, source_key: str, fetcher: ContextFetcher) -> None:
        if source_key not in ALL_CONTEXT_SOURCES:
            raise ValueError(f"Unknown context source: {source_key}")
        self._fetchers[source_key] = fetcher

    def available_sources(self) -> list[str]:
        return sorted(self._fetchers.keys())

    def build(self, request: ContextRequest) -> dict[str, Any]:
        sources = request.sources or list(self._fetchers.keys())
        payload: dict[str, Any] = {}
        for source in sources:
            fetcher = self._fetchers.get(source)
            if fetcher is None:
                continue
            payload[source] = fetcher(
                patient_id=request.patient_id,
                encounter_id=request.encounter_id,
                topic_keys=request.topic_keys,
                object_types=request.object_types,
                extra=request.extra,
            )
        return payload


def default_context_builder() -> ContextBuilder:
    """Wire published read-only integration hooks."""
    builder = ContextBuilder()

    def _knowledge_fetcher(**kwargs: Any) -> list[dict[str, Any]]:
        from app.modules.knowledge_library.services import KnowledgeService

        service = KnowledgeService()
        topic_keys = kwargs.get("topic_keys") or []
        object_types = kwargs.get("object_types") or []
        results: list[dict[str, Any]] = []
        repo = service.provider.repository
        if topic_keys:
            for key in topic_keys:
                for obj in service.find_by_topic_key(key):
                    results.append(_knowledge_object_summary(obj))
        elif object_types:
            for ot in object_types:
                for obj in repo.list_by_type(ot, status="published", limit=100):
                    results.append(_knowledge_object_summary(obj))
        else:
            for obj in repo.list_by_type("guideline", status="published", limit=50):
                results.append(_knowledge_object_summary(obj))
        return results

    def _empty_fetcher(**kwargs: Any) -> list[Any]:
        _ = kwargs
        return []

    builder.register_fetcher(CONTEXT_KNOWLEDGE_OBJECTS, _knowledge_fetcher)
    for source in (
        CONTEXT_CLINICAL_HISTORY,
        CONTEXT_CLINICAL_REGISTRY,
        CONTEXT_LABORATORY,
        CONTEXT_IMAGING,
        CONTEXT_PROCEDURES,
        CONTEXT_REPORTS,
        CONTEXT_RESEARCH,
    ):
        builder.register_fetcher(source, _empty_fetcher)
    return builder


def _knowledge_object_summary(obj: Any) -> dict[str, Any]:
    version = getattr(obj, "version", None)
    return {
        "stable_id": getattr(obj, "stable_id", None),
        "object_type": getattr(obj, "object_type", None),
        "title": getattr(obj, "title", None),
        "status": getattr(version, "status", None),
        "topic_key": getattr(obj, "topic_key", None),
    }
