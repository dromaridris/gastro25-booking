"""Load clinical catalogue structures from published Knowledge Library content."""

from __future__ import annotations

import json

from app.modules.decision_support.constants import (
    RULE_KIND_BRANCH_ACTIVATION,
    RULE_KIND_INVESTIGATION_ADVANCED,
    RULE_KIND_INVESTIGATION_BASELINE,
    RULE_KIND_PRIOR,
    RULE_KIND_QUESTION,
    RULE_KIND_WEIGHT,
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
from app.modules.knowledge_library.constants import (
    OBJECT_TYPE_CDS_RULE,
    OBJECT_TYPE_COMPLAINT,
    OBJECT_TYPE_DISEASE,
    OBJECT_TYPE_HISTORY_QUESTION,
    OBJECT_TYPE_INVESTIGATION,
    OBJECT_TYPE_MANAGEMENT,
    STATUS_PUBLISHED,
)
from app.modules.knowledge_library.provider_factory import get_knowledge_provider


class KlCatalogIndex:
    """In-memory index of published KL catalogue — rebuilt on demand."""

    def __init__(self):
        self._provider = get_knowledge_provider()
        self._loaded = False
        self.complaints: list[CatalogComplaint] = []
        self.questions: dict[str, CatalogQuestion] = {}
        self.diagnoses: dict[str, CatalogDiagnosis] = {}
        self.question_rules: dict[str, list[CatalogQuestionRule]] = {}
        self.priors: dict[str, list[CatalogDifferentialPrior]] = {}
        self.weight_rules: dict[str, list[CatalogWeightRule]] = {}
        self.investigations: list[CatalogInvestigationRule] = []
        self.management: dict[str, CatalogManagementRule] = {}

    def ensure_loaded(self) -> None:
        if self._loaded:
            return
        repo = self._provider.repository
        for row in repo.list_by_type(OBJECT_TYPE_COMPLAINT, status=STATUS_PUBLISHED, limit=5000):
            code = row.attributes.get("complaint_code") or row.stable_id
            self.complaints.append(
                CatalogComplaint(
                    code=code,
                    name=row.title,
                    category=row.attributes.get("category", "gi"),
                    sort_order=int(row.attributes.get("sort_order", 0)),
                    knowledge_topic_key=row.topic_key,
                )
            )
        for row in repo.list_by_type(OBJECT_TYPE_DISEASE, status=STATUS_PUBLISHED, limit=5000):
            code = row.attributes.get("diagnosis_code") or row.stable_id
            self.diagnoses[code] = CatalogDiagnosis(
                code=code,
                name=row.title,
                category=row.attributes.get("category", "gi"),
                knowledge_topic_key=row.topic_key,
            )
        for row in repo.list_by_type(OBJECT_TYPE_HISTORY_QUESTION, status=STATUS_PUBLISHED, limit=5000):
            code = row.attributes.get("question_code") or row.stable_id
            choices = row.attributes.get("choices")
            self.questions[code] = CatalogQuestion(
                code=code,
                prompt_text=row.attributes.get("prompt") or row.title,
                section=row.attributes.get("section", "presenting"),
                answer_type=row.attributes.get("answer_type", "boolean"),
                choices_json=json.dumps(choices) if choices else row.attributes.get("choices_json"),
                is_exclusion_question=bool(row.attributes.get("is_exclusion_question", False)),
                help_text=row.attributes.get("help_text"),
                knowledge_topic_key=row.topic_key,
            )
            complaint = row.attributes.get("complaint_code")
            if complaint and row.attributes.get("sort_order") is not None:
                self._add_question_rule_from_question(row, complaint)
        for row in repo.list_by_type(OBJECT_TYPE_CDS_RULE, status=STATUS_PUBLISHED, limit=10000):
            self._ingest_cds_rule(row)
        for row in repo.list_by_type(OBJECT_TYPE_MANAGEMENT, status=STATUS_PUBLISHED, limit=5000):
            dx = row.attributes.get("diagnosis_code")
            if dx:
                self.management[dx] = CatalogManagementRule(
                    diagnosis_code=dx,
                    summary_text=row.summary or row.title,
                    principles_text=row.body,
                    scores_text=row.attributes.get("scores_text"),
                    red_flags_text=row.attributes.get("red_flags_text"),
                    follow_up_text=row.attributes.get("follow_up_text"),
                    knowledge_topic_key=row.topic_key,
                )
        self.complaints.sort(key=lambda c: c.sort_order)
        self._loaded = True

    def _add_question_rule_from_question(self, row, complaint: str) -> None:
        attrs = row.attributes
        code = attrs.get("question_code") or row.stable_id
        rule = CatalogQuestionRule(
            complaint_code=complaint,
            question_code=code,
            sort_order=int(attrs.get("sort_order", 0)),
            parent_question_code=attrs.get("parent_question_code"),
            parent_answer_required=attrs.get("parent_answer_required"),
            activation_json=json.dumps(attrs["activation_json"]) if isinstance(attrs.get("activation_json"), dict) else attrs.get("activation_json"),
            question_purpose=attrs.get("question_purpose", "contextual"),
            differential_priority=float(attrs.get("differential_priority", 1.0)),
            target_diagnosis_codes_json=json.dumps(attrs["target_diagnosis_codes"]) if isinstance(attrs.get("target_diagnosis_codes"), list) else attrs.get("target_diagnosis_codes_json"),
            clinical_rationale=attrs.get("clinical_rationale"),
            show_when_differential_includes=json.dumps(attrs["show_when_differential_includes"]) if isinstance(attrs.get("show_when_differential_includes"), list) else attrs.get("show_when_differential_includes"),
            hide_when_differential_below=attrs.get("hide_when_differential_below"),
            gate_diagnosis_codes_json=json.dumps(attrs["gate_diagnosis_codes"]) if isinstance(attrs.get("gate_diagnosis_codes"), list) else attrs.get("gate_diagnosis_codes_json"),
        )
        self.question_rules.setdefault(complaint, []).append(rule)

    def _ingest_cds_rule(self, row) -> None:
        attrs = row.attributes
        kind = attrs.get("rule_kind")
        complaint = attrs.get("complaint_code")
        if kind == RULE_KIND_PRIOR and complaint:
            self.priors.setdefault(complaint, []).append(
                CatalogDifferentialPrior(
                    complaint_code=complaint,
                    diagnosis_code=attrs["diagnosis_code"],
                    prior_weight=float(attrs.get("prior_weight", 0.5)),
                )
            )
        elif kind == RULE_KIND_WEIGHT and complaint:
            self.weight_rules.setdefault(complaint, []).append(
                CatalogWeightRule(
                    complaint_code=complaint,
                    question_code=attrs["question_code"],
                    answer_match=attrs["answer_match"],
                    diagnosis_code=attrs["diagnosis_code"],
                    weight_delta=float(attrs.get("weight_delta", 0)),
                )
            )
        elif kind == RULE_KIND_QUESTION and complaint:
            rule = CatalogQuestionRule(
                complaint_code=complaint,
                question_code=attrs.get("question_code", row.stable_id),
                sort_order=int(attrs.get("sort_order", 0)),
                parent_question_code=attrs.get("parent_question_code"),
                parent_answer_required=attrs.get("parent_answer_required"),
                activation_json=json.dumps(attrs["activation_json"]) if isinstance(attrs.get("activation_json"), dict) else attrs.get("activation_json"),
                question_purpose=attrs.get("question_purpose", "contextual"),
                differential_priority=float(attrs.get("differential_priority", 1.0)),
                target_diagnosis_codes_json=json.dumps(attrs["target_diagnosis_codes"]) if isinstance(attrs.get("target_diagnosis_codes"), list) else attrs.get("target_diagnosis_codes_json"),
                clinical_rationale=attrs.get("clinical_rationale") or row.summary,
                show_when_differential_includes=attrs.get("show_when_differential_includes"),
                hide_when_differential_below=attrs.get("hide_when_differential_below"),
                gate_diagnosis_codes_json=attrs.get("gate_diagnosis_codes_json"),
            )
            self.question_rules.setdefault(complaint, []).append(rule)
        elif kind == RULE_KIND_INVESTIGATION_BASELINE and complaint:
            self.investigations.append(
                CatalogInvestigationRule(
                    complaint_code=complaint,
                    investigation_code=attrs.get("investigation_code", row.stable_id),
                    tier="baseline",
                    reason_text=attrs.get("reason") or row.summary,
                    sort_order=int(attrs.get("sort_order", 0)),
                )
            )
        elif kind == RULE_KIND_INVESTIGATION_ADVANCED:
            self.investigations.append(
                CatalogInvestigationRule(
                    diagnosis_code=attrs.get("diagnosis_code"),
                    complaint_code=complaint,
                    investigation_code=attrs.get("investigation_code", row.stable_id),
                    tier="advanced",
                    reason_text=attrs.get("reason") or row.summary,
                    sort_order=int(attrs.get("sort_order", 0)),
                )
            )
        elif kind == RULE_KIND_BRANCH_ACTIVATION:
            pass  # consumed by CDS engine only

    def is_populated(self) -> bool:
        self.ensure_loaded()
        return bool(self.complaints or self.priors or self.question_rules)


_index: KlCatalogIndex | None = None


def get_kl_catalog_index() -> KlCatalogIndex:
    global _index
    if _index is None:
        _index = KlCatalogIndex()
    return _index


def reset_kl_catalog_index() -> None:
    global _index
    _index = None
