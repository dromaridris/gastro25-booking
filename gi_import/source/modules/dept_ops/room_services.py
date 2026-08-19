"""Endoscopy room operations — Sprint 7C."""

from __future__ import annotations

from datetime import date, datetime

from app.core.base_model import utcnow
from app.core.exceptions import NotFoundError, ValidationError
from app.extensions import db
from app.engines import audit_engine, permission_engine
from app.modules.dept_ops.audit_helper import log_status_change
from app.modules.dept_ops.constants import (
    RESOURCE_ROOM,
    ROOM_AVAILABLE,
    ROOM_OCCUPIED,
)
from app.modules.dept_ops.integration import sync_room_from_procedure
from app.modules.dept_ops.models import RoomOperationsState, RoomScheduleSlot, RoomStaffAssignment
from app.modules.procedures.models import EndoscopyRoom


def _require(user, permission: str) -> None:
    permission_engine.require(user, permission)


def get_or_create_room_state(room_id: int) -> RoomOperationsState:
    state = RoomOperationsState.query.filter_by(room_id=room_id, is_archived=False).first()
    if state:
        return state
    state = RoomOperationsState(room_id=room_id, department_id=1, created_by_id=None)
    db.session.add(state)
    db.session.flush()
    return state


def list_room_states(acting_user) -> list[dict]:
    _require(acting_user, "dept_ops:view")
    rooms = EndoscopyRoom.query.filter_by(is_archived=False).order_by(EndoscopyRoom.name.asc()).all()
    result = []
    for room in rooms:
        state = get_or_create_room_state(room.id)
        staff = RoomStaffAssignment.query.filter_by(
            room_id=room.id, assignment_date=date.today(), is_archived=False
        ).all()
        slots = RoomScheduleSlot.query.filter_by(room_id=room.id, is_archived=False).order_by(
            RoomScheduleSlot.start_at.asc()
        ).all()
        result.append(
            {
                "room": room,
                "state": state,
                "staff": staff,
                "schedule": slots,
                "availability": state.status == ROOM_AVAILABLE,
            }
        )
    return result


def update_room_status(acting_user, room_id: int, status: str, notes: str | None = None) -> RoomOperationsState:
    _require(acting_user, "dept_ops:room_manage")
    from app.modules.dept_ops.constants import ALL_ROOM_STATUSES

    if status not in ALL_ROOM_STATUSES:
        raise ValidationError(f"Invalid room status '{status}'.")
    state = get_or_create_room_state(room_id)
    prev = state.status
    state.status = status
    state.notes = notes
    if status != ROOM_OCCUPIED:
        state.current_procedure_id = None
    log_status_change(
        acting_user=acting_user,
        resource_type=RESOURCE_ROOM,
        resource_id=room_id,
        previous_status=prev,
        new_status=status,
        notes=notes,
    )
    db.session.commit()
    return state


def assign_room_staff(
    acting_user, room_id: int, user_id: int, assignment_date: date, role_label: str = "staff"
) -> RoomStaffAssignment:
    _require(acting_user, "dept_ops:room_manage")
    from app.modules.dept_ops.workforce_integration import is_user_on_leave

    if is_user_on_leave(user_id, assignment_date):
        raise ValidationError("Staff member is on approved leave and cannot be assigned.")
    assignment = RoomStaffAssignment(
        room_id=room_id,
        user_id=user_id,
        assignment_date=assignment_date,
        role_label=role_label,
        department_id=getattr(acting_user, "department_id", 1) or 1,
        created_by_id=acting_user.id,
    )
    db.session.add(assignment)
    db.session.commit()
    return assignment


def _slots_overlap(room_id: int, start_at: datetime, end_at: datetime, exclude_id: int | None = None) -> bool:
    query = RoomScheduleSlot.query.filter_by(room_id=room_id, is_archived=False).filter(
        RoomScheduleSlot.start_at < end_at,
        RoomScheduleSlot.end_at > start_at,
    )
    if exclude_id:
        query = query.filter(RoomScheduleSlot.id != exclude_id)
    return query.first() is not None


def book_room_slot(
    acting_user,
    room_id: int,
    start_at: datetime,
    end_at: datetime,
    *,
    procedure_id: int | None = None,
    title: str | None = None,
    notes: str | None = None,
) -> RoomScheduleSlot:
    _require(acting_user, "dept_ops:room_manage")
    if end_at <= start_at:
        raise ValidationError("End time must be after start time.")
    if _slots_overlap(room_id, start_at, end_at):
        raise ValidationError("Room is already booked for this time slot — double booking prevented.")
    state = get_or_create_room_state(room_id)
    if state.status in {"maintenance", "out_of_service"}:
        raise ValidationError("Room is not available for booking.")
    slot = RoomScheduleSlot(
        room_id=room_id,
        procedure_id=procedure_id,
        start_at=start_at,
        end_at=end_at,
        title=title,
        notes=notes,
        department_id=getattr(acting_user, "department_id", 1) or 1,
        created_by_id=acting_user.id,
    )
    db.session.add(slot)
    audit_engine.log(
        "dept_ops.room_slot_booked",
        user=acting_user,
        target_type="room_schedule_slot",
        target_id=room_id,
        details={"start": start_at.isoformat(), "end": end_at.isoformat()},
    )
    db.session.commit()
    return slot


def sync_room_state_for_procedure(procedure, acting_user) -> None:
    if procedure.room_id is None:
        return
    state = get_or_create_room_state(procedure.room_id)
    prev = state.status
    sync_room_from_procedure(state, procedure)
    if state.status != prev:
        log_status_change(
            acting_user=acting_user,
            resource_type=RESOURCE_ROOM,
            resource_id=procedure.room_id,
            previous_status=prev,
            new_status=state.status,
            notes=f"Synced from procedure {procedure.id}",
        )


def room_utilisation_pct(room_id: int, *, on_date: date | None = None) -> float:
    target = on_date or date.today()
    day_start = datetime.combine(target, datetime.min.time())
    day_end = datetime.combine(target, datetime.max.time())
    slots = RoomScheduleSlot.query.filter_by(room_id=room_id, is_archived=False).filter(
        RoomScheduleSlot.start_at >= day_start,
        RoomScheduleSlot.end_at <= day_end,
    ).all()
    if not slots:
        return 0.0
    booked_minutes = sum((s.end_at - s.start_at).total_seconds() / 60 for s in slots)
    return round(min(booked_minutes / (8 * 60), 1.0) * 100, 1)
