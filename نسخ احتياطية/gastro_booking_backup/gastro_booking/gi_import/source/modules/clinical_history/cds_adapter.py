"""Bridge Clinical History sessions to the active CDS Interview Driver."""

from __future__ import annotations

from app.modules.clinical_data_registry.context_builder import enrich_assessment_context, lab_values_for_patient
from app.modules.clinical_history.models import HistoryAnswer, HistoryQuestionDefinition, HistorySession
from app.modules.decision_support.context import AssessmentContext, InterviewStepResult
from app.modules.decision_support.interview_driver import ClinicalInterviewDriver


def _normalize(value: str) -> str:
    return (value or "").strip().lower()


def _answer_map(session_id: int) -> dict[str, str]:
    rows = HistoryAnswer.query.filter_by(session_id=session_id, is_archived=False).all()
    return {r.question_code: _normalize(r.answer_value) for r in rows}


def _patient_lab_values(patient_id: int | None) -> dict[str, str | float]:
    return lab_values_for_patient(patient_id)


def context_from_session(session: HistorySession, *, teaching_mode: bool = False) -> AssessmentContext:
    answers = _answer_map(session.id)
    context = AssessmentContext(
        complaint_code=session.chief_complaint_code or "",
        patient_id=session.patient_id,
        answers=answers,
        answered_question_codes=set(answers.keys()),
        lab_values=_patient_lab_values(session.patient_id),
        teaching_mode=teaching_mode,
        confirmed_diagnosis_code=session.confirmed_diagnosis_code,
    )
    return enrich_assessment_context(context)


def kl_drives_interview(complaint_code: str | None) -> bool:
    """
    Clinical History Intelligence reads KL via KnowledgeLibraryCatalogProvider.
    The CDS Interview Driver remains available for direct API use but does not
    override the catalogue intelligence path — preserves identical behaviour.
    """
    return False


def advance_interview(session: HistorySession, *, teaching_mode: bool = False) -> InterviewStepResult:
    context = context_from_session(session, teaching_mode=teaching_mode)
    return ClinicalInterviewDriver().advance(context)


def on_answer_recorded(
    session: HistorySession,
    question_code: str,
    answer: str,
    *,
    teaching_mode: bool = False,
) -> InterviewStepResult:
    context = context_from_session(session, teaching_mode=teaching_mode)
    return ClinicalInterviewDriver().on_answer(context, question_code, answer)


def differential_for_display(session: HistorySession) -> list[dict]:
    step = advance_interview(session)
    return [
        {
            "diagnosis_code": d.diagnosis_code,
            "name": d.name,
            "consideration_level": d.consideration_level,
            "consideration_label": d.consideration_label,
        }
        for d in step.differential
    ]


def investigations_for_display(session: HistorySession) -> list[dict]:
    step = advance_interview(session)
    return [
        {
            "investigation_code": i.investigation_code,
            "tier": i.tier,
            "reason_text": i.reason,
            "linked_diagnosis_code": i.linked_diagnosis_code,
            "skip_suggested": i.skip_suggested,
            "context_note": i.context_note,
        }
        for i in step.investigations
    ]


def resolve_question_batch(session: HistorySession, batch_size: int = 1) -> tuple[list[HistoryQuestionDefinition], bool, dict | None]:
    """
    Return next question(s) from CDS when KL drives this complaint.
    Maps KL question codes to catalogue HistoryQuestionDefinition rows for existing UI.
    """
    step = advance_interview(session)
    meta = {
        "purpose_hint": step.next_question.rationale if step.next_question else None,
        "differential": differential_for_display(session),
        "red_flags": [{"title": r.title, "message": r.message} for r in step.red_flags],
        "active_branches": step.active_branches,
        "cds_driven": True,
    }
    if step.interview_complete or not step.next_question:
        return [], step.interview_complete, meta

    codes = [step.next_question.question_code]
    if batch_size > 1:
        codes = codes[:batch_size]

    questions = (
        HistoryQuestionDefinition.query.filter(
            HistoryQuestionDefinition.code.in_(codes),
            HistoryQuestionDefinition.is_archived.is_(False),
        )
        .all()
    )
    order = {code: idx for idx, code in enumerate(codes)}
    batch = sorted(questions, key=lambda q: order.get(q.code, 999))
    return batch, step.interview_complete, meta
