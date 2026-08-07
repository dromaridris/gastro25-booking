"""Clinical integration — read-only references to frozen modules."""

from __future__ import annotations

from datetime import date, datetime

from app.core.base_model import utcnow
from app.modules.appointments.models import Appointment
from app.modules.procedure_execution.models import OUTCOME_COMPLETED, ProcedureSession, RoomOccupancyPeriod
from app.modules.procedures.models import (
    STATUS_CANCELLED,
    STATUS_FINISHED,
    STATUS_IN_ROOM,
    Procedure,
)


def active_procedures_today(*, department_id: int = 1) -> list[Procedure]:
    today = date.today()
    return (
        Procedure.query.filter_by(is_archived=False)
        .join(Appointment)
        .filter(Appointment.scheduled_at >= datetime.combine(today, datetime.min.time()))
        .filter(Appointment.scheduled_at <= datetime.combine(today, datetime.max.time()))
        .filter(Procedure.status.notin_([STATUS_CANCELLED]))
        .all()
    )


def procedures_in_room(*, department_id: int = 1) -> list[Procedure]:
    return Procedure.query.filter_by(is_archived=False, status=STATUS_IN_ROOM).all()


def open_room_occupancy(room_id: int) -> RoomOccupancyPeriod | None:
    return (
        RoomOccupancyPeriod.query.filter_by(room_id=room_id)
        .filter(RoomOccupancyPeriod.occupied_until.is_(None))
        .order_by(RoomOccupancyPeriod.occupied_from.desc())
        .first()
    )


def today_procedure_count(*, department_id: int = 1) -> int:
    today = date.today()
    return (
        Procedure.query.filter_by(is_archived=False)
        .join(Appointment)
        .filter(Appointment.scheduled_at >= datetime.combine(today, datetime.min.time()))
        .filter(Appointment.scheduled_at <= datetime.combine(today, datetime.max.time()))
        .count()
    )


def completed_sessions_today(*, department_id: int = 1) -> int:
    today = date.today()
    start = datetime.combine(today, datetime.min.time())
    end = datetime.combine(today, datetime.max.time())
    return (
        ProcedureSession.query.filter_by(is_archived=False, outcome=OUTCOME_COMPLETED)
        .filter(ProcedureSession.procedure_finish_at >= start)
        .filter(ProcedureSession.procedure_finish_at <= end)
        .count()
    )


def sync_room_from_procedure(room_state, procedure: Procedure | None) -> None:
    """Update operational room state from live procedure workflow (read-only source)."""
    from app.modules.dept_ops.constants import ROOM_AVAILABLE, ROOM_OCCUPIED

    if procedure is None:
        if room_state.status == ROOM_OCCUPIED:
            room_state.current_procedure_id = None
            room_state.status = ROOM_AVAILABLE
        return
    if procedure.status == STATUS_IN_ROOM:
        room_state.current_procedure_id = procedure.id
        room_state.status = ROOM_OCCUPIED
    elif procedure.status in {STATUS_FINISHED, STATUS_CANCELLED}:
        room_state.current_procedure_id = None
        if room_state.status == ROOM_OCCUPIED:
            room_state.status = ROOM_AVAILABLE
