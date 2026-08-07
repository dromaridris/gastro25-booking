"""Repository implementations backed by KnowledgeProvider storage."""

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
from app.modules.knowledge_library.domain import (
    DiseaseKnowledge,
    GuidelineKnowledge,
    HistoryQuestionKnowledge,
    KnowledgeObject,
    ManagementRecommendationKnowledge,
    ReferenceKnowledge,
)
from app.modules.knowledge_library.interfaces import KnowledgeRepository


class TypedRepositoryFacade:
    """Typed repository views over a shared KnowledgeRepository implementation."""

    def __init__(self, repository: KnowledgeRepository):
        self._repository = repository

    def _typed_list(self, object_type: str, cls, *, specialty_code: str | None = None):
        rows = self._repository.list_by_type(object_type, specialty_code=specialty_code, status="published")
        return [row for row in rows if isinstance(row, cls) or True]

    def get(self, stable_id: str, version_sequence: int | None = None) -> KnowledgeObject | None:
        return self._repository.get(stable_id, version_sequence)


class PostgresKnowledgeRepository:
    """PostgreSQL registry repository — internal to postgres provider."""

    def __init__(self, default_object_type: str | None = None):
        self._default_object_type = default_object_type

    def get(self, stable_id: str, version_sequence: int | None = None) -> KnowledgeObject | None:
        from app.modules.knowledge_library.models import KnowledgeObjectRecord
        from app.modules.knowledge_library.mappers import record_to_domain

        q = KnowledgeObjectRecord.query.filter_by(stable_id=stable_id, is_archived=False)
        if self._default_object_type:
            q = q.filter_by(object_type=self._default_object_type)
        if version_sequence is not None:
            q = q.filter_by(version_sequence=version_sequence)
        else:
            q = q.order_by(KnowledgeObjectRecord.version_sequence.desc())
        record = q.first()
        return record_to_domain(record) if record else None

    def get_published(self, stable_id: str) -> KnowledgeObject | None:
        from app.modules.knowledge_library.models import KnowledgeObjectRecord
        from app.modules.knowledge_library.mappers import record_to_domain

        q = KnowledgeObjectRecord.query.filter_by(
            stable_id=stable_id, status="published", is_archived=False
        )
        if self._default_object_type:
            q = q.filter_by(object_type=self._default_object_type)
        record = q.order_by(KnowledgeObjectRecord.version_sequence.desc()).first()
        return record_to_domain(record) if record else None

    def list_versions(self, stable_id: str) -> list[KnowledgeObject]:
        from app.modules.knowledge_library.models import KnowledgeObjectRecord
        from app.modules.knowledge_library.mappers import record_to_domain

        q = KnowledgeObjectRecord.query.filter_by(stable_id=stable_id, is_archived=False)
        if self._default_object_type:
            q = q.filter_by(object_type=self._default_object_type)
        return [record_to_domain(r) for r in q.order_by(KnowledgeObjectRecord.version_sequence.asc()).all()]

    def list_by_type(
        self,
        object_type: str,
        *,
        specialty_code: str | None = None,
        status: str | None = None,
        limit: int = 500,
    ) -> list[KnowledgeObject]:
        from app.modules.knowledge_library.models import KnowledgeObjectRecord
        from app.modules.knowledge_library.mappers import record_to_domain

        q = KnowledgeObjectRecord.query.filter_by(object_type=object_type, is_archived=False)
        if specialty_code is not None:
            q = q.filter_by(specialty_code=specialty_code)
        if status is not None:
            q = q.filter_by(status=status)
        records = q.order_by(KnowledgeObjectRecord.title.asc()).limit(limit).all()
        return [record_to_domain(r) for r in records]

    def find_by_topic_key(self, topic_key: str, *, status: str | None = None) -> list[KnowledgeObject]:
        from app.modules.knowledge_library.models import KnowledgeObjectRecord
        from app.modules.knowledge_library.mappers import record_to_domain

        q = KnowledgeObjectRecord.query.filter_by(topic_key=topic_key, is_archived=False)
        if status is not None:
            q = q.filter_by(status=status)
        records = q.order_by(KnowledgeObjectRecord.version_sequence.desc()).all()
        return [record_to_domain(r) for r in records]

    def list_links(
        self,
        stable_id: str,
        *,
        link_type: str | None = None,
        direction: str = "outbound",
    ) -> list:
        from app.modules.knowledge_library.models import KnowledgeObjectLinkRecord
        from app.modules.knowledge_library.mappers import link_to_domain

        if direction == "inbound":
            q = KnowledgeObjectLinkRecord.query.filter_by(to_stable_id=stable_id, is_archived=False)
        else:
            q = KnowledgeObjectLinkRecord.query.filter_by(from_stable_id=stable_id, is_archived=False)
        if link_type:
            q = q.filter_by(link_type=link_type)
        return [link_to_domain(r) for r in q.all()]


class DiseaseRepositoryAdapter:
    def __init__(self, repository: KnowledgeRepository):
        self._repository = repository

    def get(self, stable_id: str, version_sequence: int | None = None) -> DiseaseKnowledge | None:
        obj = self._repository.get(stable_id, version_sequence)
        return obj if isinstance(obj, DiseaseKnowledge) or obj is None else DiseaseKnowledge(**obj.__dict__)

    def list(self, *, specialty_code: str | None = None) -> list[DiseaseKnowledge]:
        rows = self._repository.list_by_type(OBJECT_TYPE_DISEASE, specialty_code=specialty_code, status="published")
        return [
            row if isinstance(row, DiseaseKnowledge) else DiseaseKnowledge(**row.__dict__)
            for row in rows
        ]


class QuestionRepositoryAdapter:
    def __init__(self, repository: KnowledgeRepository):
        self._repository = repository

    def get(self, stable_id: str, version_sequence: int | None = None) -> HistoryQuestionKnowledge | None:
        obj = self._repository.get(stable_id, version_sequence)
        if obj is None:
            return None
        return obj if isinstance(obj, HistoryQuestionKnowledge) else HistoryQuestionKnowledge(**obj.__dict__)

    def list(self, *, specialty_code: str | None = None) -> list[HistoryQuestionKnowledge]:
        rows = self._repository.list_by_type(
            OBJECT_TYPE_HISTORY_QUESTION, specialty_code=specialty_code, status="published"
        )
        return [
            row if isinstance(row, HistoryQuestionKnowledge) else HistoryQuestionKnowledge(**row.__dict__)
            for row in rows
        ]


class GuidelineRepositoryAdapter:
    def __init__(self, repository: KnowledgeRepository):
        self._repository = repository

    def get(self, stable_id: str, version_sequence: int | None = None) -> GuidelineKnowledge | None:
        obj = self._repository.get(stable_id, version_sequence)
        if obj is None:
            return None
        return obj if isinstance(obj, GuidelineKnowledge) else GuidelineKnowledge(**obj.__dict__)

    def get_published(self, stable_id: str) -> GuidelineKnowledge | None:
        obj = self._repository.get_published(stable_id)
        if obj is None:
            return None
        return obj if isinstance(obj, GuidelineKnowledge) else GuidelineKnowledge(**obj.__dict__)

    def list_versions(self, stable_id: str) -> list[GuidelineKnowledge]:
        rows = self._repository.list_versions(stable_id)
        return [
            row if isinstance(row, GuidelineKnowledge) else GuidelineKnowledge(**row.__dict__)
            for row in rows
        ]


class ManagementRepositoryAdapter:
    def __init__(self, repository: KnowledgeRepository):
        self._repository = repository

    def get(self, stable_id: str, version_sequence: int | None = None) -> ManagementRecommendationKnowledge | None:
        obj = self._repository.get(stable_id, version_sequence)
        if obj is None:
            return None
        return (
            obj
            if isinstance(obj, ManagementRecommendationKnowledge)
            else ManagementRecommendationKnowledge(**obj.__dict__)
        )

    def find_by_topic_key(self, topic_key: str) -> list[ManagementRecommendationKnowledge]:
        rows = self._repository.find_by_topic_key(topic_key, status="published")
        return [
            row
            if isinstance(row, ManagementRecommendationKnowledge)
            else ManagementRecommendationKnowledge(**row.__dict__)
            for row in rows
        ]


class ReferenceRepositoryAdapter:
    def __init__(self, repository: KnowledgeRepository):
        self._repository = repository

    def get(self, stable_id: str, version_sequence: int | None = None) -> ReferenceKnowledge | None:
        obj = self._repository.get(stable_id, version_sequence)
        if obj is None:
            return None
        return obj if isinstance(obj, ReferenceKnowledge) else ReferenceKnowledge(**obj.__dict__)

    def list_for_object(self, stable_id: str) -> list[ReferenceKnowledge]:
        links = self._repository.list_links(stable_id, link_type="references")
        refs: list[ReferenceKnowledge] = []
        for link in links:
            ref = self.get(link.to_stable_id)
            if ref:
                refs.append(ref)
        return refs


def typed_repository(repository: KnowledgeRepository, object_type: str) -> PostgresKnowledgeRepository:
    return PostgresKnowledgeRepository(default_object_type=object_type)


# Export object type constants for provider wiring
COMPLAINT = OBJECT_TYPE_COMPLAINT
DIFFERENTIAL = OBJECT_TYPE_DIFFERENTIAL
DISEASE = OBJECT_TYPE_DISEASE
GUIDELINE = OBJECT_TYPE_GUIDELINE
HISTORY_QUESTION = OBJECT_TYPE_HISTORY_QUESTION
INVESTIGATION = OBJECT_TYPE_INVESTIGATION
MANAGEMENT = OBJECT_TYPE_MANAGEMENT
PHYSICAL_EXAMINATION = OBJECT_TYPE_PHYSICAL_EXAMINATION
REFERENCE = OBJECT_TYPE_REFERENCE
SCORE = OBJECT_TYPE_SCORE
SYMPTOM = OBJECT_TYPE_SYMPTOM
TEACHING = OBJECT_TYPE_TEACHING
