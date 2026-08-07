"""Map persistence records to domain knowledge objects."""

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
    ClinicalScoreKnowledge,
    ComplaintKnowledge,
    DifferentialDiagnosisKnowledge,
    DiseaseKnowledge,
    GuidelineKnowledge,
    HistoryQuestionKnowledge,
    InvestigationKnowledge,
    KnowledgeLink,
    KnowledgeObject,
    KnowledgeVersion,
    ManagementRecommendationKnowledge,
    PhysicalExaminationKnowledge,
    ReferenceKnowledge,
    SymptomKnowledge,
    TeachingNoteKnowledge,
)
from app.modules.knowledge_library.models import KnowledgeObjectLinkRecord, KnowledgeObjectRecord

_TYPE_MAP = {
    OBJECT_TYPE_DISEASE: DiseaseKnowledge,
    OBJECT_TYPE_SYMPTOM: SymptomKnowledge,
    OBJECT_TYPE_COMPLAINT: ComplaintKnowledge,
    OBJECT_TYPE_HISTORY_QUESTION: HistoryQuestionKnowledge,
    OBJECT_TYPE_PHYSICAL_EXAMINATION: PhysicalExaminationKnowledge,
    OBJECT_TYPE_DIFFERENTIAL: DifferentialDiagnosisKnowledge,
    OBJECT_TYPE_INVESTIGATION: InvestigationKnowledge,
    OBJECT_TYPE_SCORE: ClinicalScoreKnowledge,
    OBJECT_TYPE_GUIDELINE: GuidelineKnowledge,
    OBJECT_TYPE_MANAGEMENT: ManagementRecommendationKnowledge,
    OBJECT_TYPE_TEACHING: TeachingNoteKnowledge,
    OBJECT_TYPE_REFERENCE: ReferenceKnowledge,
}


def record_to_domain(record: KnowledgeObjectRecord) -> KnowledgeObject:
    version = KnowledgeVersion(
        stable_id=record.stable_id,
        version_sequence=record.version_sequence,
        version_label=record.version_label,
        status=record.status,
        published_at=record.published_at,
        supersedes_stable_id=record.supersedes_stable_id,
    )
    cls = _TYPE_MAP.get(record.object_type, KnowledgeObject)
    return cls(
        stable_id=record.stable_id,
        object_type=record.object_type,
        title=record.title,
        version=version,
        specialty_code=record.specialty_code,
        topic_key=record.topic_key,
        summary=record.summary,
        body=record.body,
        attributes=record.attributes,
    )


def link_to_domain(record: KnowledgeObjectLinkRecord) -> KnowledgeLink:
    return KnowledgeLink(
        from_stable_id=record.from_stable_id,
        to_stable_id=record.to_stable_id,
        link_type=record.link_type,
        version_sequence=record.version_sequence,
    )
