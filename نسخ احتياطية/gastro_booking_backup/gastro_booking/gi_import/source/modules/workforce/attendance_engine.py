"""Activity-based attendance engine — Sprint 7A."""

from __future__ import annotations

from calendar import monthrange
from datetime import date, datetime, timedelta, timezone

from app.modules.workforce.constants import OFFICIAL_VERIFY_STATUSES
from app.modules.workforce.models import AttendanceAdjustment, PortfolioEntry


def _date_only(dt: datetime | date) -> date:
    if isinstance(dt, datetime):
        return dt.date()
    return dt


def active_dates_for_user(user_id: int, period_start: date, period_end: date) -> set[date]:
    """Days with verified clinical activity or approved manual adjustment."""
    active: set[date] = set()

    entries = PortfolioEntry.query.filter(
        PortfolioEntry.user_id == user_id,
        PortfolioEntry.is_archived.is_(False),
        PortfolioEntry.verification_status.in_(OFFICIAL_VERIFY_STATUSES),
        PortfolioEntry.activity_at >= datetime.combine(period_start, datetime.min.time(), tzinfo=timezone.utc),
        PortfolioEntry.activity_at <= datetime.combine(period_end, datetime.max.time(), tzinfo=timezone.utc),
    ).all()
    for entry in entries:
        active.add(_date_only(entry.activity_at))

    adjustments = AttendanceAdjustment.query.filter(
        AttendanceAdjustment.user_id == user_id,
        AttendanceAdjustment.is_archived.is_(False),
        AttendanceAdjustment.adjustment_date >= period_start,
        AttendanceAdjustment.adjustment_date <= period_end,
    ).all()
    for adj in adjustments:
        active.add(adj.adjustment_date)

    return active


def attendance_score(user_id: int, *, year: int | None = None, month: int | None = None) -> dict:
    """
    Activity-based attendance score for a calendar month.
    No clinical activity on a weekday = absent by default.
    """
    today = date.today()
    year = year or today.year
    month = month or today.month
    _, days_in_month = monthrange(year, month)
    period_start = date(year, month, 1)
    period_end = date(year, month, days_in_month)

    weekdays = []
    d = period_start
    while d <= period_end:
        if d.weekday() < 5:
            weekdays.append(d)
        d += timedelta(days=1)

    active = active_dates_for_user(user_id, period_start, period_end)
    present_weekdays = [d for d in weekdays if d in active]
    expected = len(weekdays)
    present = len(present_weekdays)
    score = round(present * 100 / expected, 1) if expected else 0.0

    return {
        "year": year,
        "month": month,
        "expected_days": expected,
        "present_days": present,
        "absent_days": expected - present,
        "attendance_pct": score,
        "active_dates": sorted(active),
    }


def daily_activity_summary(user_id: int, target_date: date | None = None) -> dict:
    target = target_date or date.today()
    start = datetime.combine(target, datetime.min.time(), tzinfo=timezone.utc)
    end = datetime.combine(target, datetime.max.time(), tzinfo=timezone.utc)

    entries = PortfolioEntry.query.filter(
        PortfolioEntry.user_id == user_id,
        PortfolioEntry.is_archived.is_(False),
        PortfolioEntry.activity_at >= start,
        PortfolioEntry.activity_at <= end,
    ).order_by(PortfolioEntry.activity_at.asc()).all()

    by_type: dict[str, int] = {}
    for e in entries:
        by_type[e.activity_type] = by_type.get(e.activity_type, 0) + 1

    return {
        "date": target.isoformat(),
        "total_activities": len(entries),
        "by_type": by_type,
        "entries": entries,
    }
