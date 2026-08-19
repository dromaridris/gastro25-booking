"""Operational calendar views — Sprint 7C."""

from __future__ import annotations

from datetime import date, datetime, timedelta

from app.engines import permission_engine
from app.modules.dept_ops.models import DutyRosterEntry, RoomScheduleSlot, WaitingListEntry
from app.modules.procedures.models import EndoscopyRoom


def _require(user, permission: str) -> None:
    permission_engine.require(user, permission)


def week_start(on_date: date | None = None) -> date:
    target = on_date or date.today()
    return target - timedelta(days=target.weekday())


def weekly_roster_calendar(acting_user, on_date: date | None = None) -> dict:
    _require(acting_user, "dept_ops:view")
    start = week_start(on_date)
    days = [start + timedelta(days=i) for i in range(7)]
    grid: dict[str, list] = {d.isoformat(): [] for d in days}
    for d in days:
        entries = DutyRosterEntry.query.filter_by(roster_date=d, is_archived=False).order_by(
            DutyRosterEntry.shift_type.asc()
        ).all()
        grid[d.isoformat()] = entries
    return {"week_start": start, "days": days, "grid": grid}


def room_schedule_calendar(acting_user, *, room_id: int | None = None, on_date: date | None = None) -> dict:
    _require(acting_user, "dept_ops:view")
    target = on_date or date.today()
    day_start = datetime.combine(target, datetime.min.time())
    day_end = datetime.combine(target, datetime.max.time())
    rooms = (
        [EndoscopyRoom.query.get(room_id)]
        if room_id
        else EndoscopyRoom.query.filter_by(is_archived=False).order_by(EndoscopyRoom.name.asc()).all()
    )
    schedules = {}
    for room in rooms:
        if room is None:
            continue
        slots = (
            RoomScheduleSlot.query.filter_by(room_id=room.id, is_archived=False)
            .filter(RoomScheduleSlot.start_at >= day_start, RoomScheduleSlot.start_at <= day_end)
            .order_by(RoomScheduleSlot.start_at.asc())
            .all()
        )
        schedules[room.id] = {"room": room, "slots": slots}
    hours = list(range(7, 20))
    return {"date": target, "hours": hours, "schedules": schedules}


def waiting_list_schedule(acting_user, on_date: date | None = None) -> dict:
    _require(acting_user, "dept_ops:view")
    start = week_start(on_date)
    days = [start + timedelta(days=i) for i in range(7)]
    grid: dict[str, list] = {d.isoformat(): [] for d in days}
    for d in days:
        scheduled = WaitingListEntry.query.filter_by(is_archived=False, scheduled_date=d).order_by(
            WaitingListEntry.priority.desc()
        ).all()
        active = WaitingListEntry.query.filter_by(is_archived=False, status="active").filter(
            WaitingListEntry.listed_at <= datetime.combine(d, datetime.max.time())
        ).all()
        grid[d.isoformat()] = {"scheduled": scheduled, "active_unscheduled": active if d == date.today() else []}
    return {"week_start": start, "days": days, "grid": grid}
