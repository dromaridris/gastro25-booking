"""Knowledge object view for SQLite-backed CDS."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class KnowledgeObject:
    stable_id: str
    title: str
    object_type: str
    summary: str = ''
    body: str = ''
    topic_key: str = ''
    attributes: dict[str, Any] = field(default_factory=dict)
    object_id: int | None = None
