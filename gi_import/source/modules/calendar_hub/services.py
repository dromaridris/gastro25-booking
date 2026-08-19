"""Calendar aggregator — pulls events from clinical and ops modules."""

from __future__ import annotations

from datetime import date, datetime, timedelta

from app.engines import permission_engine
from app.modules.appointments.models import Appointment
from app.modules.calendar_hub.models import EVENT_APPOINTMENT, EVENT_DUTY, EVENT_EDUCATION, EVENT_PROCEDURE, EVENT_ROSTER, CalendarEvent
from app.modules.dept_ops.models import DutyRosterEntry
from app.modules.education.models import EducationActivity
from app.modules.procedures.models import Procedure


def _require(user, code: str):
    permission_engine.require(user, code)


def week_start(on_date: date | None = None) -> date:
    target = on_date or date.today()
    return target - timedelta(days=target.weekday())


def aggregate_week(acting_user, on_date: date | None = None) -> dict:
    _require(acting_user, "calendar:view")
    start = week_start(on_date)
    end = start + timedelta(days=7)
    day_start = datetime.combine(start, datetime.min.time())
    day_end = datetime.combine(end, datetime.min.time())
    events: list[dict] = []

    for appt in Appointment.query.filter(
        Appointment.is_archived.is_(False),
        Appointment.scheduled_at >= day_start,
        Appointment.scheduled_at < day_end,
    ).all():
        events.append({
            "type": EVENT_APPOINTMENT,
            "title": f"Appointment: {appt.patient.full_name if appt.patient else 'Patient'}",
            "start_at": appt.scheduled_at,
            "end_at": None,
            "source_id": appt.id,
            "link": f"/appointments/{appt.id}",
        })

    for proc in (
        Procedure.query.join(Appointment)
        .filter(
            Procedure.is_archived.is_(False),
            Appointment.scheduled_at >= day_start,
            Appointment.scheduled_at < day_end,
        )
        .all()
    ):
        appt_time = proc.appointment.scheduled_at if proc.appointment else None
        if appt_time is None:
            continue
        events.append({
            "type": EVENT_PROCEDURE,
            "title": f"Procedure: {proc.procedure_type.name if proc.procedure_type else 'Endoscopy'}",
            "start_at": appt_time,
            "end_at": None,
            "source_id": proc.id,
            "link": f"/procedures/{proc.id}",
        })

    for entry in DutyRosterEntry.query.filter(
        DutyRosterEntry.is_archived.is_(False),
        DutyRosterEntry.roster_date >= start,
        DutyRosterEntry.roster_date < end,
    ).all():
        events.append({
            "type": EVENT_ROSTER,
            "title": f"Roster: {entry.shift_type}",
            "start_at": datetime.combine(entry.roster_date, datetime.min.time()),
            "end_at": None,
            "source_id": entry.id,
            "link": "/dept-ops/roster",
        })

    for edu in EducationActivity.query.filter(
        EducationActivity.is_archived.is_(False),
        EducationActivity.activity_date >= start,
        EducationActivity.activity_date < end,
    ).all():
        events.append({
            "type": EVENT_EDUCATION,
            "title": edu.title,
            "start_at": datetime.combine(edu.activity_date, datetime.min.time()),
            "end_at": None,
            "source_id": edu.id,
            "link": f"/education/{edu.id}",
        })

    for custom in CalendarEvent.query.filter(
        CalendarEvent.is_archived.is_(False),
        CalendarEvent.start_at >= day_start,
        CalendarEvent.start_at < day_end,
    ).all():
        events.append({
            "type": custom.event_type,
            "title": custom.title,
            "start_at": custom.start_at,
            "end_at": custom.end_at,
            "source_id": custom.id,
            "link": None,
        })

    days = [start + timedelta(days=i) for i in range(7)]
    grid: dict[str, list] = {d.isoformat(): [] for d in days}
    for ev in events:
        day_key = ev["start_at"].date().isoformat()
        if day_key in grid:
            grid[day_key].append(ev)
    for day_events in grid.values():
        day_events.sort(key=lambda e: e["start_at"])

    return {"week_start": start, "days": days, "grid": grid, "events": events}
