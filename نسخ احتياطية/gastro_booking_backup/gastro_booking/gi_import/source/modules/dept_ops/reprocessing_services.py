"""Scope reprocessing / sterilisation workflow — Sprint 7C."""

from __future__ import annotations

from app.core.base_model import utcnow
from app.core.exceptions import NotFoundError, ValidationError
from app.extensions import db
from app.engines import audit_engine, permission_engine
from app.modules.dept_ops.constants import (
    REPROCESSING_STEPS,
    REPROC_PROCEDURE_FINISHED,
    REPROC_READY,
    SCOPE_AVAILABLE,
    SCOPE_AWAITING_CLEANING,
    SCOPE_CLEANING,
)
from app.modules.dept_ops.models import Endoscope, ScopeReprocessingCycle, ScopeReprocessingStep
from app.modules.dept_ops.scope_services import release_scope_after_procedure, update_scope_status


def _require(user, permission: str) -> None:
    permission_engine.require(user, permission)


def get_active_cycle(scope_id: int) -> ScopeReprocessingCycle | None:
    return (
        ScopeReprocessingCycle.query.filter_by(scope_id=scope_id, status="in_progress", is_archived=False)
        .order_by(ScopeReprocessingCycle.started_at.desc())
        .first()
    )


def start_reprocessing(acting_user, scope: Endoscope, procedure_session_id: int | None = None) -> ScopeReprocessingCycle:
    _require(acting_user, "dept_ops:scope_manage")
    if get_active_cycle(scope.id):
        raise ValidationError("Scope already has an active reprocessing cycle.")
    now = utcnow()
    cycle = ScopeReprocessingCycle(
        scope_id=scope.id,
        procedure_session_id=procedure_session_id,
        started_at=now,
        current_step=REPROC_PROCEDURE_FINISHED,
        status="in_progress",
        department_id=getattr(acting_user, "department_id", 1) or 1,
        created_by_id=acting_user.id,
    )
    db.session.add(cycle)
    db.session.flush()
    _record_step(acting_user, cycle, REPROC_PROCEDURE_FINISHED)
    update_scope_status(acting_user, scope, SCOPE_CLEANING, notes="Reprocessing started")
    audit_engine.log("dept_ops.reprocessing_started", user=acting_user, target_type="endoscope", target_id=scope.id)
    db.session.commit()
    return cycle


def start_reprocessing_for_session(session, acting_user) -> ScopeReprocessingCycle | None:
    """Hook: start reprocessing for scopes assigned to a completed session."""
    scopes = Endoscope.query.filter_by(
        is_archived=False, assigned_procedure_id=session.procedure_id
    ).all()
    if not scopes:
        return None
    cycles = []
    for scope in scopes:
        release_scope_after_procedure(acting_user, scope)
        cycles.append(start_reprocessing(acting_user, scope, session.id))
    return cycles[0] if cycles else None


def advance_reprocessing_step(acting_user, cycle: ScopeReprocessingCycle, notes: str | None = None) -> ScopeReprocessingCycle:
    _require(acting_user, "dept_ops:scope_manage")
    if cycle.status != "in_progress":
        raise ValidationError("Reprocessing cycle is not active.")
    try:
        idx = REPROCESSING_STEPS.index(cycle.current_step)
    except ValueError:
        raise ValidationError("Invalid current step.")
    if idx >= len(REPROCESSING_STEPS) - 1:
        raise ValidationError("Reprocessing cycle is at final step — complete it instead.")
    next_step = REPROCESSING_STEPS[idx + 1]
    cycle.current_step = next_step
    _record_step(acting_user, cycle, next_step, notes=notes)
    scope = Endoscope.query.get(cycle.scope_id)
    if scope and next_step != REPROC_READY:
        update_scope_status(acting_user, scope, SCOPE_CLEANING, notes=notes)
    db.session.commit()
    return cycle


def complete_reprocessing(acting_user, cycle: ScopeReprocessingCycle, notes: str | None = None) -> ScopeReprocessingCycle:
    _require(acting_user, "dept_ops:scope_manage")
    if cycle.status != "in_progress":
        raise ValidationError("Reprocessing cycle is not active.")
    cycle.current_step = REPROC_READY
    cycle.completed_at = utcnow()
    cycle.status = "completed"
    _record_step(acting_user, cycle, REPROC_READY, notes=notes)
    scope = Endoscope.query.get(cycle.scope_id)
    if scope:
        update_scope_status(acting_user, scope, SCOPE_AVAILABLE, notes="Reprocessing complete — available for use")
    audit_engine.log(
        "dept_ops.reprocessing_completed",
        user=acting_user,
        target_type="scope_reprocessing_cycle",
        target_id=cycle.id,
    )
    db.session.commit()
    return cycle


def _record_step(acting_user, cycle: ScopeReprocessingCycle, step_code: str, notes: str | None = None) -> ScopeReprocessingStep:
    step = ScopeReprocessingStep(
        cycle_id=cycle.id,
        step_code=step_code,
        completed_at=utcnow(),
        completed_by_id=acting_user.id,
        notes=notes,
        department_id=getattr(acting_user, "department_id", 1) or 1,
        created_by_id=acting_user.id,
    )
    db.session.add(step)
    return step


def cleaning_queue(acting_user) -> list[ScopeReprocessingCycle]:
    _require(acting_user, "dept_ops:view")
    return ScopeReprocessingCycle.query.filter_by(status="in_progress", is_archived=False).order_by(
        ScopeReprocessingCycle.started_at.asc()
    ).all()
