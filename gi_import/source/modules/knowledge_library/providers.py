"""Knowledge provider implementations."""

from __future__ import annotations

from app.modules.knowledge_library.constants import (
    OBJECT_TYPE_COMPLAINT,
    OBJECT_TYPE_DIFFERENTIAL,
    OBJECT_TYPE_DISEASE,
    OBJECT_TYPE_GUIDELINE,
    OBJECT_TYPE_HISTORY_QUESTION,
    OBJECT_TYPE_INVESTIGATION,
    OBJECT_TYPE_MANAGEMENT,
    OBJECT_TYPE_PHYSICAL_EXAMINATION,
    OBJECT_TYPE_REFERENCE,
    OBJECT_TYPE_SCORE,
    OBJECT_TYPE_SYMPTOM,
    OBJECT_TYPE_TEACHING,
)
from app.modules.knowledge_library.repositories import (
    DiseaseRepositoryAdapter,
    GuidelineRepositoryAdapter,
    ManagementRepositoryAdapter,
    PostgresKnowledgeRepository,
    QuestionRepositoryAdapter,
    ReferenceRepositoryAdapter,
)


class NullKnowledgeRepository:
    def get(self, stable_id: str, version_sequence: int | None = None):
        return None

    def get_published(self, stable_id: str):
        return None

    def list_versions(self, stable_id: str):
        return []

    def list_by_type(self, object_type: str, *, specialty_code: str | None = None, status: str | None = None, limit: int = 500):
        return []

    def find_by_topic_key(self, topic_key: str, *, status: str | None = None):
        return []

    def list_links(self, stable_id: str, *, link_type: str | None = None, direction: str = "outbound"):
        return []


class NullKnowledgeProvider:
    provider_key = "null"

    def __init__(self):
        self._repository = NullKnowledgeRepository()
        self._diseases = DiseaseRepositoryAdapter(self._repository)
        self._questions = QuestionRepositoryAdapter(self._repository)
        self._guidelines = GuidelineRepositoryAdapter(self._repository)
        self._management = ManagementRepositoryAdapter(self._repository)
        self._references = ReferenceRepositoryAdapter(self._repository)

    def health_check(self) -> bool:
        return True

    @property
    def repository(self):
        return self._repository

    @property
    def diseases(self):
        return self._diseases

    @property
    def questions(self):
        return self._questions

    @property
    def guidelines(self):
        return self._guidelines

    @property
    def management(self):
        return self._management

    @property
    def references(self):
        return self._references

    def symptoms(self):
        return self._repository

    def complaints(self):
        return self._repository

    def physical_examinations(self):
        return self._repository

    def differentials(self):
        return self._repository

    def investigations(self):
        return self._repository

    def scores(self):
        return self._repository

    def teaching_notes(self):
        return self._repository


class PostgresKnowledgeProvider:
    provider_key = "postgres"

    def __init__(self):
        self._repository = PostgresKnowledgeRepository()
        self._diseases = DiseaseRepositoryAdapter(self._repository)
        self._questions = QuestionRepositoryAdapter(self._repository)
        self._guidelines = GuidelineRepositoryAdapter(self._repository)
        self._management = ManagementRepositoryAdapter(self._repository)
        self._references = ReferenceRepositoryAdapter(self._repository)
        self._typed = {
            OBJECT_TYPE_SYMPTOM: PostgresKnowledgeRepository(OBJECT_TYPE_SYMPTOM),
            OBJECT_TYPE_COMPLAINT: PostgresKnowledgeRepository(OBJECT_TYPE_COMPLAINT),
            OBJECT_TYPE_PHYSICAL_EXAMINATION: PostgresKnowledgeRepository(OBJECT_TYPE_PHYSICAL_EXAMINATION),
            OBJECT_TYPE_DIFFERENTIAL: PostgresKnowledgeRepository(OBJECT_TYPE_DIFFERENTIAL),
            OBJECT_TYPE_INVESTIGATION: PostgresKnowledgeRepository(OBJECT_TYPE_INVESTIGATION),
            OBJECT_TYPE_SCORE: PostgresKnowledgeRepository(OBJECT_TYPE_SCORE),
            OBJECT_TYPE_TEACHING: PostgresKnowledgeRepository(OBJECT_TYPE_TEACHING),
        }

    def health_check(self) -> bool:
        from app.modules.knowledge_library.models import KnowledgeObjectRecord

        try:
            KnowledgeObjectRecord.query.limit(1).all()
            return True
        except Exception:
            return False

    @property
    def repository(self):
        return self._repository

    @property
    def diseases(self):
        return self._diseases

    @property
    def questions(self):
        return self._questions

    @property
    def guidelines(self):
        return self._guidelines

    @property
    def management(self):
        return self._management

    @property
    def references(self):
        return self._references

    def symptoms(self):
        return self._typed[OBJECT_TYPE_SYMPTOM]

    def complaints(self):
        return self._typed[OBJECT_TYPE_COMPLAINT]

    def physical_examinations(self):
        return self._typed[OBJECT_TYPE_PHYSICAL_EXAMINATION]

    def differentials(self):
        return self._typed[OBJECT_TYPE_DIFFERENTIAL]

    def investigations(self):
        return self._typed[OBJECT_TYPE_INVESTIGATION]

    def scores(self):
        return self._typed[OBJECT_TYPE_SCORE]

    def teaching_notes(self):
        return self._typed[OBJECT_TYPE_TEACHING]
