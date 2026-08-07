"""Load CDS artifacts exclusively through KnowledgeProvider interfaces."""

from __future__ import annotations

from app.modules.decision_support.constants import (
    RULE_KIND_INVESTIGATION_ADVANCED,
    RULE_KIND_INVESTIGATION_BASELINE,
    RULE_KIND_PRIOR,
    RULE_KIND_QUESTION,
    RULE_KIND_RED_FLAG,
    RULE_KIND_BRANCH_ACTIVATION,
    RULE_KIND_WEIGHT,
)
from app.modules.knowledge_library.constants import (
    OBJECT_TYPE_CDS_RULE,
    OBJECT_TYPE_DISEASE,
    OBJECT_TYPE_GUIDELINE,
    OBJECT_TYPE_HISTORY_QUESTION,
    OBJECT_TYPE_INVESTIGATION,
    OBJECT_TYPE_MANAGEMENT,
    OBJECT_TYPE_SCORE,
    STATUS_PUBLISHED,
)
from app.modules.knowledge_library.domain import KnowledgeObject
from app.modules.knowledge_library.interfaces import KnowledgeProvider


class CdsKnowledgeAccessor:
    """Specialty-independent knowledge reader — no file paths, no hardcoded clinical content."""

    def __init__(self, provider: KnowledgeProvider):
        self._provider = provider

    @property
    def provider_key(self) -> str:
        return self._provider.provider_key

    def _published_rules(self, rule_kind: str | None = None, complaint_code: str | None = None) -> list[KnowledgeObject]:
        rows = self._provider.repository.list_by_type(
            OBJECT_TYPE_CDS_RULE, status=STATUS_PUBLISHED, limit=5000
        )
        out = []
        for row in rows:
            kind = row.attributes.get("rule_kind")
            if rule_kind and kind != rule_kind:
                continue
            if complaint_code and row.attributes.get("complaint_code") != complaint_code:
                continue
            out.append(row)
        return out

    def differential_priors(self, complaint_code: str) -> list[KnowledgeObject]:
        return self._published_rules(RULE_KIND_PRIOR, complaint_code)

    def weight_rules(self, complaint_code: str) -> list[KnowledgeObject]:
        return self._published_rules(RULE_KIND_WEIGHT, complaint_code)

    def question_rules(self, complaint_code: str) -> list[KnowledgeObject]:
        rules = self._published_rules(RULE_KIND_QUESTION, complaint_code)
        questions = self._provider.repository.list_by_type(
            OBJECT_TYPE_HISTORY_QUESTION, status=STATUS_PUBLISHED, limit=5000
        )
        for q in questions:
            if q.attributes.get("complaint_code") != complaint_code:
                continue
            if not any(r.attributes.get("question_code") == q.attributes.get("question_code") for r in rules):
                rules.append(q)
        return rules

    def red_flag_rules(self, complaint_code: str) -> list[KnowledgeObject]:
        return self._published_rules(RULE_KIND_RED_FLAG, complaint_code)

    def branch_activation_rules(self, complaint_code: str) -> list[KnowledgeObject]:
        return self._published_rules(RULE_KIND_BRANCH_ACTIVATION, complaint_code)

    def baseline_investigations(self, complaint_code: str) -> list[KnowledgeObject]:
        return self._published_rules(RULE_KIND_INVESTIGATION_BASELINE, complaint_code)

    def advanced_investigations(self, complaint_code: str, diagnosis_code: str | None = None) -> list[KnowledgeObject]:
        rows = self._published_rules(RULE_KIND_INVESTIGATION_ADVANCED, complaint_code)
        if diagnosis_code:
            rows = [
                r for r in rows
                if not r.attributes.get("diagnosis_code") or r.attributes.get("diagnosis_code") == diagnosis_code
            ]
        return rows

    def score_definitions(self) -> list[KnowledgeObject]:
        return self._provider.repository.list_by_type(
            OBJECT_TYPE_SCORE, status=STATUS_PUBLISHED, limit=500
        )

    def disease(self, diagnosis_code: str) -> KnowledgeObject | None:
        for row in self._provider.repository.list_by_type(OBJECT_TYPE_DISEASE, status=STATUS_PUBLISHED, limit=5000):
            if row.attributes.get("diagnosis_code") == diagnosis_code or row.stable_id == diagnosis_code:
                return row
        return None

    def investigation(self, investigation_code: str) -> KnowledgeObject | None:
        for row in self._provider.repository.list_by_type(OBJECT_TYPE_INVESTIGATION, status=STATUS_PUBLISHED, limit=5000):
            if row.attributes.get("investigation_code") == investigation_code or row.stable_id == investigation_code:
                return row
        return self._provider.repository.get(investigation_code)

    def guidelines_for_diagnosis(self, diagnosis_code: str) -> list[KnowledgeObject]:
        linked = []
        dx = self.disease(diagnosis_code)
        if dx:
            for link in self._provider.repository.list_links(dx.stable_id, link_type="applies_to"):
                g = self._provider.repository.get_published(link.to_stable_id)
                if g and g.object_type == OBJECT_TYPE_GUIDELINE:
                    linked.append(g)
        by_topic = self._provider.repository.find_by_topic_key(f"kl.{diagnosis_code}", status=STATUS_PUBLISHED)
        by_topic += self._provider.repository.find_by_topic_key(diagnosis_code, status=STATUS_PUBLISHED)
        seen = {g.stable_id for g in linked}
        for g in by_topic:
            if g.object_type == OBJECT_TYPE_GUIDELINE and g.stable_id not in seen:
                linked.append(g)
        return linked

    def management_for_diagnosis(self, diagnosis_code: str) -> KnowledgeObject | None:
        rows = self._provider.management.find_by_topic_key(diagnosis_code)
        if rows:
            return rows[0]
        for row in self._provider.repository.list_by_type(OBJECT_TYPE_MANAGEMENT, status=STATUS_PUBLISHED, limit=5000):
            if row.attributes.get("diagnosis_code") == diagnosis_code:
                return row
        return None

    def question_prompt(self, question_code: str) -> str:
        for row in self._provider.repository.list_by_type(OBJECT_TYPE_HISTORY_QUESTION, status=STATUS_PUBLISHED, limit=5000):
            if row.attributes.get("question_code") == question_code:
                return row.title
        return question_code

    def references_for_object(self, stable_id: str):
        return self._provider.references.list_for_object(stable_id)
