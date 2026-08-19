"""
Service layer for the Procedure Engine (Sprint 2B "Procedure Scheduling &
Endoscopy Workflow"). Booking and workflow only -- no findings, diagnosis,
recommendations, images, or report generation (that's the Report Engine,
a later sprint).

Permission codes are string literals, not imported constants -- same
reasoning as every other service module: the set of roles/permissions is
database data (app/modules/rbac/), not Python. Five permissions gate this
module (see app/modules/rbac/seed_data.py for the full rationale):

- procedure_catalogue:manage -- admin-tier: add/edit/archive/restore
  ProcedureType and EndoscopyRoom rows.
- procedure:view -- view procedures, the daily list, the waiting list.
- procedure:edit -- book/edit a procedure whose type does NOT have
  requires_special_authorization set: create, change type/priority,
  assign/reassign room or endoscopist.
- procedure:workflow -- move any procedure through the daily workflow
  (waiting/ready/in room/finished/cancelled) and assign/reassign its
  room. Deliberately broader than procedure:edit and NOT gated by
  requires_special_authorization -- explicit Sprint 2B decision that
  day-to-day endoscopy-unit workflow is nursing-driven.
- procedure:special_authorization -- required INSTEAD OF procedure:edit
  for any procedure whose type has requires_special_authorization=True:
  booking it, changing its type/priority, and deciding who performs it
  (assign/reassign endoscopist). This is a pure authorization-policy
  gate; WHICH procedure types require it is entirely a Procedure
  Catalogue decision (ProcedureType.requires_special_authorization,
  administrator-set per row -- never a clinical-complexity judgment made
  in this code). Explicit Sprint 2B decision: procedures the catalogue
  flags this way are booked, and their endoscopist decided, by Head of
  Department / Core Consultant only.
"""

from datetime import datetime, timedelta, timezone

from app.core.exceptions import NotFoundError, ValidationError
from app.engines import audit_engine, permission_engine
from app.extensions import db
from app.modules.appointments.models import Appointment
from app.modules.auth.models import User
from app.modules.procedures.models import (
    ALL_PRIORITIES,
    PRIORITY_ROUTINE,
    STATUS_BOOKED,
    STATUS_CANCELLED,
    STATUS_FINISHED,
    STATUS_IN_ROOM,
    STATUS_READY,
    STATUS_WAITING,
    TERMINAL_STATUSES,
    EndoscopyRoom,
    Procedure,
    ProcedureType,
    ALL_REPORT_TEMPLATE_KEYS,
    CATALOGUE_REPORT_TEMPLATE_KEYS,
)


def _utcnow():
    return datetime.now(timezone.utc)


def _department_id_for(acting_user, department_id=None):
    return department_id or getattr(acting_user, "department_id", None)


def _normalize_report_template_key(report_template_key: str = None):
    if report_template_key is None:
        return None
    key = (report_template_key or "").strip()
    if not key:
        return None
    if key not in CATALOGUE_REPORT_TEMPLATE_KEYS:
        raise ValidationError(f"Invalid report template key: '{key}'.")
    return key


# --- Procedure Catalogue (administrator-managed) ---


def list_procedure_types(acting_user, include_archived: bool = False):
    permission_engine.require(acting_user, "procedure:view")
    query = ProcedureType.query
    if not include_archived:
        query = query.filter_by(is_archived=False)
    return query.order_by(ProcedureType.name.asc()).all()


def get_procedure_type(acting_user, procedure_type_id: int) -> ProcedureType:
    permission_engine.require(acting_user, "procedure:view")
    procedure_type = ProcedureType.query.get(procedure_type_id)
    if procedure_type is None:
        raise NotFoundError(f"No procedure type with id {procedure_type_id}")
    return procedure_type


def create_procedure_type(
    acting_user,
    name: str,
    requires_special_authorization: bool = False,
    description: str = None,
    report_template_key: str = None,
    department_id: int = None,
) -> ProcedureType:
    permission_engine.require(
        acting_user, "procedure_catalogue:manage", audit_context={"target_type": "ProcedureType"}
    )

    name_clean = (name or "").strip()
    if not name_clean:
        raise ValidationError("Procedure type name is required.")
    if ProcedureType.query.filter_by(name=name_clean).first() is not None:
        raise ValidationError("A procedure type with this name already exists.")

    procedure_type = ProcedureType(
        name=name_clean,
        requires_special_authorization=bool(requires_special_authorization),
        report_template_key=_normalize_report_template_key(report_template_key),
        description=(description or "").strip() or None,
        department_id=_department_id_for(acting_user, department_id),
        created_by_id=getattr(acting_user, "id", None),
    )
    db.session.add(procedure_type)
    db.session.commit()

    audit_engine.log(
        action="procedure_type.created",
        user=acting_user,
        target_type="ProcedureType",
        target_id=procedure_type.id,
        details={
            "name": procedure_type.name,
            "requires_special_authorization": procedure_type.requires_special_authorization,
            "report_template_key": procedure_type.report_template_key,
        },
    )
    return procedure_type


def update_procedure_type(
    acting_user,
    target: ProcedureType,
    name: str,
    requires_special_authorization: bool,
    description: str = None,
    report_template_key: str = None,
) -> ProcedureType:
    permission_engine.require(
        acting_user,
        "procedure_catalogue:manage",
        audit_context={"target_type": "ProcedureType", "target_id": target.id},
    )

    name_clean = (name or "").strip()
    if not name_clean:
        raise ValidationError("Procedure type name is required.")
    existing = ProcedureType.query.filter_by(name=name_clean).first()
    if existing is not None and existing.id != target.id:
        raise ValidationError("A procedure type with this name already exists.")

    before = {
        "name": target.name,
        "requires_special_authorization": target.requires_special_authorization,
        "report_template_key": target.report_template_key,
    }
    target.name = name_clean
    target.requires_special_authorization = bool(requires_special_authorization)
    target.report_template_key = _normalize_report_template_key(report_template_key)
    target.description = (description or "").strip() or None
    db.session.commit()

    audit_engine.log(
        action="procedure_type.updated",
        user=acting_user,
        target_type="ProcedureType",
        target_id=target.id,
        details={
            "before": before,
            "after": {
                "name": target.name,
                "requires_special_authorization": target.requires_special_authorization,
                "report_template_key": target.report_template_key,
            },
        },
    )
    return target


def archive_procedure_type(acting_user, target: ProcedureType, reason: str = None) -> ProcedureType:
    permission_engine.require(
        acting_user,
        "procedure_catalogue:manage",
        audit_context={"target_type": "ProcedureType", "target_id": target.id},
    )
    target.archive(by_user_id=getattr(acting_user, "id", None), reason=reason)
    db.session.commit()

    audit_engine.log(
        action="procedure_type.archived",
        user=acting_user,
        target_type="ProcedureType",
        target_id=target.id,
        details={"reason": reason},
    )
    return target


def restore_procedure_type(acting_user, target: ProcedureType) -> ProcedureType:
    permission_engine.require(
        acting_user,
        "procedure_catalogue:manage",
        audit_context={"target_type": "ProcedureType", "target_id": target.id},
    )
    target.restore()
    db.session.commit()

    audit_engine.log(
        action="procedure_type.restored",
        user=acting_user,
        target_type="ProcedureType",
        target_id=target.id,
    )
    return target


# --- Endoscopy Rooms (administrator-managed) ---


def list_rooms(acting_user, include_archived: bool = False):
    permission_engine.require(acting_user, "procedure:view")
    query = EndoscopyRoom.query
    if not include_archived:
        query = query.filter_by(is_archived=False)
    return query.order_by(EndoscopyRoom.name.asc()).all()


def get_room(acting_user, room_id: int) -> EndoscopyRoom:
    permission_engine.require(acting_user, "procedure:view")
    room = EndoscopyRoom.query.get(room_id)
    if room is None:
        raise NotFoundError(f"No endoscopy room with id {room_id}")
    return room


def create_room(
    acting_user, name: str, description: str = None, department_id: int = None
) -> EndoscopyRoom:
    permission_engine.require(
        acting_user, "procedure_catalogue:manage", audit_context={"target_type": "EndoscopyRoom"}
    )

    name_clean = (name or "").strip()
    if not name_clean:
        raise ValidationError("Room name is required.")
    if EndoscopyRoom.query.filter_by(name=name_clean).first() is not None:
        raise ValidationError("A room with this name already exists.")

    room = EndoscopyRoom(
        name=name_clean,
        description=(description or "").strip() or None,
        department_id=_department_id_for(acting_user, department_id),
        created_by_id=getattr(acting_user, "id", None),
    )
    db.session.add(room)
    db.session.commit()

    audit_engine.log(
        action="endoscopy_room.created",
        user=acting_user,
        target_type="EndoscopyRoom",
        target_id=room.id,
        details={"name": room.name},
    )
    return room


def update_room(acting_user, target: EndoscopyRoom, name: str, description: str = None) -> EndoscopyRoom:
    permission_engine.require(
        acting_user,
        "procedure_catalogue:manage",
        audit_context={"target_type": "EndoscopyRoom", "target_id": target.id},
    )

    name_clean = (name or "").strip()
    if not name_clean:
        raise ValidationError("Room name is required.")
    existing = EndoscopyRoom.query.filter_by(name=name_clean).first()
    if existing is not None and existing.id != target.id:
        raise ValidationError("A room with this name already exists.")

    before_name = target.name
    target.name = name_clean
    target.description = (description or "").strip() or None
    db.session.commit()

    audit_engine.log(
        action="endoscopy_room.updated",
        user=acting_user,
        target_type="EndoscopyRoom",
        target_id=target.id,
        details={"old_name": before_name, "new_name": target.name},
    )
    return target


def archive_room(acting_user, target: EndoscopyRoom, reason: str = None) -> EndoscopyRoom:
    permission_engine.require(
        acting_user,
        "procedure_catalogue:manage",
        audit_context={"target_type": "EndoscopyRoom", "target_id": target.id},
    )
    target.archive(by_user_id=getattr(acting_user, "id", None), reason=reason)
    db.session.commit()

    audit_engine.log(
        action="endoscopy_room.archived",
        user=acting_user,
        target_type="EndoscopyRoom",
        target_id=target.id,
        details={"reason": reason},
    )
    return target


def restore_room(acting_user, target: EndoscopyRoom) -> EndoscopyRoom:
    permission_engine.require(
        acting_user,
        "procedure_catalogue:manage",
        audit_context={"target_type": "EndoscopyRoom", "target_id": target.id},
    )
    target.restore()
    db.session.commit()

    audit_engine.log(
        action="endoscopy_room.restored",
        user=acting_user,
        target_type="EndoscopyRoom",
        target_id=target.id,
    )
    return target


# --- Procedure booking & workflow ---


def _require_booking_permission(acting_user, procedure_type: ProcedureType, target_id=None):
    """
    The core RBAC branch for this module: a procedure type the catalogue
    flags requires_special_authorization requires
    procedure:special_authorization; anything else only requires
    procedure:edit. This is a pure authorization-policy branch -- WHICH
    types require it is entirely the Procedure Catalogue's decision (see
    ProcedureType.requires_special_authorization), not a judgment made
    here. See module docstring for the product decision behind this
    split.
    """
    permission = (
        "procedure:special_authorization"
        if procedure_type.requires_special_authorization
        else "procedure:edit"
    )
    audit_context = {"target_type": "Procedure"}
    if target_id is not None:
        audit_context["target_id"] = target_id
    permission_engine.require(acting_user, permission, audit_context=audit_context)


def _resolve_appointment(appointment_id: int) -> Appointment:
    appointment = Appointment.query.get(appointment_id)
    if appointment is None or appointment.is_archived:
        raise ValidationError("Invalid or archived appointment.")
    return appointment


def _resolve_procedure_type(procedure_type_id: int) -> ProcedureType:
    procedure_type = ProcedureType.query.get(procedure_type_id)
    if procedure_type is None or procedure_type.is_archived:
        raise ValidationError("Invalid or archived procedure type.")
    return procedure_type


def _resolve_room(room_id):
    if room_id is None:
        return None
    room = EndoscopyRoom.query.get(room_id)
    if room is None or room.is_archived:
        raise ValidationError("Invalid or archived endoscopy room.")
    return room


def _resolve_endoscopist(endoscopist_id):
    """
    Endoscopist eligibility reuses the SAME User.is_provider flag Sprint
    2A introduced for appointment providers -- explicit decision, see
    app/modules/procedures/models.py's Procedure.endoscopist_id docstring
    for why this isn't a second, separate flag.
    """
    if endoscopist_id is None:
        return None
    user = User.query.get(endoscopist_id)
    if (
        user is None
        or user.is_archived
        or not user.is_active_account
        or not user.is_provider
    ):
        raise ValidationError("Invalid endoscopist: must be an active, provider-flagged user.")
    return user


def _resolve_priority(priority):
    value = priority or PRIORITY_ROUTINE
    if value not in ALL_PRIORITIES:
        raise ValidationError(f"Invalid priority: {value}")
    return value


def _raise_if_terminal(procedure: Procedure) -> None:
    if procedure.status in TERMINAL_STATUSES:
        raise ValidationError(
            f"Procedure is already '{procedure.status}' -- no further workflow "
            "changes are allowed on it."
        )


def create_procedure(
    acting_user,
    appointment_id: int,
    procedure_type_id: int,
    room_id: int = None,
    endoscopist_id: int = None,
    priority: str = None,
    notes: str = None,
    department_id: int = None,
    is_capacity_override: bool = False,
) -> Procedure:
    appointment = _resolve_appointment(appointment_id)
    procedure_type = _resolve_procedure_type(procedure_type_id)
    _require_booking_permission(acting_user, procedure_type)

    from app.modules.appointments.booking_capacity import services as capacity_services

    capacity_services.validate_endoscopy_booking(
        acting_user,
        appointment.scheduled_at,
        procedure_type=procedure_type,
        is_capacity_override=is_capacity_override,
    )

    room = _resolve_room(room_id)
    endoscopist = _resolve_endoscopist(endoscopist_id)
    resolved_priority = _resolve_priority(priority)

    procedure = Procedure(
        appointment_id=appointment.id,
        procedure_type_id=procedure_type.id,
        room_id=room.id if room else None,
        endoscopist_id=endoscopist.id if endoscopist else None,
        priority=resolved_priority,
        status=STATUS_BOOKED,
        notes=(notes or "").strip() or None,
        department_id=_department_id_for(acting_user, department_id),
        created_by_id=getattr(acting_user, "id", None),
        is_capacity_override=bool(is_capacity_override),
    )
    db.session.add(procedure)
    db.session.commit()

    audit_engine.log(
        action="procedure.created",
        user=acting_user,
        target_type="Procedure",
        target_id=procedure.id,
        details={
            "appointment_id": appointment.id,
            "procedure_type_id": procedure_type.id,
            "requires_special_authorization": procedure_type.requires_special_authorization,
            "room_id": procedure.room_id,
            "endoscopist_id": procedure.endoscopist_id,
            "priority": procedure.priority,
        },
    )
    return procedure


def get_procedure(acting_user, procedure_id: int) -> Procedure:
    permission_engine.require(acting_user, "procedure:view")
    procedure = Procedure.query.get(procedure_id)
    if procedure is None:
        raise NotFoundError(f"No procedure with id {procedure_id}")
    return procedure


def search_procedures(
    acting_user,
    date_from=None,
    date_to=None,
    room_id: int = None,
    procedure_type_id: int = None,
    endoscopist_id: int = None,
    status: str = None,
    priority: str = None,
    include_archived: bool = False,
):
    """
    Backs the Daily Endoscopy List (feature 6) and the Waiting List
    (feature 7) -- both are just filtered views over the same query.
    Filtering is done by joining Appointment for scheduled_at, since
    Procedure deliberately doesn't duplicate that column (see
    Procedure.patient's docstring). A NULL endoscopist_id is never
    implicitly excluded -- unassigned procedures appear normally, per
    explicit requirement, unless the caller passes endoscopist_id itself.
    """
    permission_engine.require(acting_user, "procedure:view")

    query = Procedure.query.join(Appointment, Procedure.appointment_id == Appointment.id)
    if not include_archived:
        query = query.filter(Procedure.is_archived == False)  # noqa: E712
    if date_from is not None:
        query = query.filter(Appointment.scheduled_at >= date_from)
    if date_to is not None:
        query = query.filter(Appointment.scheduled_at <= date_to)
    if room_id is not None:
        query = query.filter(Procedure.room_id == room_id)
    if procedure_type_id is not None:
        query = query.filter(Procedure.procedure_type_id == procedure_type_id)
    if endoscopist_id is not None:
        query = query.filter(Procedure.endoscopist_id == endoscopist_id)
    if status is not None:
        query = query.filter(Procedure.status == status)
    if priority is not None:
        query = query.filter(Procedure.priority == priority)

    return query.order_by(Appointment.scheduled_at.asc()).all()


def daily_list(
    acting_user,
    on_date,
    room_id: int = None,
    procedure_type_id: int = None,
    endoscopist_id: int = None,
    status: str = None,
    priority: str = None,
):
    """The printable daily list (feature 6): every procedure whose
    appointment falls on `on_date` (a date object), narrowed by the same
    filters search_procedures supports."""
    day_start = datetime.combine(on_date, datetime.min.time())
    day_end = day_start + timedelta(days=1)
    return search_procedures(
        acting_user,
        date_from=day_start,
        date_to=day_end - timedelta(microseconds=1),
        room_id=room_id,
        procedure_type_id=procedure_type_id,
        endoscopist_id=endoscopist_id,
        status=status,
        priority=priority,
    )


def waiting_list(acting_user):
    """The Waiting List view (feature 7): every non-archived procedure
    currently sitting in STATUS_WAITING."""
    return search_procedures(acting_user, status=STATUS_WAITING)


def assign_endoscopist(acting_user, target: Procedure, endoscopist_id) -> Procedure:
    """
    Sets, changes, or clears (endoscopist_id=None) who performs this
    procedure. Always audit logged, per explicit requirement that every
    assignment AND reassignment is logged. Gated the same way booking is
    -- procedure:special_authorization when the procedure type requires
    it, procedure:edit otherwise -- since deciding who performs such a
    procedure is explicitly reserved for Head of Department / Core
    Consultant (see module docstring).
    """
    _require_booking_permission(acting_user, target.procedure_type, target_id=target.id)
    _raise_if_terminal(target)

    endoscopist = _resolve_endoscopist(endoscopist_id)
    old_endoscopist_id = target.endoscopist_id
    target.endoscopist_id = endoscopist.id if endoscopist else None
    db.session.commit()

    audit_engine.log(
        action="procedure.endoscopist_assigned",
        user=acting_user,
        target_type="Procedure",
        target_id=target.id,
        details={"old_endoscopist_id": old_endoscopist_id, "new_endoscopist_id": target.endoscopist_id},
    )
    return target


def assign_room(acting_user, target: Procedure, room_id) -> Procedure:
    """Room assignment is workflow, not booking authority -- gated by
    procedure:workflow regardless of whether the procedure type requires
    special authorization (see module docstring)."""
    permission_engine.require(
        acting_user,
        "procedure:workflow",
        audit_context={"target_type": "Procedure", "target_id": target.id},
    )
    _raise_if_terminal(target)

    room = _resolve_room(room_id)
    old_room_id = target.room_id
    target.room_id = room.id if room else None
    db.session.commit()

    audit_engine.log(
        action="procedure.room_assigned",
        user=acting_user,
        target_type="Procedure",
        target_id=target.id,
        details={"old_room_id": old_room_id, "new_room_id": target.room_id},
    )
    from app.modules.dept_ops.events import on_room_assigned

    on_room_assigned(target, acting_user)
    return target


def change_procedure_type(acting_user, target: Procedure, new_procedure_type_id: int) -> Procedure:
    """
    Requires booking-tier permission for BOTH the old and the new
    procedure type -- changing a booking to a type that requires special
    authorization (or vice versa) must not be a way to route around that
    restriction in either direction.
    """
    new_type = _resolve_procedure_type(new_procedure_type_id)
    _require_booking_permission(acting_user, target.procedure_type, target_id=target.id)
    _require_booking_permission(acting_user, new_type, target_id=target.id)
    _raise_if_terminal(target)

    old_type_id = target.procedure_type_id
    target.procedure_type_id = new_type.id
    db.session.commit()

    audit_engine.log(
        action="procedure.type_changed",
        user=acting_user,
        target_type="Procedure",
        target_id=target.id,
        details={"old_procedure_type_id": old_type_id, "new_procedure_type_id": new_type.id},
    )
    return target


def set_priority(acting_user, target: Procedure, priority: str) -> Procedure:
    _require_booking_permission(acting_user, target.procedure_type, target_id=target.id)
    _raise_if_terminal(target)

    resolved_priority = _resolve_priority(priority)
    old_priority = target.priority
    target.priority = resolved_priority
    db.session.commit()

    audit_engine.log(
        action="procedure.priority_changed",
        user=acting_user,
        target_type="Procedure",
        target_id=target.id,
        details={"old_priority": old_priority, "new_priority": target.priority},
    )
    return target


def _transition_status(acting_user, target: Procedure, new_status: str, action: str) -> Procedure:
    permission_engine.require(
        acting_user,
        "procedure:workflow",
        audit_context={"target_type": "Procedure", "target_id": target.id},
    )
    _raise_if_terminal(target)

    old_status = target.status
    target.status = new_status
    db.session.commit()

    audit_engine.log(
        action=action,
        user=acting_user,
        target_type="Procedure",
        target_id=target.id,
        details={"old_status": old_status, "new_status": new_status},
    )
    from app.modules.dept_ops.events import on_procedure_status_changed

    on_procedure_status_changed(target, acting_user)
    return target


def move_to_waiting_list(acting_user, target: Procedure, reason: str = None) -> Procedure:
    """Sprint 2B feature 7: if no slot (room/endoscopist/time) is
    available, the procedure moves to the waiting list instead of staying
    booked against a slot that doesn't exist."""
    permission_engine.require(
        acting_user,
        "procedure:workflow",
        audit_context={"target_type": "Procedure", "target_id": target.id},
    )
    _raise_if_terminal(target)

    old_status = target.status
    target.status = STATUS_WAITING
    db.session.commit()

    audit_engine.log(
        action="procedure.waitlisted",
        user=acting_user,
        target_type="Procedure",
        target_id=target.id,
        details={"old_status": old_status, "reason": reason},
    )
    return target


def mark_ready(acting_user, target: Procedure) -> Procedure:
    return _transition_status(acting_user, target, STATUS_READY, "procedure.marked_ready")


def mark_in_room(acting_user, target: Procedure) -> Procedure:
    return _transition_status(acting_user, target, STATUS_IN_ROOM, "procedure.marked_in_room")


def mark_finished(acting_user, target: Procedure) -> Procedure:
    return _transition_status(acting_user, target, STATUS_FINISHED, "procedure.finished")


def cancel_procedure(acting_user, target: Procedure, reason: str = None) -> Procedure:
    permission_engine.require(
        acting_user,
        "procedure:workflow",
        audit_context={"target_type": "Procedure", "target_id": target.id},
    )
    _raise_if_terminal(target)

    old_status = target.status
    target.status = STATUS_CANCELLED
    db.session.commit()

    audit_engine.log(
        action="procedure.cancelled",
        user=acting_user,
        target_type="Procedure",
        target_id=target.id,
        details={"old_status": old_status, "reason": reason},
    )
    return target


def archive_procedure(acting_user, target: Procedure, reason: str = None) -> Procedure:
    """Reserved for correcting an erroneous/duplicate booking -- not for
    routine cancellation (use cancel_procedure() for that). Same
    convention as Appointment/Patient archive."""
    _require_booking_permission(acting_user, target.procedure_type, target_id=target.id)

    target.archive(by_user_id=getattr(acting_user, "id", None), reason=reason)
    db.session.commit()

    audit_engine.log(
        action="procedure.archived",
        user=acting_user,
        target_type="Procedure",
        target_id=target.id,
        details={"reason": reason},
    )
    return target


def restore_procedure(acting_user, target: Procedure) -> Procedure:
    _require_booking_permission(acting_user, target.procedure_type, target_id=target.id)

    target.restore()
    db.session.commit()

    audit_engine.log(
        action="procedure.restored",
        user=acting_user,
        target_type="Procedure",
        target_id=target.id,
    )
    return target
