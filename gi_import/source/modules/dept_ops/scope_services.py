"""Endoscope management — Sprint 7C."""

from __future__ import annotations

from datetime import datetime

from app.core.base_model import utcnow
from app.core.exceptions import NotFoundError, ValidationError
from app.extensions import db
from app.engines import audit_engine, permission_engine
from app.modules.dept_ops.audit_helper import log_status_change
from app.modules.dept_ops.constants import (
    ALL_SCOPE_STATUSES,
    ALL_SCOPE_TYPES,
    MAINTENANCE_REPAIR,
    MAINTENANCE_SERVICE,
    RESOURCE_SCOPE,
    SCOPE_AVAILABLE,
    SCOPE_AWAITING_CLEANING,
    SCOPE_IN_PROCEDURE,
    SCOPE_READY,
)
from app.modules.dept_ops.models import Endoscope, ScopeMaintenanceRecord


def _require(user, permission: str) -> None:
    permission_engine.require(user, permission)


def list_scopes(acting_user) -> list[Endoscope]:
    _require(acting_user, "dept_ops:view")
    return Endoscope.query.filter_by(is_archived=False).order_by(Endoscope.scope_code.asc()).all()


def get_scope(acting_user, scope_id: int) -> Endoscope:
    _require(acting_user, "dept_ops:view")
    scope = Endoscope.query.filter_by(id=scope_id, is_archived=False).first()
    if scope is None:
        raise NotFoundError("Endoscope not found.")
    return scope


def create_scope(
    acting_user,
    *,
    scope_code: str,
    scope_type: str,
    serial_number: str | None = None,
    model: str | None = None,
    manufacturer: str | None = None,
    purchase_date=None,
) -> Endoscope:
    _require(acting_user, "dept_ops:scope_manage")
    if scope_type not in ALL_SCOPE_TYPES:
        raise ValidationError(f"Invalid scope type '{scope_type}'.")
    code = scope_code.strip()
    if Endoscope.query.filter_by(scope_code=code).first():
        raise ValidationError(f"Scope code '{code}' already exists.")
    scope = Endoscope(
        scope_code=code,
        scope_type=scope_type,
        serial_number=serial_number,
        model=model,
        manufacturer=manufacturer,
        purchase_date=purchase_date,
        status=SCOPE_AVAILABLE,
        department_id=getattr(acting_user, "department_id", 1) or 1,
        created_by_id=acting_user.id,
    )
    db.session.add(scope)
    db.session.flush()
    audit_engine.log("dept_ops.scope_created", user=acting_user, target_type="endoscope", target_id=scope.id)
    db.session.commit()
    return scope


def update_scope_status(
    acting_user,
    scope: Endoscope,
    status: str,
    *,
    location: str | None = None,
    assigned_room_id: int | None = None,
    assigned_procedure_id: int | None = None,
    assigned_technician_id: int | None = None,
    notes: str | None = None,
) -> Endoscope:
    _require(acting_user, "dept_ops:scope_manage")
    if status not in ALL_SCOPE_STATUSES:
        raise ValidationError(f"Invalid scope status '{status}'.")
    prev = scope.status
    scope.status = status
    if location is not None:
        scope.current_location = location
    if assigned_room_id is not None:
        scope.assigned_room_id = assigned_room_id
    if assigned_procedure_id is not None:
        scope.assigned_procedure_id = assigned_procedure_id
    if assigned_technician_id is not None:
        scope.assigned_technician_id = assigned_technician_id
    log_status_change(
        acting_user=acting_user,
        resource_type=RESOURCE_SCOPE,
        resource_id=scope.id,
        previous_status=prev,
        new_status=status,
        notes=notes,
    )
    db.session.commit()
    return scope


def assign_scope_to_procedure(
    acting_user, scope: Endoscope, procedure_id: int, room_id: int | None = None, technician_id: int | None = None
) -> Endoscope:
    return update_scope_status(
        acting_user,
        scope,
        SCOPE_IN_PROCEDURE,
        assigned_procedure_id=procedure_id,
        assigned_room_id=room_id,
        assigned_technician_id=technician_id,
    )


def release_scope_after_procedure(acting_user, scope: Endoscope) -> Endoscope:
    return update_scope_status(
        acting_user,
        scope,
        SCOPE_AWAITING_CLEANING,
        assigned_procedure_id=None,
        notes="Procedure finished — awaiting reprocessing",
    )


def record_maintenance(
    acting_user,
    scope: Endoscope,
    record_type: str,
    *,
    performed_at: datetime | None = None,
    notes: str | None = None,
    next_due_at: datetime | None = None,
) -> ScopeMaintenanceRecord:
    _require(acting_user, "dept_ops:scope_manage")
    if record_type not in {MAINTENANCE_SERVICE, MAINTENANCE_REPAIR}:
        raise ValidationError("Record type must be 'service' or 'repair'.")
    when = performed_at or utcnow()
    record = ScopeMaintenanceRecord(
        scope_id=scope.id,
        record_type=record_type,
        performed_at=when,
        performed_by_id=acting_user.id,
        notes=notes,
        next_due_at=next_due_at,
        department_id=getattr(acting_user, "department_id", 1) or 1,
        created_by_id=acting_user.id,
    )
    scope.last_maintenance_at = when
    if next_due_at:
        scope.next_maintenance_at = next_due_at
    db.session.add(record)
    audit_engine.log(
        "dept_ops.scope_maintenance",
        user=acting_user,
        target_type="endoscope",
        target_id=scope.id,
        details={"type": record_type},
    )
    db.session.commit()
    return record


def scopes_needing_maintenance(acting_user) -> list[Endoscope]:
    _require(acting_user, "dept_ops:view")
    now = utcnow()
    return (
        Endoscope.query.filter_by(is_archived=False)
        .filter(Endoscope.next_maintenance_at.isnot(None))
        .filter(Endoscope.next_maintenance_at <= now)
        .all()
    )


def scopes_by_status(acting_user, status: str) -> list[Endoscope]:
    _require(acting_user, "dept_ops:view")
    return Endoscope.query.filter_by(is_archived=False, status=status).all()


def get_scope_detail(acting_user, scope_id: int) -> dict:
    scope = get_scope(acting_user, scope_id)
    from app.modules.dept_ops.models import ScopeMaintenanceRecord, ScopeReprocessingCycle

    maintenance = (
        ScopeMaintenanceRecord.query.filter_by(scope_id=scope.id, is_archived=False)
        .order_by(ScopeMaintenanceRecord.performed_at.desc())
        .all()
    )
    cycles = (
        ScopeReprocessingCycle.query.filter_by(scope_id=scope.id, is_archived=False)
        .order_by(ScopeReprocessingCycle.started_at.desc())
        .limit(10)
        .all()
    )
    return {"scope": scope, "maintenance": maintenance, "reprocessing_cycles": cycles}
