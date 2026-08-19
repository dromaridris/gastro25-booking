"""Auto Portfolio Engine — generates logbook entries from verified clinical activity."""

from __future__ import annotations

import json
from datetime import datetime

from app.core.base_model import utcnow
from app.extensions import db
from app.modules.auth.models import User
from app.modules.clinical_history.models import FollowUpEntry, HistorySession
from app.modules.encounters.models import ClinicalEncounter, ENCOUNTER_STATUS_CLOSED
from app.modules.investigations.models import ImagingStudy, InvestigationOrder, LabResultSet
from app.modules.procedure_execution.models import OUTCOME_COMPLETED, ProcedureSession
from app.modules.procedures.models import Procedure
from app.modules.reports.models import Report, STATUS_FINALIZED, STATUS_LOCKED
from app.modules.research.study_models import ResearchCase
from app.modules.workforce.constants import (
    ACTIVITY_DIAGNOSIS_CONFIRMATION,
    ACTIVITY_ENCOUNTER,
    ACTIVITY_FOLLOW_UP,
    ACTIVITY_HISTORY_TAKING,
    ACTIVITY_IMAGING_REVIEW,
    ACTIVITY_LAB_REVIEW,
    ACTIVITY_PROCEDURE,
    ACTIVITY_PROCEDURE_SKILL,
    ACTIVITY_REPORT_AUTHORED,
    ACTIVITY_REPORT_SUPERVISED,
    ACTIVITY_RESEARCH,
    COMPETENCY_OTHER,
    ROLE_ASSISTANT,
    ROLE_ENDOSCOPY_NURSE,
    ROLE_OBSERVER,
    ROLE_PRIMARY_OPERATOR,
    ROLE_REPORTING_PHYSICIAN,
    ROLE_SEDATION_PHYSICIAN,
    ROLE_TECHNICIAN,
    SOURCE_CLINICAL_HISTORY,
    SOURCE_ENCOUNTERS,
    SOURCE_INVESTIGATIONS,
    SOURCE_PROCEDURE_EXECUTION,
    SOURCE_REPORTS,
    SOURCE_CLINICAL_REPORTS,
    SOURCE_RESEARCH,
    SUBTYPE_ASSISTED,
    SUBTYPE_INDEPENDENT,
    SUBTYPE_OBSERVED,
    TEMPLATE_TO_COMPETENCY,
    TRAINEE_ROLE_CODES,
    VERIFY_DRAFT,
)
from app.modules.workforce.models import PortfolioEntry


def _role_code(user_id: int | None) -> str | None:
    if user_id is None:
        return None
    user = User.query.filter_by(id=user_id, is_archived=False).first()
    if user is None or user.role is None:
        return None
    return user.role.code


def _is_trainee(user_id: int | None) -> bool:
    code = _role_code(user_id)
    return code in TRAINEE_ROLE_CODES if code else False


def _competency_for_procedure(procedure: Procedure | None) -> str:
    if procedure is None or procedure.procedure_type is None:
        return COMPETENCY_OTHER
    key = procedure.procedure_type.report_template_key
    return TEMPLATE_TO_COMPETENCY.get(key or "", COMPETENCY_OTHER)


def _procedure_subtype(user_id: int, participation_role: str) -> str | None:
    if participation_role == ROLE_PRIMARY_OPERATOR:
        return SUBTYPE_INDEPENDENT if _is_trainee(user_id) else None
    if participation_role == ROLE_ASSISTANT:
        return SUBTYPE_ASSISTED if _is_trainee(user_id) else None
    if participation_role == ROLE_OBSERVER:
        return SUBTYPE_OBSERVED
    return None


def _upsert_entry(
    *,
    user_id: int,
    activity_type: str,
    source_module: str,
    source_type: str,
    source_id: int,
    title: str,
    activity_at: datetime,
    patient_id: int | None = None,
    participation_role: str | None = None,
    activity_subtype: str | None = None,
    competency_category: str | None = None,
    skill_code: str | None = None,
    context: dict | None = None,
) -> PortfolioEntry | None:
    if user_id is None:
        return None

    skill_key = skill_code or ""
    existing = PortfolioEntry.query.filter_by(
        user_id=user_id,
        source_module=source_module,
        source_type=source_type,
        source_id=source_id,
        activity_type=activity_type,
        participation_role=participation_role,
        skill_code=skill_key,
        is_archived=False,
    ).first()

    ctx_json = json.dumps(context or {})
    if existing:
        if existing.verification_status != VERIFY_DRAFT:
            return existing
        existing.title = title
        existing.activity_at = activity_at
        existing.patient_id = patient_id
        existing.activity_subtype = activity_subtype
        existing.competency_category = competency_category
        existing.skill_code = skill_key
        existing.context_json = ctx_json
        return existing

    entry = PortfolioEntry(
        user_id=user_id,
        activity_type=activity_type,
        activity_subtype=activity_subtype,
        participation_role=participation_role,
        competency_category=competency_category,
        skill_code=skill_key,
        source_module=source_module,
        source_type=source_type,
        source_id=source_id,
        patient_id=patient_id,
        activity_at=activity_at,
        title=title,
        context_json=ctx_json,
        verification_status=VERIFY_DRAFT,
        department_id=1,
    )
    db.session.add(entry)
    return entry


def _sync_encounters(user_id: int | None = None) -> int:
    query = ClinicalEncounter.query.filter_by(is_archived=False, status=ENCOUNTER_STATUS_CLOSED)
    if user_id:
        query = query.filter_by(created_by_id=user_id)
    count = 0
    for enc in query.all():
        if enc.created_by_id is None:
            continue
        _upsert_entry(
            user_id=enc.created_by_id,
            activity_type=ACTIVITY_ENCOUNTER,
            source_module=SOURCE_ENCOUNTERS,
            source_type="clinical_encounter",
            source_id=enc.id,
            title=f"Clinical encounter ({enc.encounter_type})",
            activity_at=enc.closed_at or enc.started_at or enc.created_at,
            patient_id=enc.patient_id,
            context={"encounter_type": enc.encounter_type},
        )
        count += 1
    return count


def _sync_history(user_id: int | None = None) -> int:
    count = 0
    sessions = HistorySession.query.filter_by(is_archived=False)
    for session in sessions.all():
        if session.status != "completed" and session.completed_at is None:
            continue
        at = session.completed_at or session.created_at
        if session.created_by_id and (user_id is None or session.created_by_id == user_id):
            _upsert_entry(
                user_id=session.created_by_id,
                activity_type=ACTIVITY_HISTORY_TAKING,
                source_module=SOURCE_CLINICAL_HISTORY,
                source_type="history_session",
                source_id=session.id,
                title=f"History taking — {session.chief_complaint_code or 'session'}",
                activity_at=at,
                patient_id=session.patient_id,
                context={"chief_complaint": session.chief_complaint_code},
            )
            count += 1
        if session.diagnosis_confirmed_by_id and (user_id is None or session.diagnosis_confirmed_by_id == user_id):
            _upsert_entry(
                user_id=session.diagnosis_confirmed_by_id,
                activity_type=ACTIVITY_DIAGNOSIS_CONFIRMATION,
                source_module=SOURCE_CLINICAL_HISTORY,
                source_type="history_session",
                source_id=session.id,
                title=f"Diagnosis confirmed — {session.confirmed_diagnosis_code or 'diagnosis'}",
                activity_at=session.diagnosis_confirmed_at or at,
                patient_id=session.patient_id,
                context={"diagnosis_code": session.confirmed_diagnosis_code},
            )
            count += 1
    return count


def _sync_follow_ups(user_id: int | None = None) -> int:
    query = FollowUpEntry.query.filter_by(is_archived=False)
    if user_id:
        query = query.filter_by(documented_by_id=user_id)
    count = 0
    for entry in query.all():
        if entry.documented_by_id is None:
            continue
        _upsert_entry(
            user_id=entry.documented_by_id,
            activity_type=ACTIVITY_FOLLOW_UP,
            source_module=SOURCE_CLINICAL_HISTORY,
            source_type="follow_up_entry",
            source_id=entry.id,
            title="Follow-up note documented",
            activity_at=entry.documented_at,
            patient_id=entry.patient_id,
        )
        count += 1
    return count


def _sync_single_procedure_session(session: ProcedureSession) -> int:
    if session.is_cancelled or session.outcome != OUTCOME_COMPLETED:
        return 0
    procedure = session.procedure
    competency = _competency_for_procedure(procedure)
    proc_name = procedure.procedure_type.name if procedure and procedure.procedure_type else "Procedure"
    at = session.procedure_finish_at or session.procedure_start_at or session.created_at
    count = 0
    team = [
        (session.endoscopist_id, ROLE_PRIMARY_OPERATOR),
        (session.assistant_id, ROLE_ASSISTANT),
        (session.nurse_id, ROLE_ENDOSCOPY_NURSE),
        (session.technician_id, ROLE_TECHNICIAN),
        (session.anaesthetist_id, ROLE_SEDATION_PHYSICIAN),
    ]
    for uid, role in team:
        if uid is None:
            continue
        subtype = _procedure_subtype(uid, role)
        _upsert_entry(
            user_id=uid,
            activity_type=ACTIVITY_PROCEDURE,
            source_module=SOURCE_PROCEDURE_EXECUTION,
            source_type="procedure_session",
            source_id=session.id,
            title=f"{proc_name} — {role.replace('_', ' ')}",
            activity_at=at,
            patient_id=session.patient_id,
            participation_role=role,
            activity_subtype=subtype,
            competency_category=competency,
            context={"procedure_type": proc_name, "outcome": session.outcome},
        )
        count += 1
    return count


def _sync_procedures(user_id: int | None = None) -> int:
    count = 0
    sessions = ProcedureSession.query.filter_by(is_archived=False, is_cancelled=False)
    for session in sessions.all():
        if session.outcome != OUTCOME_COMPLETED:
            continue
        if user_id:
            team_ids = {session.endoscopist_id, session.assistant_id, session.nurse_id, session.technician_id, session.anaesthetist_id}
            if user_id not in team_ids:
                continue
        count += _sync_single_procedure_session(session)
    return count


def _sync_report_skills(report: Report) -> int:
    from app.modules.workforce.skill_detector import detect_skills_for_report

    if report.status not in {STATUS_FINALIZED, STATUS_LOCKED}:
        return 0
    skills = detect_skills_for_report(report)
    if not skills:
        return 0
    at = report.finalized_at or report.created_at
    proc = report.procedure
    competency = _competency_for_procedure(proc)
    count = 0
    author_id = report.author_id
    if author_id is None:
        return 0
    for skill in skills:
        _upsert_entry(
            user_id=author_id,
            activity_type=ACTIVITY_PROCEDURE_SKILL,
            source_module=SOURCE_CLINICAL_REPORTS,
            source_type="report_skill",
            source_id=report.id,
            title=f"Skill: {skill.label}",
            activity_at=at,
            patient_id=report.patient_id,
            participation_role=ROLE_PRIMARY_OPERATOR,
            competency_category=competency,
            skill_code=skill.skill_code,
            context={"detection_source": skill.source, "report_number": report.report_number},
        )
        count += 1
    return count


def _sync_single_report(report: Report) -> int:
    count = 0
    at = report.finalized_at or report.created_at
    proc_name = report.header_procedure_type or "Endoscopy report"

    if report.author_id:
        _upsert_entry(
            user_id=report.author_id,
            activity_type=ACTIVITY_REPORT_AUTHORED,
            source_module=SOURCE_REPORTS,
            source_type="report",
            source_id=report.id,
            title=f"Report authored — {proc_name}",
            activity_at=at,
            patient_id=report.patient_id,
            participation_role=ROLE_REPORTING_PHYSICIAN,
            context={"report_number": report.report_number},
        )
        count += 1

    if report.supervising_consultant_id and report.supervising_consultant_id != report.author_id:
        _upsert_entry(
            user_id=report.supervising_consultant_id,
            activity_type=ACTIVITY_REPORT_SUPERVISED,
            source_module=SOURCE_REPORTS,
            source_type="report",
            source_id=report.id,
            title=f"Report supervised — {proc_name}",
            activity_at=at,
            patient_id=report.patient_id,
            participation_role=ROLE_OBSERVER,
            activity_subtype=SUBTYPE_OBSERVED,
            context={"report_number": report.report_number},
        )
        count += 1

    count += _sync_report_skills(report)
    return count


def _sync_reports(user_id: int | None = None) -> int:
    count = 0
    reports = Report.query.filter(
        Report.is_archived.is_(False),
        Report.status.in_([STATUS_FINALIZED, STATUS_LOCKED]),
    )
    for report in reports.all():
        if user_id and report.author_id != user_id and report.supervising_consultant_id != user_id:
            continue
        count += _sync_single_report(report)
    return count


def _sync_investigations(user_id: int | None = None) -> int:
    count = 0
    for order in InvestigationOrder.query.filter_by(is_archived=False).all():
        if order.reviewed_by_id is None:
            continue
        if user_id and order.reviewed_by_id != user_id:
            continue
        _upsert_entry(
            user_id=order.reviewed_by_id,
            activity_type=ACTIVITY_LAB_REVIEW,
            source_module=SOURCE_INVESTIGATIONS,
            source_type="investigation_order",
            source_id=order.id,
            title="Laboratory order reviewed",
            activity_at=order.updated_at or order.created_at,
            patient_id=order.patient_id,
        )
        count += 1

    for rs in LabResultSet.query.filter_by(is_archived=False).all():
        if rs.reviewed_by_id is None:
            continue
        if user_id and rs.reviewed_by_id != user_id:
            continue
        _upsert_entry(
            user_id=rs.reviewed_by_id,
            activity_type=ACTIVITY_LAB_REVIEW,
            source_module=SOURCE_INVESTIGATIONS,
            source_type="lab_result_set",
            source_id=rs.id,
            title="Laboratory results reviewed",
            activity_at=rs.updated_at or rs.created_at,
            patient_id=rs.patient_id,
        )
        count += 1

    for study in ImagingStudy.query.filter_by(is_archived=False).all():
        if study.reviewed_by_id is None:
            continue
        if user_id and study.reviewed_by_id != user_id:
            continue
        _upsert_entry(
            user_id=study.reviewed_by_id,
            activity_type=ACTIVITY_IMAGING_REVIEW,
            source_module=SOURCE_INVESTIGATIONS,
            source_type="imaging_study",
            source_id=study.id,
            title="Imaging study reviewed",
            activity_at=study.updated_at or study.created_at,
            patient_id=study.patient_id,
        )
        count += 1
    return count


def _sync_research(user_id: int | None = None) -> int:
    count = 0
    query = ResearchCase.query.filter_by(is_archived=False, case_status="enrolled")
    if user_id:
        query = query.filter(
            (ResearchCase.enrolled_by_id == user_id) | (ResearchCase.reviewer_id == user_id)
        )
    for case in query.all():
        if case.enrolled_by_id and (user_id is None or case.enrolled_by_id == user_id):
            study_title = case.study.title if case.study else "Research study"
            _upsert_entry(
                user_id=case.enrolled_by_id,
                activity_type=ACTIVITY_RESEARCH,
                source_module=SOURCE_RESEARCH,
                source_type="research_case",
                source_id=case.id,
                title=f"Research enrolment — {study_title}",
                activity_at=case.enrolled_at,
                patient_id=case.patient_id,
                context={"study_code": case.study.study_code if case.study else None},
            )
            count += 1
    return count


def sync_portfolio(user_id: int | None = None) -> dict:
    """Scan clinical modules and upsert portfolio entries. Idempotent."""
    counts = {
        "encounters": _sync_encounters(user_id),
        "history": _sync_history(user_id),
        "follow_ups": _sync_follow_ups(user_id),
        "procedures": _sync_procedures(user_id),
        "reports": _sync_reports(user_id),
        "investigations": _sync_investigations(user_id),
        "research": _sync_research(user_id),
    }
    db.session.commit()
    return counts


def procedure_totals(user_id: int, *, official_only: bool = True) -> dict:
    """Legacy procedure participation tallies — superseded by competency_progress."""
    from app.modules.workforce.competency_engine import competency_summary_by_specialty

    sync_portfolio(user_id)
    return competency_summary_by_specialty(user_id, official_only=official_only)


# ---------------------------------------------------------------------------
# Event-driven incremental sync (Sprint 7A mandatory)
# ---------------------------------------------------------------------------


def sync_encounter_by_id(encounter_id: int) -> None:
    enc = ClinicalEncounter.query.filter_by(id=encounter_id, is_archived=False).first()
    if enc and enc.status == ENCOUNTER_STATUS_CLOSED and enc.created_by_id:
        _sync_encounters(enc.created_by_id)


def sync_history_session_by_id(session_id: int) -> None:
    session = HistorySession.query.filter_by(id=session_id, is_archived=False).first()
    if session:
        uid = session.created_by_id or session.diagnosis_confirmed_by_id
        _sync_history(uid)


def sync_follow_up_by_id(entry_id: int) -> None:
    entry = FollowUpEntry.query.filter_by(id=entry_id, is_archived=False).first()
    if entry and entry.documented_by_id:
        _sync_follow_ups(entry.documented_by_id)


def sync_procedure_session_by_id(session_id: int) -> None:
    session = ProcedureSession.query.filter_by(id=session_id, is_archived=False).first()
    if session:
        _sync_single_procedure_session(session)


def sync_report_by_id(report_id: int) -> None:
    report = Report.query.filter_by(id=report_id, is_archived=False).first()
    if report:
        _sync_single_report(report)


def sync_lab_result_set_by_id(result_set_id: int) -> None:
    rs = LabResultSet.query.filter_by(id=result_set_id, is_archived=False).first()
    if rs and rs.reviewed_by_id:
        _sync_investigations(rs.reviewed_by_id)


def sync_imaging_study_by_id(study_id: int) -> None:
    study = ImagingStudy.query.filter_by(id=study_id, is_archived=False).first()
    if study and study.reviewed_by_id:
        _sync_investigations(study.reviewed_by_id)


def sync_research_case_by_id(case_id: int) -> None:
    case = ResearchCase.query.filter_by(id=case_id, is_archived=False).first()
    if case and case.enrolled_by_id:
        _sync_research(case.enrolled_by_id)
