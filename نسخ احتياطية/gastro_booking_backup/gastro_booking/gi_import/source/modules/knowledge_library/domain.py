"""Knowledge Library domain objects — transport-neutral, provider-agnostic."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class KnowledgeVersion:
    """Immutable version descriptor for any knowledge object."""

    stable_id: str
    version_sequence: int
    version_label: str
    status: str
    published_at: datetime | None = None
    supersedes_stable_id: str | None = None


@dataclass(frozen=True)
class KnowledgeObject:
    """
    Generic knowledge record returned by any provider.

    `attributes` holds provider-specific structured fields without exposing
    storage format (JSON document, SQL columns, API payload, etc.) to consumers.
    """

    stable_id: str
    object_type: str
    title: str
    version: KnowledgeVersion
    specialty_code: str | None = None
    topic_key: str | None = None
    summary: str | None = None
    body: str | None = None
    attributes: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class DiseaseKnowledge(KnowledgeObject):
    """Disease entity — extends generic object for typed repository contracts."""


@dataclass(frozen=True)
class SymptomKnowledge(KnowledgeObject):
    pass


@dataclass(frozen=True)
class ComplaintKnowledge(KnowledgeObject):
    pass


@dataclass(frozen=True)
class HistoryQuestionKnowledge(KnowledgeObject):
    pass


@dataclass(frozen=True)
class PhysicalExaminationKnowledge(KnowledgeObject):
    pass


@dataclass(frozen=True)
class DifferentialDiagnosisKnowledge(KnowledgeObject):
    pass


@dataclass(frozen=True)
class InvestigationKnowledge(KnowledgeObject):
    pass


@dataclass(frozen=True)
class ClinicalScoreKnowledge(KnowledgeObject):
    pass


@dataclass(frozen=True)
class GuidelineKnowledge(KnowledgeObject):
    pass


@dataclass(frozen=True)
class ManagementRecommendationKnowledge(KnowledgeObject):
    pass


@dataclass(frozen=True)
class TeachingNoteKnowledge(KnowledgeObject):
    pass


@dataclass(frozen=True)
class ReferenceKnowledge(KnowledgeObject):
    pass


@dataclass(frozen=True)
class KnowledgeLink:
    """Directed relationship between two stable identifiers."""

    from_stable_id: str
    to_stable_id: str
    link_type: str
    version_sequence: int | None = None


@dataclass(frozen=True)
class GuidanceSnippet:
    """Teaching / guideline excerpt for clinical engines."""

    topic_key: str
    title: str
    body: str
    source_provider: str
    stable_id: str | None = None
    version_label: str | None = None
