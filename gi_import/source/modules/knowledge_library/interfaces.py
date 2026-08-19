"""Knowledge Library repository and provider interfaces."""

from __future__ import annotations

from typing import Protocol

from app.modules.knowledge_library.domain import (
    ClinicalScoreKnowledge,
    ComplaintKnowledge,
    DifferentialDiagnosisKnowledge,
    DiseaseKnowledge,
    GuidelineKnowledge,
    HistoryQuestionKnowledge,
    InvestigationKnowledge,
    KnowledgeLink,
    KnowledgeObject,
    ManagementRecommendationKnowledge,
    PhysicalExaminationKnowledge,
    ReferenceKnowledge,
    SymptomKnowledge,
    TeachingNoteKnowledge,
)


class KnowledgeRepository(Protocol):
    """Base read contract for versioned knowledge objects."""

    def get(self, stable_id: str, version_sequence: int | None = None) -> KnowledgeObject | None: ...

    def get_published(self, stable_id: str) -> KnowledgeObject | None: ...

    def list_versions(self, stable_id: str) -> list[KnowledgeObject]: ...

    def list_by_type(
        self,
        object_type: str,
        *,
        specialty_code: str | None = None,
        status: str | None = None,
        limit: int = 500,
    ) -> list[KnowledgeObject]: ...

    def find_by_topic_key(self, topic_key: str, *, status: str | None = None) -> list[KnowledgeObject]: ...

    def list_links(
        self,
        stable_id: str,
        *,
        link_type: str | None = None,
        direction: str = "outbound",
    ) -> list[KnowledgeLink]: ...


class DiseaseRepository(Protocol):
    def get(self, stable_id: str, version_sequence: int | None = None) -> DiseaseKnowledge | None: ...

    def list(self, *, specialty_code: str | None = None) -> list[DiseaseKnowledge]: ...


class QuestionRepository(Protocol):
    def get(self, stable_id: str, version_sequence: int | None = None) -> HistoryQuestionKnowledge | None: ...

    def list(self, *, specialty_code: str | None = None) -> list[HistoryQuestionKnowledge]: ...


class GuidelineRepository(Protocol):
    def get(self, stable_id: str, version_sequence: int | None = None) -> GuidelineKnowledge | None: ...

    def get_published(self, stable_id: str) -> GuidelineKnowledge | None: ...

    def list_versions(self, stable_id: str) -> list[GuidelineKnowledge]: ...


class ManagementRepository(Protocol):
    def get(self, stable_id: str, version_sequence: int | None = None) -> ManagementRecommendationKnowledge | None: ...

    def find_by_topic_key(self, topic_key: str) -> list[ManagementRecommendationKnowledge]: ...


class ReferenceRepository(Protocol):
    def get(self, stable_id: str, version_sequence: int | None = None) -> ReferenceKnowledge | None: ...

    def list_for_object(self, stable_id: str) -> list[ReferenceKnowledge]: ...


class KnowledgeProvider(Protocol):
    """
    Root abstraction — clinical engines depend on this interface only.

    Concrete providers (PostgreSQL, SQLite, Markdown, JSON, external API, cloud)
    implement the same repository surface without the application knowing
    storage location or serialization format.
    """

    @property
    def provider_key(self) -> str: ...

    def health_check(self) -> bool: ...

    @property
    def repository(self) -> KnowledgeRepository: ...

    @property
    def diseases(self) -> DiseaseRepository: ...

    @property
    def questions(self) -> QuestionRepository: ...

    @property
    def guidelines(self) -> GuidelineRepository: ...

    @property
    def management(self) -> ManagementRepository: ...

    @property
    def references(self) -> ReferenceRepository: ...

    # Typed accessors for remaining object families (same underlying repository)
    def symptoms(self) -> KnowledgeRepository: ...
    def complaints(self) -> KnowledgeRepository: ...
    def physical_examinations(self) -> KnowledgeRepository: ...
    def differentials(self) -> KnowledgeRepository: ...
    def investigations(self) -> KnowledgeRepository: ...
    def scores(self) -> KnowledgeRepository: ...
    def teaching_notes(self) -> KnowledgeRepository: ...
