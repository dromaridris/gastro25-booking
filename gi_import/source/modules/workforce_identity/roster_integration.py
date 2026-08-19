"""Integration hooks for duty roster — does not modify frozen dept_ops services."""

from __future__ import annotations

from datetime import date

from app.extensions import db
from app.modules.dept_ops.models import DutyRosterEntry


def roster_entry_snapshot(entry: DutyRosterEntry) -> dict:
    return {
        "id": entry.id,
        "user_id": entry.user_id,
        "roster_date": entry.roster_date.isoformat(),
        "shift_type": entry.shift_type,
        "is_on_call": entry.is_on_call,
        "is_leave": entry.is_leave,
        "cover_for_user_id": entry.cover_for_user_id,
    }


def list_user_upcoming_duties(user_id: int, *, from_date: date | None = None, limit: int = 10) -> list[DutyRosterEntry]:
    target = from_date or date.today()
    return (
        DutyRosterEntry.query.filter(
            DutyRosterEntry.user_id == user_id,
            DutyRosterEntry.roster_date >= target,
            DutyRosterEntry.is_archived.is_(False),
            DutyRosterEntry.is_leave.is_(False),
        )
        .order_by(DutyRosterEntry.roster_date.asc(), DutyRosterEntry.shift_type.asc())
        .limit(limit)
        .all()
    )


def list_today_on_duty(*, roster_date: date | None = None) -> list[DutyRosterEntry]:
    target = roster_date or date.today()
    return (
        DutyRosterEntry.query.filter(
            DutyRosterEntry.roster_date == target,
            DutyRosterEntry.is_archived.is_(False),
            DutyRosterEntry.is_leave.is_(False),
        )
        .order_by(DutyRosterEntry.shift_type.asc())
        .all()
    )


def apply_swap_to_roster(original_entry: DutyRosterEntry, replacement_user_id: int) -> dict:
    """Swap assigned user on original duty entry — integration hook for approved swaps."""
    before = roster_entry_snapshot(original_entry)
    original_entry.user_id = replacement_user_id
    original_entry.cover_for_user_id = before["user_id"]
    db.session.flush()
    after = roster_entry_snapshot(original_entry)
    return {"before": before, "after": after}
