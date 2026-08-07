"""Workforce ↔ Department Operations synchronisation — Sprint 7C."""

from __future__ import annotations

from datetime import date

from app.extensions import db
from app.modules.dept_ops.models import DutyRosterEntry, RoomStaffAssignment
from app.modules.dept_ops.roster_services import staff_on_duty


def is_user_on_leave(user_id: int, on_date: date | None = None) -> bool:
    target = on_date or date.today()
    return (
        DutyRosterEntry.query.filter_by(
            user_id=user_id, roster_date=target, is_leave=True, is_archived=False
        ).first()
        is not None
    )


def available_staff(acting_user, on_date: date | None = None) -> list[DutyRosterEntry]:
    """Staff on duty excluding approved leave."""
    return staff_on_duty(acting_user, roster_date=on_date)


def on_procedure_team_updated(session, acting_user) -> None:
    """Sync portfolio and room staff when procedure team changes."""
    from app.modules.workforce.portfolio_engine import sync_procedure_session_by_id

    sync_procedure_session_by_id(session.id)
    procedure = session.procedure
    if procedure and procedure.room_id:
        _sync_session_team_to_room(session, acting_user)
    db.session.commit()


def _sync_session_team_to_room(session, acting_user) -> None:
    """Mirror execution team onto room staff assignments for today."""
    from app.modules.dept_ops.room_services import assign_room_staff

    procedure = session.procedure
    if not procedure or not procedure.room_id:
        return
    today = date.today()
    team = [
        (session.endoscopist_id, "endoscopist"),
        (session.assistant_id, "assistant"),
        (session.nurse_id, "nurse"),
        (session.technician_id, "technician"),
        (session.anaesthetist_id, "anaesthetist"),
    ]
    for user_id, role in team:
        if user_id is None or is_user_on_leave(user_id, today):
            continue
        exists = RoomStaffAssignment.query.filter_by(
            room_id=procedure.room_id,
            user_id=user_id,
            assignment_date=today,
            role_label=role,
            is_archived=False,
        ).first()
        if exists:
            continue
        assign_room_staff(acting_user, procedure.room_id, user_id, today, role_label=role)


def department_attendance_summary(acting_user) -> dict:
    """Attendance summary for staff on duty today."""
    from app.modules.workforce.attendance_engine import attendance_score

    on_duty = available_staff(acting_user)
    rows = []
    for entry in on_duty:
        score = attendance_score(entry.user_id)
        rows.append(
            {
                "user_id": entry.user_id,
                "shift_type": entry.shift_type,
                "attendance_pct": score["attendance_pct"],
                "present_days": score["present_days"],
            }
        )
    avg = round(sum(r["attendance_pct"] for r in rows) / len(rows), 1) if rows else 0.0
    return {"staff": rows, "average_attendance_pct": avg, "on_duty_count": len(rows)}
