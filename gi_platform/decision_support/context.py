"""Assessment context and result models — ported from GastroIntelligence."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AssessmentContext:
    complaint_code: str
    patient_id: int | None = None
    specialty_code: str | None = None
    demographics: dict[str, Any] = field(default_factory=dict)
    answers: dict[str, str] = field(default_factory=dict)
    existing_diagnoses: list[str] = field(default_factory=list)
    lab_values: dict[str, Any] = field(default_factory=dict)
    answered_question_codes: set[str] = field(default_factory=set)
    teaching_mode: bool = False
    confirmed_diagnosis_code: str | None = None
    session_id: int | None = None
    ward_patient_id: int | None = None


@dataclass
class QuestionRecommendation:
    question_stable_id: str
    question_code: str
    prompt: str
    diagnostic_value: float
    purpose: str
    rationale: str | None = None


@dataclass
class DifferentialItem:
    diagnosis_stable_id: str
    diagnosis_code: str
    name: str
    consideration_level: str
    consideration_label: str


@dataclass
class InvestigationRecommendation:
    investigation_stable_id: str
    investigation_code: str
    tier: str
    reason: str | None
    linked_diagnosis_code: str | None = None
    skip_suggested: bool = False
    context_note: str | None = None


@dataclass
class ScoreResult:
    score_stable_id: str
    score_code: str
    name: str
    available: bool
    value: str | None = None
    interpretation: str | None = None
    missing_variables: list[str] = field(default_factory=list)


@dataclass
class RedFlagAlert:
    stable_id: str
    code: str
    title: str
    message: str
    severity: str = 'high'


@dataclass
class GuidelineRecommendation:
    stable_id: str
    topic_key: str
    title: str
    summary: str
    full_reference_stable_id: str | None = None


@dataclass
class TeachingInsight:
    category: str
    message: str
    related_codes: list[str] = field(default_factory=list)


@dataclass
class InterviewStepResult:
    differential: list[DifferentialItem] = field(default_factory=list)
    investigations: list[InvestigationRecommendation] = field(default_factory=list)
    red_flags: list[RedFlagAlert] = field(default_factory=list)
    scores: list[ScoreResult] = field(default_factory=list)
    guidelines: list[GuidelineRecommendation] = field(default_factory=list)
    teaching: list[TeachingInsight] = field(default_factory=list)
    next_question: QuestionRecommendation | None = None
    interview_complete: bool = False
    active_branches: list[str] = field(default_factory=list)
    questions_answered: int = 0
    provider_key: str = ''
    disclaimer: str = (
        'Clinical decision support assists the physician. '
        'The treating clinician retains full responsibility for diagnosis and management.'
    )


@dataclass
class AssessmentResult:
    next_questions: list[QuestionRecommendation] = field(default_factory=list)
    differential: list[DifferentialItem] = field(default_factory=list)
    investigations: list[InvestigationRecommendation] = field(default_factory=list)
    scores: list[ScoreResult] = field(default_factory=list)
    red_flags: list[RedFlagAlert] = field(default_factory=list)
    guidelines: list[GuidelineRecommendation] = field(default_factory=list)
    teaching: list[TeachingInsight] = field(default_factory=list)
    provider_key: str = ''
    disclaimer: str = (
        'Clinical decision support assists the physician. '
        'The treating clinician retains full responsibility for diagnosis and management.'
    )
