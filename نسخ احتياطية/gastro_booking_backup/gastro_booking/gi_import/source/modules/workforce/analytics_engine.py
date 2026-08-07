"""Performance analytics for supervision — Sprint 7A. No ranking or public scoring."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta, timezone

from app.modules.auth.models import User
from app.modules.reports.models import Report, STATUS_DRAFT, STATUS_FINALIZED, STATUS_LOCKED
from app.modules.workforce.constants import (
    ACTIVITY_ENCOUNTER,
    ACTIVITY_HISTORY_TAKING,
    ACTIVITY_PROCEDURE,
    ACTIVITY_REPORT_AUTHORED,
    ACTIVITY_RESEARCH,
    OFFICIAL_VERIFY_STATUSES,
    TRAINEE_ROLE_CODES,
)
from app.modules.workforce.models import PortfolioEntry
from app.modules.workforce.portfolio_engine import sync_portfolio


def _month_key(dt: datetime) -> str:
    return dt.strftime("%Y-%m")


def user_kpis(user_id: int, *, months: int = 6, official_only: bool = True) -> dict:
    sync_portfolio(user_id)
    cutoff = datetime.now(timezone.utc) - timedelta(days=months * 31)

    query = PortfolioEntry.query.filter(
        PortfolioEntry.user_id == user_id,
        PortfolioEntry.is_archived.is_(False),
        PortfolioEntry.activity_at >= cutoff,
    )
    if official_only:
        query = query.filter(PortfolioEntry.verification_status.in_(OFFICIAL_VERIFY_STATUSES))

    entries = query.all()
    by_type: dict[str, int] = defaultdict(int)
    by_month: dict[str, int] = defaultdict(int)
    procedure_mix: dict[str, int] = defaultdict(int)

    for e in entries:
        by_type[e.activity_type] += 1
        by_month[_month_key(e.activity_at)] += 1
        if e.activity_type == ACTIVITY_PROCEDURE and e.competency_category:
            procedure_mix[e.competency_category] += 1

    reports_authored = by_type.get(ACTIVITY_REPORT_AUTHORED, 0)
    reports_pending = Report.query.filter_by(author_id=user_id, status=STATUS_DRAFT, is_archived=False).count()
    reports_finalized = Report.query.filter(
        Report.author_id == user_id,
        Report.status.in_([STATUS_FINALIZED, STATUS_LOCKED]),
        Report.is_archived.is_(False),
    ).count()

    turnaround_hours: list[float] = []
    for report in Report.query.filter(
        Report.author_id == user_id,
        Report.finalized_at.isnot(None),
        Report.is_archived.is_(False),
    ).all():
        if report.finalized_at and report.created_at:
            delta = report.finalized_at - report.created_at
            turnaround_hours.append(delta.total_seconds() / 3600)

    avg_turnaround = round(sum(turnaround_hours) / len(turnaround_hours), 1) if turnaround_hours else None
    active_days = len({e.activity_at.date() for e in entries})
    avg_daily = round(len(entries) / active_days, 1) if active_days else 0

    return {
        "user_id": user_id,
        "encounters": by_type.get(ACTIVITY_ENCOUNTER, 0),
        "histories": by_type.get(ACTIVITY_HISTORY_TAKING, 0),
        "procedures": by_type.get(ACTIVITY_PROCEDURE, 0),
        "reports_authored": reports_authored,
        "reports_finalized": reports_finalized,
        "reports_pending": reports_pending,
        "research_cases": by_type.get(ACTIVITY_RESEARCH, 0),
        "procedure_mix": dict(procedure_mix),
        "monthly_trend": dict(sorted(by_month.items())),
        "avg_daily_workload": avg_daily,
        "report_turnaround_hours": avg_turnaround,
        "completion_rate_pct": round(reports_finalized * 100 / (reports_finalized + reports_pending), 1)
        if (reports_finalized + reports_pending)
        else 100.0,
    }


def department_summary(department_id: int = 1) -> dict:
    trainees = (
        User.query.filter(User.is_archived.is_(False), User.department_id == department_id)
        .all()
    )
    trainee_users = [u for u in trainees if u.role and u.role.code in TRAINEE_ROLE_CODES]

    summaries = []
    for user in trainee_users:
        sync_portfolio(user.id)
        summaries.append({"user": user, "kpis": user_kpis(user.id)})

    totals = {
        "encounters": sum(s["kpis"]["encounters"] for s in summaries),
        "procedures": sum(s["kpis"]["procedures"] for s in summaries),
        "reports": sum(s["kpis"]["reports_authored"] for s in summaries),
        "research": sum(s["kpis"]["research_cases"] for s in summaries),
    }
    return {"trainees": summaries, "department_totals": totals, "trainee_count": len(trainee_users)}


def compare_trainees(department_id: int = 1) -> list[dict]:
    """Side-by-side trainee comparison for HoD supervision — not public ranking."""
    summary = department_summary(department_id)
    rows = []
    for item in summary["trainees"]:
        user = item["user"]
        kpis = item["kpis"]
        rows.append(
            {
                "user_id": user.id,
                "name": user.full_name,
                "role": user.role.code if user.role else None,
                "encounters": kpis["encounters"],
                "procedures": kpis["procedures"],
                "reports": kpis["reports_authored"],
                "research": kpis["research_cases"],
                "avg_daily": kpis["avg_daily_workload"],
            }
        )
    return rows
