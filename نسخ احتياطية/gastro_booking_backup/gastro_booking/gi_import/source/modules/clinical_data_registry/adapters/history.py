"""Clinical history read adapter — owner: clinical_history module."""

from __future__ import annotations

from app.modules.clinical_data_registry.constants import SOURCE_MODULE_CLINICAL_HISTORY
from app.modules.clinical_data_registry.domain import ClinicalObservationRef
from app.modules.clinical_history.models import HistoryAnswer, HistorySession


def fetch_history_answer(
    patient_id: int,
    question_code: str,
    *,
    canonical_code: str,
    complaint_code: str | None = None,
) -> ClinicalObservationRef | None:
    query = (
        HistoryAnswer.query.join(HistorySession, HistoryAnswer.session_id == HistorySession.id)
        .filter(
            HistorySession.patient_id == patient_id,
            HistoryAnswer.question_code == question_code,
            HistoryAnswer.is_archived.is_(False),
            HistorySession.is_archived.is_(False),
        )
    )
    if complaint_code:
        query = query.filter(HistorySession.chief_complaint_code == complaint_code)
    row = query.order_by(HistoryAnswer.answered_at.desc()).first()
    if row is None:
        return None
    session = row.session
    return ClinicalObservationRef(
        ref_id=f"clinical_history:history_answer:{row.id}",
        canonical_code=canonical_code,
        patient_id=patient_id,
        encounter_id=session.encounter_id,
        value_numeric=None,
        value_text=row.answer_value,
        unit=None,
        effective_at=row.answered_at,
        recorded_at=row.created_at,
        source_module=SOURCE_MODULE_CLINICAL_HISTORY,
        source_type="history_answer",
        source_key=question_code,
        author_id=row.created_by_id or session.created_by_id,
        status=session.status,
        version=(row.updated_at or row.created_at).isoformat(),
        is_latest=True,
    )


def fetch_confirmed_diagnosis(
    patient_id: int,
    *,
    canonical_code: str,
    complaint_code: str | None = None,
) -> ClinicalObservationRef | None:
    query = HistorySession.query.filter_by(patient_id=patient_id, is_archived=False).filter(
        HistorySession.confirmed_diagnosis_code.isnot(None)
    )
    if complaint_code:
        query = query.filter_by(chief_complaint_code=complaint_code)
    row = query.order_by(HistorySession.diagnosis_confirmed_at.desc()).first()
    if row is None:
        return None
    return ClinicalObservationRef(
        ref_id=f"clinical_history:history_session:{row.id}:diagnosis",
        canonical_code=canonical_code,
        patient_id=patient_id,
        encounter_id=row.encounter_id,
        value_numeric=None,
        value_text=row.confirmed_diagnosis_code,
        unit=None,
        effective_at=row.diagnosis_confirmed_at,
        recorded_at=row.created_at,
        source_module=SOURCE_MODULE_CLINICAL_HISTORY,
        source_type="history_confirmed_diagnosis",
        source_key=row.chief_complaint_code or "",
        author_id=row.created_by_id,
        status=row.status,
        version=(row.updated_at or row.created_at).isoformat(),
        is_latest=True,
    )
