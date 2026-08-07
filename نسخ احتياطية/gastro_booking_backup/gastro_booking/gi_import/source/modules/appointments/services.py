"""
Service layer for Appointment Core (Sprint 2A). Scheduling only -- no
procedure or clinical encounter data (that's the Procedure Engine, a
later sprint).

Permission codes ("appointment:view", "appointment:edit") are string
literals, not imported constants -- same reasoning as every other
service module: the set of roles/permissions is database data
(app/modules/rbac/), not Python.
"""

from datetime import datetime, timedelta, timezone

from app.core.exceptions import NotFoundError, ValidationError
from app.engines import audit_engine, permission_engine
from app.extensions import db
from app.modules.appointments.models import (
    CONFLICT_CHECK_STATUSES,
    STATUS_CANCELLED,
    STATUS_CHECKED_IN,
    STATUS_COMPLETED,
    STATUS_IN_PROGRESS,
    STATUS_NO_SHOW,
    STATUS_RESCHEDULED,
    STATUS_SCHEDULED,
    Appointment,
)
from app.modules.department.models import Department
from app.modules.patients.models import Patient

# Statuses that mean "this appointment is over" -- no further
# status-changing action (reschedule/check-in/start/complete/no-show)
# is allowed on it. Archive/restore are still allowed, same as any
# BaseModel record.
TERMINAL_STATUSES = {STATUS_CANCELLED, STATUS_COMPLETED, STATUS_NO_SHOW}


def _utcnow():
    return datetime.now(timezone.utc)


def _enforce_daily_limit(acting_user) -> None:
    """
    Blocks appointment CREATION once acting_user has already created
    daily_appointment_limit appointments today. NULL limit = unlimited.

    Deliberately computed on demand from appointments.created_at rather
    than a stored/decrementing counter column -- "resets" automatically
    at UTC midnight with no scheduled job needed, and self-corrects if
    the limit value itself changes mid-day. Only counts CREATION: this
    function is called from create_appointment() only, never from
    reschedule/check-in/complete/cancel/no-show, per the explicit
    requirement that only creation counts against the limit.
    """
    limit = getattr(acting_user, "daily_appointment_limit", None)
    if limit is None:
        return

    now = _utcnow()
    start_of_today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    start_of_tomorrow = start_of_today + timedelta(days=1)

    created_today = Appointment.query.filter(
        Appointment.created_by_id == acting_user.id,
        Appointment.created_at >= start_of_today,
        Appointment.created_at < start_of_tomorrow,
    ).count()

    if created_today >= limit:
        raise ValidationError(
            f"Daily appointment booking limit reached ({created_today}/{limit}). "
            "Try again tomorrow, or ask an administrator to raise your limit."
        )


def _raise_if_conflict(
    provider_id, scheduled_at, duration_minutes, exclude_appointment_id=None
) -> None:
    """
    Hard-enforced double-booking prevention: rejects a create/reschedule
    if it overlaps another active appointment for the same provider.
    Only applies when provider_id is set -- an unassigned appointment
    can't conflict with anything.

    Pre-filters candidates to the same UTC calendar day (a generous
    optimization -- appointments are not expected to cross midnight)
    then does the exact overlap comparison in Python. Deliberately not
    a database-level overlap constraint: that would need a Postgres-only
    exclusion constraint (btree_gist), breaking the "must remain fully
    SQLite-testable" convention the rest of this codebase follows.
    """
    if provider_id is None:
        return

    new_start = scheduled_at
    new_end = scheduled_at + timedelta(minutes=duration_minutes)

    day_start = scheduled_at.replace(hour=0, minute=0, second=0, microsecond=0)
    day_end = day_start + timedelta(days=1)

    candidates_query = Appointment.query.filter(
        Appointment.provider_id == provider_id,
        Appointment.is_archived == False,  # noqa: E712
        Appointment.status.in_(CONFLICT_CHECK_STATUSES),
        Appointment.scheduled_at >= day_start,
        Appointment.scheduled_at < day_end,
    )
    if exclude_appointment_id is not None:
        candidates_query = candidates_query.filter(Appointment.id != exclude_appointment_id)

    for existing in candidates_query.all():
        existing_start = existing.scheduled_at
        existing_end = existing_start + timedelta(minutes=existing.duration_minutes)
        if new_start < existing_end and existing_start < new_end:
            raise ValidationError(
                f"This provider already has an appointment from "
                f"{existing_start.isoformat()} to {existing_end.isoformat()} "
                "that overlaps this time slot."
            )


def _raise_if_terminal(appointment: Appointment) -> None:
    if appointment.status in TERMINAL_STATUSES:
        raise ValidationError(
            f"Appointment is already '{appointment.status}' -- no further status "
            "changes are allowed on it."
        )


def create_appointment(
    acting_user,
    patient_id: int,
    scheduled_at,
    provider_id: int = None,
    duration_minutes: int = None,
    reason: str = None,
    notes: str = None,
    department_id: int = None,
) -> Appointment:
    permission_engine.require(
        acting_user, "appointment:edit", audit_context={"target_type": "Appointment"}
    )

    if scheduled_at is None:
        raise ValidationError("Scheduled date/time is required.")

    patient = Patient.query.get(patient_id)
    if patient is None or patient.is_archived:
        raise ValidationError("Invalid or archived patient.")

    duration = duration_minutes or 30
    if duration <= 0:
        raise ValidationError("Duration must be a positive number of minutes.")

    resolved_department_id = department_id or getattr(acting_user, "department_id", None)
    department = Department.query.get(resolved_department_id)
    if department is None:
        raise ValidationError("Invalid department.")

    _enforce_daily_limit(acting_user)
    _raise_if_conflict(provider_id, scheduled_at, duration)

    appointment = Appointment(
        patient_id=patient.id,
        provider_id=provider_id,
        scheduled_at=scheduled_at,
        original_scheduled_at=scheduled_at,
        duration_minutes=duration,
        status=STATUS_SCHEDULED,
        reason=(reason or "").strip() or None,
        notes=(notes or "").strip() or None,
        department_id=department.id,
        created_by_id=getattr(acting_user, "id", None),
    )
    db.session.add(appointment)
    db.session.commit()

    audit_engine.log(
        action="appointment.created",
        user=acting_user,
        target_type="Appointment",
        target_id=appointment.id,
        details={
            "patient_id": patient.id,
            "provider_id": provider_id,
            "scheduled_at": scheduled_at.isoformat(),
        },
    )
    return appointment


def get_appointment(acting_user, appointment_id: int) -> Appointment:
    permission_engine.require(acting_user, "appointment:view")
    appointment = Appointment.query.get(appointment_id)
    if appointment is None:
        raise NotFoundError(f"No appointment with id {appointment_id}")
    return appointment


def search_appointments(
    acting_user,
    date_from=None,
    date_to=None,
    patient_id: int = None,
    provider_id: int = None,
    status: str = None,
    include_archived: bool = False,
):
    permission_engine.require(acting_user, "appointment:view")

    query = Appointment.query
    if not include_archived:
        query = query.filter_by(is_archived=False)
    if date_from is not None:
        query = query.filter(Appointment.scheduled_at >= date_from)
    if date_to is not None:
        query = query.filter(Appointment.scheduled_at <= date_to)
    if patient_id is not None:
        query = query.filter_by(patient_id=patient_id)
    if provider_id is not None:
        query = query.filter_by(provider_id=provider_id)
    if status is not None:
        query = query.filter_by(status=status)

    return query.order_by(Appointment.scheduled_at.asc()).all()


def reschedule_appointment(
    acting_user, target_appointment: Appointment, new_scheduled_at, reason: str = None,
    is_capacity_override: bool = False,
) -> Appointment:
    """
    Moves the appointment to a new time. original_scheduled_at is never
    touched (it's set once, at creation) -- new_scheduled_at becomes the
    new scheduled_at, and the OLD scheduled_at (before this call) is
    what gets recorded as "old" in the audit entry below. Together,
    original_scheduled_at (on the row) + every appointment.rescheduled
    audit entry (old -> new, each time) gives the full reschedule
    history without a second, parallel history table.
    """
    permission_engine.require(
        acting_user,
        "appointment:edit",
        audit_context={"target_type": "Appointment", "target_id": target_appointment.id},
    )
    _raise_if_terminal(target_appointment)

    if new_scheduled_at is None:
        raise ValidationError("New scheduled date/time is required.")

    _raise_if_conflict(
        target_appointment.provider_id,
        new_scheduled_at,
        target_appointment.duration_minutes,
        exclude_appointment_id=target_appointment.id,
    )

    from app.modules.appointments.booking_capacity import services as capacity_services

    capacity_services.validate_appointment_reschedule(
        acting_user,
        target_appointment,
        new_scheduled_at,
        is_capacity_override=is_capacity_override,
    )

    old_scheduled_at = target_appointment.scheduled_at
    target_appointment.scheduled_at = new_scheduled_at
    target_appointment.status = STATUS_RESCHEDULED
    target_appointment.is_capacity_override = bool(is_capacity_override)
    db.session.commit()

    audit_engine.log(
        action="appointment.rescheduled",
        user=acting_user,
        target_type="Appointment",
        target_id=target_appointment.id,
        details={
            "old_scheduled_at": old_scheduled_at.isoformat(),
            "new_scheduled_at": new_scheduled_at.isoformat(),
            "original_scheduled_at": target_appointment.original_scheduled_at.isoformat(),
            "reason": reason,
        },
    )
    return target_appointment


def _transition_status(acting_user, target_appointment: Appointment, new_status: str, action: str):
    permission_engine.require(
        acting_user,
        "appointment:edit",
        audit_context={"target_type": "Appointment", "target_id": target_appointment.id},
    )
    _raise_if_terminal(target_appointment)

    old_status = target_appointment.status
    target_appointment.status = new_status
    db.session.commit()

    audit_engine.log(
        action=action,
        user=acting_user,
        target_type="Appointment",
        target_id=target_appointment.id,
        details={"old_status": old_status, "new_status": new_status},
    )
    return target_appointment


def check_in_appointment(acting_user, target_appointment: Appointment) -> Appointment:
    return _transition_status(
        acting_user, target_appointment, STATUS_CHECKED_IN, "appointment.checked_in"
    )


def start_appointment(acting_user, target_appointment: Appointment) -> Appointment:
    return _transition_status(
        acting_user, target_appointment, STATUS_IN_PROGRESS, "appointment.started"
    )


def complete_appointment(acting_user, target_appointment: Appointment) -> Appointment:
    return _transition_status(
        acting_user, target_appointment, STATUS_COMPLETED, "appointment.completed"
    )


def cancel_appointment(
    acting_user, target_appointment: Appointment, reason: str = None
) -> Appointment:
    """Cancellation is a STATUS change, not an archive -- a cancelled
    appointment stays visible in schedules/reports (it's a real
    scheduling outcome), unlike archive() which is reserved for
    correcting an erroneous/duplicate booking (see module docstring)."""
    permission_engine.require(
        acting_user,
        "appointment:edit",
        audit_context={"target_type": "Appointment", "target_id": target_appointment.id},
    )
    _raise_if_terminal(target_appointment)

    old_status = target_appointment.status
    target_appointment.status = STATUS_CANCELLED
    db.session.commit()

    audit_engine.log(
        action="appointment.cancelled",
        user=acting_user,
        target_type="Appointment",
        target_id=target_appointment.id,
        details={"old_status": old_status, "reason": reason},
    )
    return target_appointment


def mark_no_show(acting_user, target_appointment: Appointment) -> Appointment:
    return _transition_status(
        acting_user, target_appointment, STATUS_NO_SHOW, "appointment.no_show"
    )


def archive_appointment(
    acting_user, target_appointment: Appointment, reason: str = None
) -> Appointment:
    """Reserved for correcting an erroneous/duplicate booking -- not for
    routine cancellation (use cancel_appointment() for that)."""
    permission_engine.require(
        acting_user,
        "appointment:edit",
        audit_context={"target_type": "Appointment", "target_id": target_appointment.id},
    )

    target_appointment.archive(by_user_id=getattr(acting_user, "id", None), reason=reason)
    db.session.commit()

    audit_engine.log(
        action="appointment.archived",
        user=acting_user,
        target_type="Appointment",
        target_id=target_appointment.id,
        details={"reason": reason},
    )
    return target_appointment


def restore_appointment(acting_user, target_appointment: Appointment) -> Appointment:
    permission_engine.require(
        acting_user,
        "appointment:edit",
        audit_context={"target_type": "Appointment", "target_id": target_appointment.id},
    )

    target_appointment.restore()
    db.session.commit()

    audit_engine.log(
        action="appointment.restored",
        user=acting_user,
        target_type="Appointment",
        target_id=target_appointment.id,
    )
    return target_appointment
