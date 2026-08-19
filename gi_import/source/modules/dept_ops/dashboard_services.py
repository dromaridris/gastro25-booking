"""Department Operations dashboards — Sprint 7C."""

from __future__ import annotations

from datetime import date

from app.engines import permission_engine
from app.modules.dept_ops.alert_services import collect_alerts
from app.modules.dept_ops.announcement_services import list_announcements, unread_announcements
from app.modules.dept_ops.calendar_services import room_schedule_calendar, waiting_list_schedule, weekly_roster_calendar
from app.modules.dept_ops.constants import ROOM_AVAILABLE, ROOM_OCCUPIED, SCOPE_AVAILABLE, SCOPE_AWAITING_CLEANING, SCOPE_IN_PROCEDURE
from app.modules.dept_ops.consumable_services import list_consumables, low_stock_items
from app.modules.dept_ops.integration import (
    active_procedures_today,
    completed_sessions_today,
    procedures_in_room,
    today_procedure_count,
)
from app.modules.dept_ops.reprocessing_services import cleaning_queue
from app.modules.dept_ops.resource_services import resources_under_maintenance
from app.modules.dept_ops.room_services import list_room_states, room_utilisation_pct
from app.modules.dept_ops.scope_services import scopes_by_status
from app.modules.dept_ops.waiting_list_services import delay_alerts, waiting_list_summary
from app.modules.dept_ops.workforce_integration import available_staff, department_attendance_summary


def _require(user, permission: str) -> None:
    permission_engine.require(user, permission)


def _base_context(acting_user) -> dict:
    return {"alerts": collect_alerts(acting_user)}


def get_hod_dashboard(acting_user) -> dict:
    _require(acting_user, "dept_ops:view")
    rooms = list_room_states(acting_user)
    occupied = [r for r in rooms if r["state"].status == ROOM_OCCUPIED]
    available_rooms = [r for r in rooms if r["state"].status == ROOM_AVAILABLE]
    utilisation = [
        {"room_id": r["room"].id, "name": r["room"].name, "pct": room_utilisation_pct(r["room"].id)}
        for r in rooms
    ]
    avg_util = round(sum(u["pct"] for u in utilisation) / len(utilisation), 1) if utilisation else 0.0
    wl = waiting_list_summary(acting_user)
    return {
        **_base_context(acting_user),
        "rooms_occupied": len(occupied),
        "rooms_available": len(available_rooms),
        "rooms_total": len(rooms),
        "active_procedures": procedures_in_room(),
        "available_scopes": scopes_by_status(acting_user, SCOPE_AVAILABLE),
        "scopes_awaiting_cleaning": scopes_by_status(acting_user, SCOPE_AWAITING_CLEANING),
        "scopes_in_procedure": scopes_by_status(acting_user, SCOPE_IN_PROCEDURE),
        "equipment_maintenance": resources_under_maintenance(acting_user),
        "waiting_list": wl,
        "waiting_pressure": wl["urgent_count"] + wl["delayed_count"],
        "low_stock": low_stock_items(acting_user),
        "staff_on_duty": available_staff(acting_user),
        "attendance_summary": department_attendance_summary(acting_user),
        "announcements": list_announcements(acting_user)[:10],
        "today_procedure_count": today_procedure_count(),
        "today_completed_count": completed_sessions_today(),
        "average_room_utilisation": avg_util,
        "room_board": rooms,
        "roster_calendar": weekly_roster_calendar(acting_user),
        "room_calendar": room_schedule_calendar(acting_user),
        "waiting_calendar": waiting_list_schedule(acting_user),
        "calendar_today": date.today(),
    }


def get_nurse_dashboard(acting_user) -> dict:
    _require(acting_user, "dept_ops:view")
    rooms = list_room_states(acting_user)
    assigned = [r for r in rooms if any(s.user_id == acting_user.id for s in r["staff"])]
    active_rooms = [r for r in rooms if r["state"].status == ROOM_OCCUPIED]
    return {
        **_base_context(acting_user),
        "assigned_rooms": assigned,
        "active_rooms": active_rooms,
        "active_procedures": active_procedures_today(),
        "cleaning_queue": cleaning_queue(acting_user),
        "scopes_awaiting": scopes_by_status(acting_user, SCOPE_AWAITING_CLEANING),
        "scopes_in_cleaning": scopes_by_status(acting_user, "cleaning"),
        "maintenance_alerts": scopes_by_status(acting_user, "maintenance"),
        "assigned_scopes": scopes_by_status(acting_user, SCOPE_IN_PROCEDURE),
        "consumables": list_consumables(acting_user),
        "low_stock": low_stock_items(acting_user),
        "announcements": unread_announcements(acting_user)[:5],
        "room_calendar": room_schedule_calendar(acting_user),
    }


def get_reception_dashboard(acting_user) -> dict:
    _require(acting_user, "dept_ops:view")
    from app.modules.appointments.models import Appointment
    from datetime import datetime

    today = date.today()
    start = datetime.combine(today, datetime.min.time())
    end = datetime.combine(today, datetime.max.time())
    bookings = (
        Appointment.query.filter_by(is_archived=False)
        .filter(Appointment.scheduled_at >= start)
        .filter(Appointment.scheduled_at <= end)
        .order_by(Appointment.scheduled_at.asc())
        .all()
    )
    rooms = list_room_states(acting_user)
    available_rooms = [r for r in rooms if r["state"].status == ROOM_AVAILABLE]
    delayed = delay_alerts(acting_user)
    wl = waiting_list_summary(acting_user)
    return {
        **_base_context(acting_user),
        "today_bookings": bookings,
        "waiting_list": wl,
        "waiting_patients": wl["entries"],
        "delayed_patients": delayed,
        "available_rooms": available_rooms,
        "rooms_total": len(rooms),
        "announcements": list_announcements(acting_user)[:5],
        "waiting_calendar": waiting_list_schedule(acting_user),
        "room_calendar": room_schedule_calendar(acting_user),
    }


def get_role_homepage(acting_user) -> dict:
    role = acting_user.role.code if acting_user.role else ""
    if permission_engine.check(acting_user, "dept_ops:manage"):
        return {"template": "dept_ops/hod_dashboard.html", "data": get_hod_dashboard(acting_user)}
    if role in {"endoscopy_nurse", "endoscopy_technician", "nurse"}:
        return {"template": "dept_ops/nurse_dashboard.html", "data": get_nurse_dashboard(acting_user)}
    if role == "reception_staff":
        return {"template": "dept_ops/reception_dashboard.html", "data": get_reception_dashboard(acting_user)}
    return {"template": "dept_ops/hod_dashboard.html", "data": get_hod_dashboard(acting_user)}
