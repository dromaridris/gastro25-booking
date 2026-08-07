"""Resource status audit logging — Sprint 7C."""

from __future__ import annotations

from app.core.base_model import utcnow
from app.extensions import db
from app.engines import audit_engine
from app.modules.dept_ops.models import ResourceStatusLog


def log_status_change(
    *,
    acting_user,
    resource_type: str,
    resource_id: int,
    previous_status: str | None,
    new_status: str,
    notes: str | None = None,
) -> ResourceStatusLog:
    entry = ResourceStatusLog(
        resource_type=resource_type,
        resource_id=resource_id,
        previous_status=previous_status,
        new_status=new_status,
        changed_by_id=getattr(acting_user, "id", None),
        changed_at=utcnow(),
        notes=notes,
        department_id=getattr(acting_user, "department_id", 1) or 1,
    )
    db.session.add(entry)
    audit_engine.log(
        "dept_ops.status_changed",
        user=acting_user,
        target_type=resource_type,
        target_id=resource_id,
        details={"previous": previous_status, "new": new_status, "notes": notes},
    )
    return entry
