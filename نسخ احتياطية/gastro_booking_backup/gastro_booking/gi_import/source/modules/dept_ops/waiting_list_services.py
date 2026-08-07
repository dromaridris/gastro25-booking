"""Waiting list engine — Sprint 7C."""

from __future__ import annotations

from datetime import date, timedelta

from app.core.base_model import utcnow
from app.core.exceptions import NotFoundError, ValidationError
from app.extensions import db
from app.engines import audit_engine, permission_engine
from app.modules.dept_ops.constants import ALL_WAITING_LIST_STATUSES, WL_ACTIVE, WL_SCHEDULED
from app.modules.dept_ops.models import WaitingListEntry
from app.modules.procedures.models import ALL_PRIORITIES


def _require(user, permission: str) -> None:
    permission_engine.require(user, permission)


def list_waiting_list(acting_user, *, status: str | None = None) -> list[WaitingListEntry]:
    _require(acting_user, "dept_ops:view")
    query = WaitingListEntry.query.filter_by(is_archived=False)
    if status:
        query = query.filter_by(status=status)
    return query.order_by(WaitingListEntry.priority.desc(), WaitingListEntry.listed_at.asc()).all()


def add_to_waiting_list(
    acting_user,
    *,
    patient_id: int,
    procedure_type_id: int,
    priority: str = "routine",
    consultant_id: int | None = None,
    scheduled_date: date | None = None,
) -> WaitingListEntry:
    _require(acting_user, "dept_ops:waiting_list")
    if priority not in ALL_PRIORITIES:
        raise ValidationError(f"Invalid priority '{priority}'.")
    entry = WaitingListEntry(
        patient_id=patient_id,
        procedure_type_id=procedure_type_id,
        priority=priority,
        consultant_id=consultant_id,
        listed_at=utcnow(),
        scheduled_date=scheduled_date,
        status=WL_SCHEDULED if scheduled_date else WL_ACTIVE,
        department_id=getattr(acting_user, "department_id", 1) or 1,
        created_by_id=acting_user.id,
    )
    db.session.add(entry)
    audit_engine.log("dept_ops.waiting_list_added", user=acting_user, target_type="waiting_list_entry", target_id=entry.id)
    db.session.commit()
    return entry


def schedule_waiting_list_entry(
    acting_user, entry: WaitingListEntry, scheduled_date: date, procedure_id: int | None = None
) -> WaitingListEntry:
    _require(acting_user, "dept_ops:waiting_list")
    entry.scheduled_date = scheduled_date
    entry.procedure_id = procedure_id
    entry.status = WL_SCHEDULED
    db.session.commit()
    return entry


def waiting_duration_days(entry: WaitingListEntry) -> int:
    listed = entry.listed_at
    now = utcnow()
    if listed.tzinfo is None and now.tzinfo is not None:
        listed = listed.replace(tzinfo=now.tzinfo)
    elif listed.tzinfo is not None and now.tzinfo is None:
        now = now.replace(tzinfo=listed.tzinfo)
    delta = now - listed
    return max(delta.days, 0)


def delay_alerts(acting_user, *, threshold_days: int = 30) -> list[WaitingListEntry]:
    _require(acting_user, "dept_ops:view")
    cutoff = utcnow() - timedelta(days=threshold_days)
    return (
        WaitingListEntry.query.filter_by(is_archived=False, status=WL_ACTIVE, delay_alert_sent=False)
        .filter(WaitingListEntry.listed_at <= cutoff)
        .order_by(WaitingListEntry.listed_at.asc())
        .all()
    )


def waiting_list_summary(acting_user) -> dict:
    _require(acting_user, "dept_ops:view")
    entries = list_waiting_list(acting_user, status=WL_ACTIVE)
    scheduled = list_waiting_list(acting_user, status=WL_SCHEDULED)
    return {
        "active_count": len(entries),
        "scheduled_count": len(scheduled),
        "urgent_count": sum(1 for e in entries if e.priority in {"urgent", "emergency"}),
        "delayed_count": len(delay_alerts(acting_user)),
        "entries": entries[:20],
    }
