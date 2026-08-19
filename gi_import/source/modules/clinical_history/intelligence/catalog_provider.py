"""Knowledge catalogue provider abstraction.

Primary source: Knowledge Library (KnowledgeProvider).
Fallback: legacy ORM seed tables (DatabaseCatalogProvider) for tests only.
"""

from __future__ import annotations

from typing import Protocol

from app.modules.clinical_history.models import (
    ChiefComplaintDefinition,
    HistoryQuestionDefinition,
    SUGGESTION_TIER_ADVANCED,
    SUGGESTION_TIER_BASELINE,
)
from app.modules.knowledge_library.catalog_adapters import (
    CatalogComplaint,
    CatalogDiagnosis,
    CatalogDifferentialPrior,
    CatalogInvestigationRule,
    CatalogManagementRule,
    CatalogQuestion,
    CatalogQuestionRule,
    CatalogWeightRule,
)
from app.modules.knowledge_library.kl_catalog_loader import get_kl_catalog_index


class CatalogProvider(Protocol):
    """Interface for complaint trees, weights, and guidance."""

    def list_complaints(self) -> list: ...

    def get_complaint(self, code: str): ...

    def get_question(self, code: str): ...

    def question_rules_for_complaint(self, complaint_code: str) -> list: ...

    def differential_priors(self, complaint_code: str) -> list: ...

    def weight_rules_for_complaint(self, complaint_code: str) -> list: ...

    def weight_rules_for_question(self, complaint_code: str, question_code: str) -> list: ...

    def investigation_rules(
        self,
        complaint_code: str | None = None,
        diagnosis_code: str | None = None,
        tier: str | None = None,
    ) -> list: ...

    def management_for_diagnosis(self, diagnosis_code: str): ...

    def diagnosis(self, code: str): ...

    def all_diagnoses(self) -> list: ...

    def is_populated(self) -> bool: ...


class DatabaseCatalogProvider:
    """Legacy ORM catalogue — fallback when KL is empty."""

    def list_complaints(self) -> list[ChiefComplaintDefinition]:
        return (
            ChiefComplaintDefinition.query.filter_by(is_archived=False)
            .order_by(ChiefComplaintDefinition.sort_order)
            .all()
        )

    def get_complaint(self, code: str) -> ChiefComplaintDefinition | None:
        return ChiefComplaintDefinition.query.filter_by(code=code, is_archived=False).first()

    def get_question(self, code: str) -> HistoryQuestionDefinition | None:
        return HistoryQuestionDefinition.query.filter_by(code=code, is_archived=False).first()

    def question_rules_for_complaint(self, complaint_code: str) -> list:
        from app.modules.clinical_history.models import ComplaintQuestionRule

        return (
            ComplaintQuestionRule.query.filter_by(complaint_code=complaint_code, is_archived=False)
            .order_by(ComplaintQuestionRule.sort_order)
            .all()
        )

    def differential_priors(self, complaint_code: str) -> list:
        from app.modules.clinical_history.models import ComplaintDifferentialPrior

        return ComplaintDifferentialPrior.query.filter_by(complaint_code=complaint_code, is_archived=False).all()

    def weight_rules_for_complaint(self, complaint_code: str) -> list:
        from app.modules.clinical_history.models import AnswerWeightRule

        return AnswerWeightRule.query.filter_by(complaint_code=complaint_code, is_archived=False).all()

    def weight_rules_for_question(self, complaint_code: str, question_code: str) -> list:
        from app.modules.clinical_history.models import AnswerWeightRule

        return AnswerWeightRule.query.filter_by(
            complaint_code=complaint_code,
            question_code=question_code,
            is_archived=False,
        ).all()

    def investigation_rules(
        self,
        complaint_code: str | None = None,
        diagnosis_code: str | None = None,
        tier: str | None = None,
    ) -> list:
        from app.modules.clinical_history.models import InvestigationGuidanceRule

        q = InvestigationGuidanceRule.query.filter_by(is_archived=False)
        if complaint_code is not None:
            q = q.filter_by(complaint_code=complaint_code)
        if diagnosis_code is not None:
            q = q.filter_by(diagnosis_code=diagnosis_code)
        if tier is not None:
            q = q.filter_by(tier=tier)
        return q.order_by(InvestigationGuidanceRule.sort_order).all()

    def management_for_diagnosis(self, diagnosis_code: str):
        from app.modules.clinical_history.models import ManagementGuidanceRule

        return ManagementGuidanceRule.query.filter_by(diagnosis_code=diagnosis_code, is_archived=False).first()

    def diagnosis(self, code: str):
        from app.modules.clinical_history.models import DiagnosisDefinition

        return DiagnosisDefinition.query.filter_by(code=code, is_archived=False).first()

    def all_diagnoses(self) -> list:
        from app.modules.clinical_history.models import DiagnosisDefinition

        return DiagnosisDefinition.query.filter_by(is_archived=False).order_by(DiagnosisDefinition.name).all()

    def is_populated(self) -> bool:
        return ChiefComplaintDefinition.query.filter_by(is_archived=False).first() is not None


class KnowledgeLibraryCatalogProvider:
    """Primary provider — reads published Knowledge Library catalogue."""

    def __init__(self):
        self._index = get_kl_catalog_index()

    def _load(self):
        self._index.ensure_loaded()

    def is_populated(self) -> bool:
        self._load()
        return self._index.is_populated()

    def list_complaints(self) -> list[CatalogComplaint]:
        self._load()
        return list(self._index.complaints)

    def get_complaint(self, code: str) -> CatalogComplaint | None:
        self._load()
        return next((c for c in self._index.complaints if c.code == code), None)

    def get_question(self, code: str) -> CatalogQuestion | None:
        self._load()
        return self._index.questions.get(code)

    def question_rules_for_complaint(self, complaint_code: str) -> list[CatalogQuestionRule]:
        self._load()
        rules = self._index.question_rules.get(complaint_code, [])
        seen: dict[str, CatalogQuestionRule] = {}
        for rule in sorted(rules, key=lambda r: r.sort_order):
            seen[rule.question_code] = rule
        return sorted(seen.values(), key=lambda r: r.sort_order)

    def differential_priors(self, complaint_code: str) -> list[CatalogDifferentialPrior]:
        self._load()
        return list(self._index.priors.get(complaint_code, []))

    def weight_rules_for_complaint(self, complaint_code: str) -> list[CatalogWeightRule]:
        self._load()
        return list(self._index.weight_rules.get(complaint_code, []))

    def weight_rules_for_question(self, complaint_code: str, question_code: str) -> list[CatalogWeightRule]:
        return [r for r in self.weight_rules_for_complaint(complaint_code) if r.question_code == question_code]

    def investigation_rules(
        self,
        complaint_code: str | None = None,
        diagnosis_code: str | None = None,
        tier: str | None = None,
    ) -> list[CatalogInvestigationRule]:
        self._load()
        out = []
        for rule in self._index.investigations:
            if complaint_code is not None and rule.complaint_code and rule.complaint_code != complaint_code:
                continue
            if diagnosis_code is not None and rule.diagnosis_code and rule.diagnosis_code != diagnosis_code:
                continue
            if tier is not None and rule.tier != tier:
                continue
            if complaint_code is not None and rule.complaint_code is None and rule.diagnosis_code is None:
                continue
            out.append(rule)
        return sorted(out, key=lambda r: r.sort_order)

    def management_for_diagnosis(self, diagnosis_code: str) -> CatalogManagementRule | None:
        self._load()
        return self._index.management.get(diagnosis_code)

    def diagnosis(self, code: str) -> CatalogDiagnosis | None:
        self._load()
        return self._index.diagnoses.get(code)

    def all_diagnoses(self) -> list[CatalogDiagnosis]:
        self._load()
        return sorted(self._index.diagnoses.values(), key=lambda d: d.name)


_provider: CatalogProvider | None = None


def get_catalog_provider(use_knowledge_library: bool | None = None) -> CatalogProvider:
    global _provider
    if _provider is not None:
        return _provider
    if use_knowledge_library is False:
        return DatabaseCatalogProvider()
    kl = KnowledgeLibraryCatalogProvider()
    if kl.is_populated():
        return kl
    return DatabaseCatalogProvider()


def set_catalog_provider(provider: CatalogProvider) -> None:
    global _provider
    _provider = provider


def reset_catalog_provider() -> None:
    global _provider
    _provider = None
