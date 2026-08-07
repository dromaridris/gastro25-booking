"""Duty roster management — Sprint 7C."""

from __future__ import annotations

from datetime import date

from app.core.exceptions import ValidationError
from app.extensions import db
from app.engines import permission_engine
from app.modules.dept_ops.constants import ALL_SHIFT_TYPES
from app.modules.dept_ops.models import DutyRosterEntry


def _require(user, permission: str) -> None:
    permission_engine.require(user, permission)


def list_roster(acting_user, *, roster_date: date | None = None) -> list[DutyRosterEntry]:
    _require(acting_user, "dept_ops:view")
    target = roster_date or date.today()
    return (
        DutyRosterEntry.query.filter_by(roster_date=target, is_archived=False)
        .order_by(DutyRosterEntry.shift_type.asc())
        .all()
    )


def create_roster_entry(
    acting_user,
    *,
    user_id: int,
    roster_date: date,
    shift_type: str,
    shift_start=None,
    shift_end=None,
    is_on_call: bool = False,
    is_leave: bool = False,
    cover_for_user_id: int | None = None,
    notes: str | None = None,
) -> DutyRosterEntry:
    _require(acting_user, "dept_ops:roster_manage")
    if shift_type not in ALL_SHIFT_TYPES:
        raise ValidationError(f"Invalid shift type '{shift_type}'.")
    entry = DutyRosterEntry(
        user_id=user_id,
        roster_date=roster_date,
        shift_type=shift_type,
        shift_start=shift_start,
        shift_end=shift_end,
        is_on_call=is_on_call,
        is_leave=is_leave,
        cover_for_user_id=cover_for_user_id,
        notes=notes,
        department_id=getattr(acting_user, "department_id", 1) or 1,
        created_by_id=acting_user.id,
    )
    db.session.add(entry)
    db.session.commit()
    return entry


def staff_on_duty(acting_user, *, roster_date: date | None = None) -> list[DutyRosterEntry]:
    target = roster_date or date.today()
    return [e for e in list_roster(acting_user, roster_date=target) if not e.is_leave]
