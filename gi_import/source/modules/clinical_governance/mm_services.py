"""Mortality & Morbidity (M&M) services — Sprint 7D."""

from __future__ import annotations

from datetime import date

from app.core.exceptions import NotFoundError, ValidationError
from app.extensions import db
from app.engines import audit_engine, permission_engine
from app.modules.clinical_governance.constants import ALL_MM_STATUSES, MM_PRESENTED, MM_SCHEDULED
from app.modules.clinical_governance.models import MortalityMorbidityCase


def _require(user, permission: str) -> None:
    permission_engine.require(user, permission)


def list_mm_cases(acting_user, *, status: str | None = None) -> list[MortalityMorbidityCase]:
    _require(acting_user, "governance:view")
    query = MortalityMorbidityCase.query.filter_by(is_archived=False)
    if status:
        query = query.filter_by(status=status)
    return query.order_by(MortalityMorbidityCase.presentation_date.desc()).all()


def create_mm_case(
    acting_user,
    *,
    case_summary: str,
    patient_id: int | None = None,
    procedure_id: int | None = None,
    presentation_date: date | None = None,
    presenter_id: int | None = None,
) -> MortalityMorbidityCase:
    _require(acting_user, "governance:mm_participate")
    case = MortalityMorbidityCase(
        patient_id=patient_id,
        procedure_id=procedure_id,
        presentation_date=presentation_date,
        case_summary=case_summary.strip(),
        status=MM_SCHEDULED,
        presenter_id=presenter_id or acting_user.id,
        department_id=getattr(acting_user, "department_id", 1) or 1,
        created_by_id=acting_user.id,
    )
    db.session.add(case)
    audit_engine.log("governance.mm_created", user=acting_user, target_type="mm_case", target_id=case.id)
    db.session.commit()
    return case


def get_mm_case(acting_user, case_id: int) -> MortalityMorbidityCase:
    _require(acting_user, "governance:view")
    case = MortalityMorbidityCase.query.filter_by(id=case_id, is_archived=False).first()
    if case is None:
        raise NotFoundError("M&M case not found.")
    return case


def update_mm_discussion(
    acting_user,
    case: MortalityMorbidityCase,
    *,
    discussion_notes: str | None = None,
    lessons_learned: str | None = None,
    recommendations: str | None = None,
    follow_up_actions: str | None = None,
    status: str | None = None,
) -> MortalityMorbidityCase:
    _require(acting_user, "governance:mm_participate")
    if status and status not in ALL_MM_STATUSES:
        raise ValidationError(f"Invalid status '{status}'.")
    if discussion_notes is not None:
        case.discussion_notes = discussion_notes
    if lessons_learned is not None:
        case.lessons_learned = lessons_learned
    if recommendations is not None:
        case.recommendations = recommendations
    if follow_up_actions is not None:
        case.follow_up_actions = follow_up_actions
    if status:
        case.status = status
    elif case.status == MM_SCHEDULED:
        case.status = MM_PRESENTED
    db.session.commit()
    return case
