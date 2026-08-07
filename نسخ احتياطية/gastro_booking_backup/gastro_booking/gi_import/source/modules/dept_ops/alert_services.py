"""Unified operational alert centre — Sprint 7C."""

from __future__ import annotations

from datetime import date, timedelta

from app.core.base_model import utcnow
from app.engines import permission_engine
from app.modules.dept_ops.constants import (
    ROOM_MAINTENANCE,
    ROOM_OUT_OF_SERVICE,
    SCOPE_AWAITING_CLEANING,
    SCOPE_MAINTENANCE,
)
from app.modules.dept_ops.consumable_services import low_stock_items
from app.modules.dept_ops.models import Endoscope, RoomOperationsState, ScopeReprocessingCycle, WaitingListEntry
from app.modules.dept_ops.resource_services import resources_under_maintenance
from app.modules.dept_ops.roster_services import staff_on_duty
from app.modules.dept_ops.waiting_list_services import delay_alerts
from app.modules.dept_ops.workforce_integration import available_staff
from app.modules.procedures.models import EndoscopyRoom

ALERT_LOW_STOCK = "low_stock"
ALERT_SCOPE_MAINTENANCE = "scope_maintenance_overdue"
ALERT_REPROCESSING_OVERDUE = "reprocessing_overdue"
ALERT_WAITING_DELAY = "waiting_delay"
ALERT_ROOM_UNAVAILABLE = "room_unavailable"
ALERT_STAFF_SHORTAGE = "staff_shortage"
ALERT_EQUIPMENT_UNAVAILABLE = "equipment_unavailable"


def _require(user, permission: str) -> None:
    permission_engine.require(user, permission)


def collect_alerts(acting_user) -> list[dict]:
    _require(acting_user, "dept_ops:view")
    alerts: list[dict] = []

    for item in low_stock_items(acting_user):
        alerts.append(
            {
                "type": ALERT_LOW_STOCK,
                "severity": "high" if item.current_stock == 0 else "medium",
                "title": f"Low stock: {item.name}",
                "detail": f"{item.current_stock} remaining (minimum {item.minimum_stock})",
                "resource_id": item.id,
            }
        )

    now = utcnow()
    for scope in Endoscope.query.filter_by(is_archived=False).filter(
        Endoscope.next_maintenance_at.isnot(None),
        Endoscope.next_maintenance_at <= now,
    ).all():
        alerts.append(
            {
                "type": ALERT_SCOPE_MAINTENANCE,
                "severity": "high",
                "title": f"Scope maintenance overdue: {scope.scope_code}",
                "detail": scope.model or scope.scope_type,
                "resource_id": scope.id,
            }
        )

    cutoff = now - timedelta(hours=4)
    for cycle in ScopeReprocessingCycle.query.filter_by(status="in_progress", is_archived=False).filter(
        ScopeReprocessingCycle.started_at <= cutoff
    ).all():
        alerts.append(
            {
                "type": ALERT_REPROCESSING_OVERDUE,
                "severity": "medium",
                "title": f"Reprocessing overdue: scope #{cycle.scope_id}",
                "detail": f"Step: {cycle.current_step}",
                "resource_id": cycle.id,
            }
        )

    for entry in delay_alerts(acting_user, threshold_days=30):
        from app.modules.dept_ops.waiting_list_services import waiting_duration_days

        days = waiting_duration_days(entry)
        alerts.append(
            {
                "type": ALERT_WAITING_DELAY,
                "severity": "high" if entry.priority == "emergency" else "medium",
                "title": f"Waiting list delay: patient #{entry.patient_id}",
                "detail": f"{days} days waiting — {entry.priority} priority",
                "resource_id": entry.id,
            }
        )

    for state in RoomOperationsState.query.filter_by(is_archived=False).filter(
        RoomOperationsState.status.in_([ROOM_MAINTENANCE, ROOM_OUT_OF_SERVICE])
    ).all():
        room = EndoscopyRoom.query.get(state.room_id)
        alerts.append(
            {
                "type": ALERT_ROOM_UNAVAILABLE,
                "severity": "medium",
                "title": f"Room unavailable: {room.name if room else state.room_id}",
                "detail": state.status.replace("_", " "),
                "resource_id": state.room_id,
            }
        )

    on_duty = available_staff(acting_user)
    rooms = EndoscopyRoom.query.filter_by(is_archived=False).count()
    if rooms and len(on_duty) < max(rooms // 2, 1):
        alerts.append(
            {
                "type": ALERT_STAFF_SHORTAGE,
                "severity": "high",
                "title": "Staff shortage today",
                "detail": f"{len(on_duty)} staff on duty for {rooms} rooms",
                "resource_id": None,
            }
        )

    for resource in resources_under_maintenance(acting_user):
        alerts.append(
            {
                "type": ALERT_EQUIPMENT_UNAVAILABLE,
                "severity": "medium",
                "title": f"Equipment unavailable: {resource.name}",
                "detail": resource.resource_type,
                "resource_id": resource.id,
            }
        )

    severity_order = {"high": 0, "medium": 1, "low": 2}
    alerts.sort(key=lambda a: severity_order.get(a["severity"], 9))
    return alerts
