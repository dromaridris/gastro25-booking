"""
Endoscopy booking capacity validation — applies to procedure scheduling and
appointment rescheduling only, not general inpatient workflow.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from app.core.exceptions import ValidationError
from app.engines import permission_engine
from app.extensions import db
from app.modules.appointments.booking_capacity.constants import (
    CAPACITY_COLONOSCOPY,
    CAPACITY_ERCP,
    CAPACITY_NONE,
    CAPACITY_PEG,
    CAPACITY_SPECIAL,
    CAPACITY_UPPER_GI,
    ERCOP_ALLOWED_WEEKDAYS,
    SCHEDULER_ROLE_CODES,
)
from app.modules.appointments.booking_capacity.models import BookingCapacitySettings, BookingHoliday
from app.modules.appointments.models import STATUS_CANCELLED, Appointment
from app.modules.procedures.models import STATUS_CANCELLED as PROCEDURE_CANCELLED, Procedure, ProcedureType

# Fixed public holidays (month, day) — same calendar every year.
FIXED_HOLIDAYS = (
    (1, 1),
    (5, 1),
    (9, 11),
    (12, 2),
    (12, 16),
    (12, 18),
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _role_code(acting_user) -> str | None:
    role = getattr(acting_user, "role", None)
    return getattr(role, "code", None)


def get_capacity_settings() -> BookingCapacitySettings:
    settings = BookingCapacitySettings.query.get(1)
    if settings is None:
        settings = BookingCapacitySettings(id=1)
        db.session.add(settings)
        db.session.commit()
    return settings


def _daily_cap(settings: BookingCapacitySettings, category: str) -> int | None:
    if category == CAPACITY_UPPER_GI:
        return settings.upper_gi_daily_cap
    if category == CAPACITY_COLONOSCOPY:
        return settings.colonoscopy_daily_cap
    if category == CAPACITY_PEG:
        return settings.peg_daily_cap
    if category in (CAPACITY_ERCP, CAPACITY_SPECIAL):
        return None
    return None


def _resolve_capacity_category(procedure_type: ProcedureType | None, explicit: str | None = None) -> str:
    if explicit:
        return explicit
    if procedure_type is None:
        return CAPACITY_NONE
    category = getattr(procedure_type, "capacity_category", None)
    if category:
        return category
    name = (procedure_type.name or "").lower()
    if "peg" in name:
        return CAPACITY_PEG
    if "ercp" in name:
        return CAPACITY_ERCP
    if "colon" in name or "sigmoid" in name:
        return CAPACITY_COLONOSCOPY
    if "upper gi" in name or "gastroscopy" in name or "oesophago" in name:
        return CAPACITY_UPPER_GI
    if procedure_type.requires_special_authorization:
        return CAPACITY_SPECIAL
    return CAPACITY_NONE


def _is_holiday(target_date: date) -> bool:
    if (target_date.month, target_date.day) in FIXED_HOLIDAYS:
        return True
    return (
        BookingHoliday.query.filter_by(holiday_date=target_date, is_archived=False).first()
        is not None
    )


def _count_bookings_for_day(
    target_date: date,
    category: str,
    *,
    created_by_id: int | None = None,
    exclude_procedure_id: int | None = None,
) -> int:
    day_start = datetime.combine(target_date, datetime.min.time()).replace(tzinfo=timezone.utc)
    day_end = day_start + timedelta(days=1)

    query = (
        db.session.query(Procedure)
        .join(Appointment, Procedure.appointment_id == Appointment.id)
        .join(ProcedureType, Procedure.procedure_type_id == ProcedureType.id)
        .filter(
            Procedure.is_archived.is_(False),
            Procedure.status != PROCEDURE_CANCELLED,
            Appointment.is_archived.is_(False),
            Appointment.status != STATUS_CANCELLED,
            Appointment.scheduled_at >= day_start,
            Appointment.scheduled_at < day_end,
        )
    )
    if created_by_id is not None:
        query = query.filter(Procedure.created_by_id == created_by_id)
    if exclude_procedure_id is not None:
        query = query.filter(Procedure.id != exclude_procedure_id)

    count = 0
    for procedure in query.all():
        proc_category = _resolve_capacity_category(procedure.procedure_type)
        if proc_category == category:
            count += 1
    return count


def validate_endoscopy_booking(
    acting_user,
    scheduled_at: datetime,
    *,
    procedure_type: ProcedureType | None = None,
    capacity_category: str | None = None,
    is_capacity_override: bool = False,
    exclude_procedure_id: int | None = None,
) -> None:
    """
    Enforce department endoscopy booking rules. Call before creating or
    rescheduling a procedure-linked slot (or when moving an appointment
    that already has a booked procedure).
    """
    if scheduled_at is None:
        raise ValidationError("Scheduled date/time is required.")

    category = _resolve_capacity_category(procedure_type, capacity_category)
    if category == CAPACITY_NONE:
        return

    if is_capacity_override:
        if permission_engine.check(acting_user, "appointment:override"):
            return
        raise ValidationError(
            "Capacity override requires Head of Department or Consultant authorization."
        )

    settings = get_capacity_settings()
    target_date = scheduled_at.date()
    role_code = _role_code(acting_user)

    if settings.sunday_blocked and target_date.weekday() == 6:
        raise ValidationError(
            "Endoscopy bookings are not scheduled on Sundays. "
            "A consultant or Head of Department can override if clinically necessary."
        )

    if _is_holiday(target_date):
        raise ValidationError(
            "Endoscopy bookings are blocked on public holidays. "
            "Use capacity override with consultant or Head of Department approval."
        )

    if category == CAPACITY_ERCP and settings.ercp_weekdays_only:
        if target_date.weekday() not in ERCOP_ALLOWED_WEEKDAYS:
            raise ValidationError(
                "ERCP is scheduled on Tuesdays and Saturdays only. "
                "Use capacity override for exceptional cases."
            )

    if role_code in SCHEDULER_ROLE_CODES and settings.time_lock_hours:
        earliest = _utcnow() + timedelta(hours=settings.time_lock_hours)
        if scheduled_at < earliest:
            raise ValidationError(
                f"Reception can only book slots at least {settings.time_lock_hours} hours ahead. "
                "Ask the on-call senior registrar or consultant for nearer dates."
            )

    daily_cap = _daily_cap(settings, category)
    if daily_cap is not None:
        department_count = _count_bookings_for_day(
            target_date, category, exclude_procedure_id=exclude_procedure_id
        )
        if department_count >= daily_cap:
            raise ValidationError(
                f"Daily limit reached for {category.replace('_', ' ')} "
                f"({department_count}/{daily_cap} on {target_date.isoformat()}). "
                "Consultant or Head of Department override required."
            )

        if role_code in SCHEDULER_ROLE_CODES and settings.scheduler_sub_quota_percent:
            scheduler_cap = max(1, int(daily_cap * settings.scheduler_sub_quota_percent / 100))
            scheduler_count = _count_bookings_for_day(
                target_date,
                category,
                created_by_id=getattr(acting_user, "id", None),
                exclude_procedure_id=exclude_procedure_id,
            )
            if scheduler_count >= scheduler_cap:
                raise ValidationError(
                    f"Reception sub-quota reached for {category.replace('_', ' ')} "
                    f"({scheduler_count}/{scheduler_cap} on {target_date.isoformat()}). "
                    "On-call doctors can book outside this sub-quota."
                )


def validate_appointment_reschedule(
    acting_user,
    appointment: Appointment,
    new_scheduled_at: datetime,
    *,
    is_capacity_override: bool = False,
) -> None:
    """Re-check capacity when moving an appointment that has active procedures."""
    active_procedures = (
        Procedure.query.filter_by(appointment_id=appointment.id, is_archived=False)
        .filter(Procedure.status != PROCEDURE_CANCELLED)
        .all()
    )
    for procedure in active_procedures:
        validate_endoscopy_booking(
            acting_user,
            new_scheduled_at,
            procedure_type=procedure.procedure_type,
            is_capacity_override=is_capacity_override,
            exclude_procedure_id=procedure.id,
        )


def update_capacity_settings(acting_user, **fields) -> BookingCapacitySettings:
    permission_engine.require(acting_user, "appointment:capacity_manage")
    settings = get_capacity_settings()
    allowed = {
        "upper_gi_daily_cap",
        "colonoscopy_daily_cap",
        "peg_daily_cap",
        "scheduler_sub_quota_percent",
        "sunday_blocked",
        "time_lock_hours",
        "ercp_weekdays_only",
    }
    for key, value in fields.items():
        if key in allowed and value is not None:
            setattr(settings, key, value)
    db.session.commit()
    return settings


def add_holiday(acting_user, holiday_date: date, label: str | None = None) -> BookingHoliday:
    permission_engine.require(acting_user, "appointment:capacity_manage")
    existing = BookingHoliday.query.filter_by(holiday_date=holiday_date, is_archived=False).first()
    if existing:
        raise ValidationError("That date is already marked as a booking holiday.")
    row = BookingHoliday(holiday_date=holiday_date, label=(label or "").strip() or None)
    db.session.add(row)
    db.session.commit()
    return row


def remove_holiday(acting_user, holiday_id: int) -> None:
    permission_engine.require(acting_user, "appointment:capacity_manage")
    row = BookingHoliday.query.get(holiday_id)
    if row is None or row.is_archived:
        raise ValidationError("Holiday not found.")
    row.archive(getattr(acting_user, "id", None))
    db.session.commit()
