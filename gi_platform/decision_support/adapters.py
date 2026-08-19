"""Bridge between decision_support models and legacy cds_service / catalogue_runtime."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from gi_platform import history_service
from gi_platform.decision_support.context import (
    AssessmentContext as DsContext,
    AssessmentResult as DsResult,
    InterviewStepResult,
    QuestionRecommendation,
)


@dataclass
class LegacyAssessmentContext:
    chief_complaint: str = ''
    complaint_code: str = ''
    symptoms: list[str] = field(default_factory=list)
    findings: list[str] = field(default_factory=list)
    session_id: int | None = None
    ward_patient_id: int | None = None
    teaching_mode: bool = False


@dataclass
class LegacyAssessmentResult:
    differentials: list[dict] = field(default_factory=list)
    red_flags: list[str] = field(default_factory=list)
    guidelines: list[dict] = field(default_factory=list)
    investigations: list[dict] = field(default_factory=list)
    scores: list[dict] = field(default_factory=list)
    teaching: list[str] = field(default_factory=list)
    next_questions: list[dict] = field(default_factory=list)
    provider_key: str = ''


def _lab_key_from_code(code: str) -> str:
    return code.replace('lab.', '') if code.startswith('lab.') else code


def build_context_from_session(
    db,
    *,
    session_id: int | None = None,
    complaint_code: str = '',
    ward_patient_id: int | None = None,
    teaching_mode: bool = False,
    legacy: LegacyAssessmentContext | None = None,
) -> DsContext:
    answers: dict[str, str] = {}
    demographics: dict[str, Any] = {}
    lab_values: dict[str, Any] = {}
    code = complaint_code

    if session_id:
        answers = history_service.get_answers_map(db, session_id)
        sess = history_service.get_session(db, session_id)
        if sess:
            code = code or (sess['complaint_code'] or '')
            ward_patient_id = ward_patient_id or sess['ward_patient_id']

    if ward_patient_id:
        wp = db.execute('SELECT * FROM ward_patient WHERE id = ?', (ward_patient_id,)).fetchone()
        if wp:
            demographics['gender'] = wp['gender'] or ''
            age_val = wp['age']
            if age_val:
                try:
                    demographics['age'] = int(re.sub(r'[^0-9]', '', str(age_val)) or '0') or age_val
                except ValueError:
                    demographics['age'] = age_val
        rows = db.execute(
            """
            SELECT test_code, test_name, result_value, status
            FROM gi_lab_result WHERE ward_patient_id = ?
            ORDER BY result_date DESC, recorded_at DESC LIMIT 40
            """,
            (ward_patient_id,),
        ).fetchall()
        for r in rows:
            key = _lab_key_from_code(r['test_code'] or '')
            if not key:
                key = re.sub(r'[^a-z0-9_]', '_', (r['test_name'] or '').lower())
            if key and key not in lab_values:
                lab_values[key] = r['result_value'] or r['status'] or ''

    if legacy:
        code = code or legacy.complaint_code
        ward_patient_id = ward_patient_id or legacy.ward_patient_id
        session_id = session_id or legacy.session_id
        teaching_mode = teaching_mode or legacy.teaching_mode

    return DsContext(
        complaint_code=code,
        patient_id=ward_patient_id,
        ward_patient_id=ward_patient_id,
        session_id=session_id,
        answers=answers,
        answered_question_codes=set(answers.keys()),
        demographics=demographics,
        lab_values=lab_values,
        teaching_mode=teaching_mode,
    )


def to_legacy_result(result: DsResult) -> LegacyAssessmentResult:
    legacy = LegacyAssessmentResult(provider_key=result.provider_key)
    for dx in result.differential:
        legacy.differentials.append({
            'title': dx.name,
            'summary': dx.consideration_label,
            'code': dx.diagnosis_code,
            'consideration_level': dx.consideration_level,
        })
    for rf in result.red_flags:
        legacy.red_flags.append(rf.message or rf.title)
    for g in result.guidelines:
        legacy.guidelines.append({'title': g.title, 'summary': g.summary, 'topic_key': g.topic_key})
    for inv in result.investigations:
        legacy.investigations.append({
            'name': inv.reason or inv.investigation_code,
            'priority': inv.tier,
            'rationale': inv.reason or '',
            'investigation_code': inv.investigation_code,
            'skip_suggested': inv.skip_suggested,
            'context_note': inv.context_note,
        })
    for sc in result.scores:
        legacy.scores.append({
            'name': sc.name,
            'code': sc.score_code,
            'available': sc.available,
            'value': sc.value,
            'interpretation': sc.interpretation,
            'missing_variables': sc.missing_variables,
        })
    for t in result.teaching:
        legacy.teaching.append(t.message)
    for q in result.next_questions:
        legacy.next_questions.append({
            'question_code': q.question_code,
            'prompt': q.prompt,
            'diagnostic_value': q.diagnostic_value,
            'purpose': q.purpose,
            'rationale': q.rationale,
        })
    return legacy


def interview_step_to_legacy(step: InterviewStepResult) -> LegacyAssessmentResult:
    return to_legacy_result(
        DsResult(
            differential=step.differential,
            investigations=step.investigations,
            scores=step.scores,
            red_flags=step.red_flags,
            guidelines=step.guidelines,
            teaching=step.teaching,
            next_questions=[step.next_question] if step.next_question else [],
            provider_key=step.provider_key,
        )
    )


def question_rec_to_view(q: QuestionRecommendation, db=None):
    """Map a CDS recommendation onto a QuestionView with real answer_type/choices."""
    from gi_platform.catalogue_runtime import QuestionView, get_question, normalize_question_view

    view = get_question(db, q.question_code) if db is not None else None
    if view:
        if q.prompt:
            view.prompt = q.prompt
        if q.rationale and not view.help_text:
            view.help_text = q.rationale
        return normalize_question_view(view)
    return normalize_question_view(QuestionView(
        code=q.question_code,
        prompt=q.prompt,
        section='presenting',
        answer_type='text',
        help_text=q.rationale,
    ))
