"""Knowledge Object linking for differential assessment."""

from __future__ import annotations

from typing import Any

from app.modules.knowledge_library.services import get_knowledge_service


def fetch_published_references(
    *,
    topic_keys: list[str] | None = None,
    stable_ids: list[str] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """
    Return traceable knowledge references and source audit metadata.

    Uses only published / activated knowledge objects — never PDFs.
    """
    service = get_knowledge_service()
    references: list[dict[str, Any]] = []
    sources: list[dict[str, Any]] = []
    seen: set[str] = set()

    for stable_id in stable_ids or []:
        obj = service.get_published(stable_id)
        if obj and obj.stable_id not in seen:
            seen.add(obj.stable_id)
            ref = _object_to_reference(obj)
            references.append(ref)
            sources.append(ref)

    for topic_key in topic_keys or []:
        for obj in service.find_by_topic_key(topic_key):
            if obj.stable_id in seen:
                continue
            seen.add(obj.stable_id)
            ref = _object_to_reference(obj)
            references.append(ref)
            sources.append(ref)

    return references, sources


def _object_to_reference(obj) -> dict[str, Any]:
    body_preview = (obj.body or obj.summary or "")[:240]
    return {
        "stable_id": obj.stable_id,
        "title": obj.title,
        "topic_key": obj.topic_key,
        "version": obj.version.version_label,
        "version_sequence": obj.version.version_sequence,
        "status": obj.version.status,
        "relevant_section": body_preview,
        "object_type": obj.object_type,
    }
