"""Catalogue adapter objects — same surface as ORM catalogue models for intelligence engines."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class CatalogComplaint:
    code: str
    name: str
    category: str = "gi"
    sort_order: int = 0
    knowledge_topic_key: str | None = None


@dataclass
class CatalogQuestion:
    code: str
    prompt_text: str
    section: str
    answer_type: str = "boolean"
    choices_json: str | None = None
    is_exclusion_question: bool = False
    help_text: str | None = None
    knowledge_topic_key: str | None = None

    @property
    def choices(self) -> list[str]:
        if not self.choices_json:
            return []
        import json
        return json.loads(self.choices_json)


@dataclass
class CatalogQuestionRule:
    complaint_code: str
    question_code: str
    sort_order: int = 0
    parent_question_code: str | None = None
    parent_answer_required: str | None = None
    activation_json: str | None = None
    question_purpose: str = "contextual"
    differential_priority: float = 1.0
    target_diagnosis_codes_json: str | None = None
    clinical_rationale: str | None = None
    show_when_differential_includes: str | None = None
    hide_when_differential_below: float | None = None
    gate_diagnosis_codes_json: str | None = None


@dataclass
class CatalogDifferentialPrior:
    complaint_code: str
    diagnosis_code: str
    prior_weight: float = 0.5


@dataclass
class CatalogDiagnosis:
    code: str
    name: str
    category: str = "gi"
    knowledge_topic_key: str | None = None


@dataclass
class CatalogWeightRule:
    complaint_code: str
    question_code: str
    answer_match: str
    diagnosis_code: str
    weight_delta: float = 0.0


@dataclass
class CatalogInvestigationRule:
    investigation_code: str
    tier: str
    complaint_code: str | None = None
    diagnosis_code: str | None = None
    reason_text: str | None = None
    sort_order: int = 0


@dataclass
class CatalogManagementRule:
    diagnosis_code: str
    summary_text: str
    principles_text: str | None = None
    scores_text: str | None = None
    red_flags_text: str | None = None
    follow_up_text: str | None = None
    knowledge_topic_key: str | None = None
