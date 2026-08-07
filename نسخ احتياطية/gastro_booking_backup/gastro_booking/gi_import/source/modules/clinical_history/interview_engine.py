"""Adaptive interview engine — delegates to CDS Interview Driver when KL drives complaint."""

from app.modules.clinical_history.cds_adapter import kl_drives_interview, resolve_question_batch
from app.modules.clinical_history.intelligence.question_selector import (
    get_next_questions as get_next_question_batch_catalog,
    interview_complete as interview_complete_catalog,
)
from app.modules.clinical_history.intelligence.branching_engine import get_visible_question_codes
from app.modules.clinical_history.intelligence.differential_engine import compute_differential
from app.modules.clinical_history.models import HistoryQuestionDefinition


def get_visible_questions(complaint_code: str, session_id: int) -> list[HistoryQuestionDefinition]:
    differential = compute_differential(complaint_code, session_id)
    codes = get_visible_question_codes(complaint_code, session_id, differential=differential)
    if not codes:
        return []
    questions = HistoryQuestionDefinition.query.filter(
        HistoryQuestionDefinition.code.in_(codes),
        HistoryQuestionDefinition.is_archived.is_(False),
    ).all()
    order = {code: idx for idx, code in enumerate(codes)}
    return sorted(questions, key=lambda q: order.get(q.code, 9999))


def get_next_question_batch(complaint_code: str, session_id: int, batch_size: int = 1):
    from app.modules.clinical_history.models import HistorySession

    session = HistorySession.query.get(session_id)
    if session and kl_drives_interview(complaint_code):
        batch, complete, _meta = resolve_question_batch(session, batch_size=batch_size)
        return batch
    return get_next_question_batch_catalog(complaint_code, session_id, batch_size=batch_size)


def interview_complete(complaint_code: str, session_id: int) -> bool:
    from app.modules.clinical_history.models import HistorySession

    session = HistorySession.query.get(session_id)
    if session and kl_drives_interview(complaint_code):
        _batch, complete, _meta = resolve_question_batch(session)
        return complete
    return interview_complete_catalog(complaint_code, session_id)


__all__ = ["get_visible_questions", "get_next_question_batch", "interview_complete"]
