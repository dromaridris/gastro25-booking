"""Role-based dashboards and worklists — Sprint 7A."""

from __future__ import annotations

from datetime import date, datetime, timezone

from app.modules.appointments.models import Appointment
from app.modules.auth.models import User
from app.modules.procedures.models import Procedure, STATUS_BOOKED, STATUS_IN_ROOM, STATUS_READY, STATUS_WAITING
from app.modules.reports.models import Report, STATUS_DRAFT
from app.modules.workforce.analytics_engine import compare_trainees, department_summary, user_kpis
from app.modules.workforce.attendance_engine import attendance_score, daily_activity_summary
from app.modules.workforce.constants import (
    OFFICIAL_VERIFY_STATUSES,
    ROLE_CONSULTANT,
    ROLE_CORE_CONSULTANT,
    ROLE_ENDOSCOPY_NURSE,
    ROLE_ENDOSCOPY_TECH,
    ROLE_HEAD,
    ROLE_HOUSE_OFFICER,
    ROLE_NURSE,
    ROLE_RECEPTION,
    ROLE_SENIOR_REGISTRAR,
    TRAINEE_ROLE_CODES,
    VERIFY_DRAFT,
)
from app.modules.workforce.models import PortfolioEntry
from app.modules.workforce.competency_engine import competency_progress_for_user, seed_competency_standards
from app.modules.workforce.portfolio_engine import sync_portfolio


def _role_code(user: User) -> str:
    return user.role.code if user.role else ""


def _today_start() -> datetime:
    today = date.today()
    return datetime.combine(today, datetime.min.time(), tzinfo=timezone.utc)


def get_trainee_dashboard(user: User) -> dict:
    sync_portfolio(user.id)
    seed_competency_standards()
    today = daily_activity_summary(user.id)
    month = attendance_score(user.id)
    kpis = user_kpis(user.id, official_only=False)
    competencies = competency_progress_for_user(user.id, official_only=False)
    pending_verify = PortfolioEntry.query.filter_by(
        user_id=user.id, verification_status=VERIFY_DRAFT, is_archived=False
    ).count()
    pending_reports = Report.query.filter_by(author_id=user.id, status=STATUS_DRAFT, is_archived=False).count()

    return {
        "today": today,
        "monthly_activity": kpis["monthly_trend"],
        "procedure_totals": competencies,
        "pending_reports": pending_reports,
        "research_participation": kpis["research_cases"],
        "portfolio_progress": {
            "total_entries": PortfolioEntry.query.filter_by(user_id=user.id, is_archived=False).count(),
            "verified_entries": PortfolioEntry.query.filter(
                PortfolioEntry.user_id == user.id,
                PortfolioEntry.verification_status.in_(OFFICIAL_VERIFY_STATUSES),
                PortfolioEntry.is_archived.is_(False),
            ).count(),
            "pending_verification": pending_verify,
        },
        "attendance": month,
        "competencies": competencies,
        "kpis": kpis,
    }


def get_hod_dashboard(acting_user: User) -> dict:
    dept = department_summary(acting_user.department_id or 1)
    comparison = compare_trainees(acting_user.department_id or 1)
    return {
        "department": dept,
        "trainee_comparison": comparison,
        "workload_summary": dept["department_totals"],
    }


def get_consultant_worklist(user: User) -> dict:
    sync_portfolio(user.id)
    pending_reports = Report.query.filter_by(author_id=user.id, status=STATUS_DRAFT, is_archived=False).limit(20).all()
    pending_supervision = PortfolioEntry.query.filter_by(
        verification_status=VERIFY_DRAFT, is_archived=False
    ).order_by(PortfolioEntry.activity_at.desc()).limit(20).all()
    today_patients = Procedure.query.filter(
        Procedure.is_archived.is_(False),
        Procedure.endoscopist_id == user.id,
        Procedure.status.in_([STATUS_BOOKED, STATUS_WAITING, STATUS_READY, STATUS_IN_ROOM]),
    ).limit(20).all()
    return {
        "pending_reports": pending_reports,
        "pending_supervision": pending_supervision,
        "today_procedures": today_patients,
    }


def get_reception_worklist() -> dict:
    today = date.today()
    start = datetime.combine(today, datetime.min.time(), tzinfo=timezone.utc)
    end = datetime.combine(today, datetime.max.time(), tzinfo=timezone.utc)
    appointments = (
        Appointment.query.filter(
            Appointment.is_archived.is_(False),
            Appointment.scheduled_at >= start,
            Appointment.scheduled_at <= end,
        )
        .order_by(Appointment.scheduled_at.asc())
        .limit(50)
        .all()
    )
    waiting = Procedure.query.filter_by(is_archived=False, status=STATUS_WAITING).limit(30).all()
    return {"appointments": appointments, "waiting_list": waiting}


def get_endoscopy_nurse_worklist() -> dict:
    today_procedures = (
        Procedure.query.filter(
            Procedure.is_archived.is_(False),
            Procedure.status.in_([STATUS_READY, STATUS_IN_ROOM, STATUS_WAITING]),
        )
        .order_by(Procedure.updated_at.desc())
        .limit(30)
        .all()
    )
    return {"endoscopy_list": today_procedures}


def get_role_homepage(user: User) -> dict:
    code = _role_code(user)
    sync_portfolio(user.id)

    if code == ROLE_HEAD:
        return {"template": "workforce/hod_dashboard.html", "data": get_hod_dashboard(user)}
    if code in TRAINEE_ROLE_CODES:
        return {"template": "workforce/trainee_dashboard.html", "data": get_trainee_dashboard(user)}
    if code in {ROLE_CONSULTANT, ROLE_CORE_CONSULTANT}:
        return {"template": "workforce/consultant_dashboard.html", "data": get_consultant_worklist(user)}
    if code in {ROLE_ENDOSCOPY_NURSE, ROLE_NURSE}:
        return {"template": "workforce/endoscopy_nurse_dashboard.html", "data": get_endoscopy_nurse_worklist()}
    if code == ROLE_ENDOSCOPY_TECH:
        return {"template": "workforce/endoscopy_nurse_dashboard.html", "data": get_endoscopy_nurse_worklist()}
    if code == ROLE_RECEPTION:
        return {"template": "workforce/reception_dashboard.html", "data": get_reception_worklist()}

    return {
        "template": "workforce/generic_dashboard.html",
        "data": {"today": daily_activity_summary(user.id), "kpis": user_kpis(user.id, official_only=False)},
    }
