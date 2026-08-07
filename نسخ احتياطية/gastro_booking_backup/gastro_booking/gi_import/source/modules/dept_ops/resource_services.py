"""Department resource management — Sprint 7C."""

from __future__ import annotations

from datetime import datetime

from app.core.base_model import utcnow
from app.core.exceptions import NotFoundError, ValidationError
from app.extensions import db
from app.engines import audit_engine, permission_engine
from app.modules.dept_ops.audit_helper import log_status_change
from app.modules.dept_ops.constants import ALL_RESOURCE_TYPES
from app.modules.dept_ops.models import DepartmentResource, ResourceStatusLog


def _require(user, permission: str) -> None:
    permission_engine.require(user, permission)


def list_resources(acting_user, *, resource_type: str | None = None) -> list[DepartmentResource]:
    _require(acting_user, "dept_ops:view")
    query = DepartmentResource.query.filter_by(is_archived=False)
    if resource_type:
        query = query.filter_by(resource_type=resource_type)
    return query.order_by(DepartmentResource.name.asc()).all()


def create_resource(
    acting_user,
    *,
    name: str,
    resource_type: str,
    location: str | None = None,
    assigned_room_id: int | None = None,
    notes: str | None = None,
) -> DepartmentResource:
    _require(acting_user, "dept_ops:manage")
    if resource_type not in ALL_RESOURCE_TYPES:
        raise ValidationError(f"Invalid resource type '{resource_type}'.")
    resource = DepartmentResource(
        name=name.strip(),
        resource_type=resource_type,
        status="available",
        location=location,
        assigned_room_id=assigned_room_id,
        notes=notes,
        department_id=getattr(acting_user, "department_id", 1) or 1,
        created_by_id=acting_user.id,
    )
    db.session.add(resource)
    db.session.commit()
    return resource


def update_resource_status(
    acting_user, resource: DepartmentResource, status: str, notes: str | None = None
) -> DepartmentResource:
    _require(acting_user, "dept_ops:manage")
    prev = resource.status
    resource.status = status
    log_status_change(
        acting_user=acting_user,
        resource_type=resource.resource_type,
        resource_id=resource.id,
        previous_status=prev,
        new_status=status,
        notes=notes,
    )
    db.session.commit()
    return resource


def resources_under_maintenance(acting_user) -> list[DepartmentResource]:
    _require(acting_user, "dept_ops:view")
    return DepartmentResource.query.filter_by(is_archived=False, status="maintenance").all()


def resource_audit_trail(acting_user, resource_type: str, resource_id: int) -> list[ResourceStatusLog]:
    _require(acting_user, "dept_ops:view")
    return (
        ResourceStatusLog.query.filter_by(resource_type=resource_type, resource_id=resource_id)
        .order_by(ResourceStatusLog.changed_at.desc())
        .all()
    )
