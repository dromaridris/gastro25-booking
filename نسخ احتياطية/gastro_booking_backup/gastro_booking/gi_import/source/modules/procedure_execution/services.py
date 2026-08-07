"""
Service layer for Procedure Execution (Sprint 2C).

Depends on the frozen Sprint 2B Procedure model and its services for
procedure lookup and workflow cancellation, but does not modify them.

Permissions (see app/modules/rbac/seed_data.py):
- procedure_execution:view — view execution sessions.
- procedure_execution:edit — edit team, times, sedation, checklist,
  outcome, and cancel during execution. Mirrors procedure:workflow's
  role set (nurses included) since day-to-day execution is
  nursing-driven.
"""

from datetime import datetime, timezone

from app.core.exceptions import NotFoundError, ValidationError
from app.engines import audit_engine, permission_engine
from app.extensions import db
from app.modules.auth.models import User
from app.modules.procedure_execution.models import (
    ALL_OUTCOMES,
    ALL_SEDATION_CATEGORIES,
    OUTCOME_COMPLETED,
    ProcedureSession,
    RoomOccupancyPeriod,
)
from app.modules.procedures import services as procedure_services
from app.modules.procedures.models import (
    STATUS_BOOKED,
    STATUS_IN_ROOM,
    STATUS_READY,
    STATUS_WAITING,
    TERMINAL_STATUSES,
    Procedure,
)

# Sprint 2C explicit product rule: execution sessions may only be opened
# while the procedure is still in an active scheduling/workflow state.
# Finished and cancelled procedures are terminal — see Sprint 2B.
ACTIVE_PROCEDURE_STATUSES_FOR_SESSION = {
    STATUS_BOOKED,
    STATUS_WAITING,
    STATUS_READY,
    STATUS_IN_ROOM,
}


def _utcnow():
    return datetime.now(timezone.utc)


def _ensure_utc(dt):
    """Normalize to UTC naive datetime — matches SQLite round-tripping and the
    rest of this test suite's convention (see appointments tests)."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt
    return dt.astimezone(timezone.utc).replace(tzinfo=None)


def _department_id_for(acting_user, department_id=None):
    return department_id or getattr(acting_user, "department_id", None)


def _require_view(acting_user):
    permission_engine.require(acting_user, "procedure_execution:view")


def _require_edit(acting_user, session: ProcedureSession = None):
    audit_context = {"target_type": "ProcedureSession"}
    if session is not None:
        audit_context["target_id"] = session.id
    permission_engine.require(acting_user, "procedure_execution:edit", audit_context=audit_context)


def _raise_if_not_editable(session: ProcedureSession) -> None:
    if session.is_cancelled:
        raise ValidationError("This execution session has been cancelled — no further edits allowed.")
    if session.outcome is not None:
        raise ValidationError(
            f"This execution session already has outcome '{session.outcome}' — no further edits allowed."
        )


def _resolve_team_member(user_id, *, require_provider=False):
    if user_id is None:
        return None
    user = User.query.get(user_id)
    if user is None or user.is_archived or not user.is_active_account:
        raise ValidationError("Invalid team member: must be an active user.")
    if require_provider and not user.is_provider:
        raise ValidationError("Endoscopist must be an active user with the provider flag set.")
    return user


def _validate_time_order(
    patient_in_at,
    procedure_start_at,
    procedure_finish_at,
    patient_out_at,
) -> None:
    ordered = [
        ("Patient In", patient_in_at),
        ("Procedure Start", procedure_start_at),
        ("Procedure Finish", procedure_finish_at),
        ("Patient Out", patient_out_at),
    ]
    previous_label = None
    previous_value = None
    for label, value in ordered:
        if value is None:
            continue
        if previous_value is not None and value < previous_value:
            raise ValidationError(
                f"{label} cannot be earlier than {previous_label}."
            )
        previous_label = label
        previous_value = value


def _snapshot_times(session: ProcedureSession) -> dict:
    return {
        "patient_in_at": session.patient_in_at.isoformat() if session.patient_in_at else None,
        "procedure_start_at": (
            session.procedure_start_at.isoformat() if session.procedure_start_at else None
        ),
        "procedure_finish_at": (
            session.procedure_finish_at.isoformat() if session.procedure_finish_at else None
        ),
        "patient_out_at": session.patient_out_at.isoformat() if session.patient_out_at else None,
    }


def _snapshot_team(session: ProcedureSession) -> dict:
    return {
        "endoscopist_id": session.endoscopist_id,
        "assistant_id": session.assistant_id,
        "nurse_id": session.nurse_id,
        "technician_id": session.technician_id,
        "anaesthetist_id": session.anaesthetist_id,
    }


def _close_open_occupancy(session: ProcedureSession, until: datetime) -> None:
    for period in session.occupancy_periods:
        if period.is_open:
            period.occupied_until = until


def _sync_room_occupancy(session: ProcedureSession) -> None:
    """
    Maintain room occupancy intervals from execution timestamps and the
    procedure's current room assignment. Opens a period when patient_in_at
    is set and a room is assigned; closes when patient_out_at is set.
    Handles patient_in and patient_out being set in a single update.
    """
    procedure = session.procedure
    room_id = procedure.room_id if procedure else None
    now = _utcnow()

    if room_id is None:
        if session.patient_out_at is not None:
            _close_open_occupancy(session, session.patient_out_at)
        return

    open_periods = [p for p in session.occupancy_periods if p.is_open]

    if session.patient_out_at is not None:
        if open_periods:
            _close_open_occupancy(session, session.patient_out_at)
        elif session.patient_in_at is not None:
            already = RoomOccupancyPeriod.query.filter_by(
                procedure_session_id=session.id, room_id=room_id
            ).first()
            if already is None:
                db.session.add(
                    RoomOccupancyPeriod(
                        procedure_session_id=session.id,
                        room_id=room_id,
                        department_id=session.department_id,
                        occupied_from=session.patient_in_at,
                        occupied_until=session.patient_out_at,
                    )
                )
        return

    if session.patient_in_at is None:
        return

    open_for_room = [p for p in open_periods if p.room_id == room_id]
    if open_for_room:
        return

    _close_open_occupancy(session, now)
    db.session.add(
        RoomOccupancyPeriod(
            procedure_session_id=session.id,
            room_id=room_id,
            department_id=session.department_id,
            occupied_from=session.patient_in_at,
        )
    )


def _raise_if_procedure_not_active_for_session(procedure: Procedure) -> None:
    if procedure.status not in ACTIVE_PROCEDURE_STATUSES_FOR_SESSION:
        raise ValidationError(
            f"Cannot start an execution session for a procedure with status "
            f"'{procedure.status}'. Sessions may only be created for active "
            "procedures (booked, waiting, ready, in_room)."
        )


def _resolve_procedure(procedure_id: int) -> Procedure:
    procedure = Procedure.query.get(procedure_id)
    if procedure is None or procedure.is_archived:
        raise NotFoundError(f"No procedure with id {procedure_id}")
    return procedure


def get_session(acting_user, session_id: int) -> ProcedureSession:
    _require_view(acting_user)
    session = ProcedureSession.query.get(session_id)
    if session is None:
        raise NotFoundError(f"No procedure session with id {session_id}")
    return session


def get_session_for_procedure(acting_user, procedure_id: int) -> ProcedureSession:
    _require_view(acting_user)
    session = ProcedureSession.query.filter_by(procedure_id=procedure_id).first()
    if session is None:
        raise NotFoundError(f"No execution session for procedure {procedure_id}")
    return session


def list_sessions(acting_user, include_archived: bool = False, active_only: bool = False):
    _require_view(acting_user)
    query = ProcedureSession.query
    if not include_archived:
        query = query.filter_by(is_archived=False)
    if active_only:
        query = query.filter_by(is_cancelled=False).filter(ProcedureSession.outcome.is_(None))
    return query.order_by(ProcedureSession.created_at.desc()).all()


def create_session(acting_user, procedure_id: int, department_id: int = None) -> ProcedureSession:
    _require_edit(acting_user)
    procedure = _resolve_procedure(procedure_id)
    _raise_if_procedure_not_active_for_session(procedure)

    existing = ProcedureSession.query.filter_by(procedure_id=procedure.id).first()
    if existing is not None:
        raise ValidationError(
            f"Procedure {procedure.id} already has an execution session (id {existing.id})."
        )

    patient = procedure.patient
    if patient is None:
        raise ValidationError("Procedure has no linked patient.")

    session = ProcedureSession(
        procedure_id=procedure.id,
        patient_id=patient.id,
        appointment_id=procedure.appointment_id,
        endoscopist_id=procedure.endoscopist_id,
        department_id=_department_id_for(acting_user, department_id),
        created_by_id=getattr(acting_user, "id", None),
    )
    db.session.add(session)
    db.session.commit()

    audit_engine.log(
        action="procedure_session.created",
        user=acting_user,
        target_type="ProcedureSession",
        target_id=session.id,
        details={
            "procedure_id": procedure.id,
            "patient_id": patient.id,
            "appointment_id": procedure.appointment_id,
        },
    )
    return session


def get_or_create_session(acting_user, procedure_id: int) -> ProcedureSession:
    """Return the existing session or create one. Used by the HTTP entry route."""
    try:
        return get_session_for_procedure(acting_user, procedure_id)
    except NotFoundError:
        return create_session(acting_user, procedure_id)


def update_team(
    acting_user,
    session: ProcedureSession,
    endoscopist_id=None,
    assistant_id=None,
    nurse_id=None,
    technician_id=None,
    anaesthetist_id=None,
    *,
    endoscopist_provided: bool = False,
    assistant_provided: bool = False,
    nurse_provided: bool = False,
    technician_provided: bool = False,
    anaesthetist_provided: bool = False,
) -> ProcedureSession:
    _require_edit(acting_user, session)
    _raise_if_not_editable(session)

    before = _snapshot_team(session)

    if endoscopist_provided:
        endoscopist = _resolve_team_member(endoscopist_id, require_provider=True)
        session.endoscopist_id = endoscopist.id if endoscopist else None
    if assistant_provided:
        assistant = _resolve_team_member(assistant_id)
        session.assistant_id = assistant.id if assistant else None
    if nurse_provided:
        nurse = _resolve_team_member(nurse_id)
        session.nurse_id = nurse.id if nurse else None
    if technician_provided:
        technician = _resolve_team_member(technician_id)
        session.technician_id = technician.id if technician else None
    if anaesthetist_provided:
        anaesthetist = _resolve_team_member(anaesthetist_id)
        session.anaesthetist_id = anaesthetist.id if anaesthetist else None

    db.session.commit()

    audit_engine.log(
        action="procedure_session.team_updated",
        user=acting_user,
        target_type="ProcedureSession",
        target_id=session.id,
        details={"before": before, "after": _snapshot_team(session)},
    )
    from app.modules.dept_ops.workforce_integration import on_procedure_team_updated

    on_procedure_team_updated(session, acting_user)
    return session


def update_times(
    acting_user,
    session: ProcedureSession,
    patient_in_at=None,
    procedure_start_at=None,
    procedure_finish_at=None,
    patient_out_at=None,
    *,
    patient_in_provided: bool = False,
    procedure_start_provided: bool = False,
    procedure_finish_provided: bool = False,
    patient_out_provided: bool = False,
) -> ProcedureSession:
    _require_edit(acting_user, session)
    _raise_if_not_editable(session)

    before = _snapshot_times(session)

    if patient_in_provided:
        session.patient_in_at = _ensure_utc(patient_in_at)
    if procedure_start_provided:
        session.procedure_start_at = _ensure_utc(procedure_start_at)
    if procedure_finish_provided:
        session.procedure_finish_at = _ensure_utc(procedure_finish_at)
    if patient_out_provided:
        session.patient_out_at = _ensure_utc(patient_out_at)

    _validate_time_order(
        session.patient_in_at,
        session.procedure_start_at,
        session.procedure_finish_at,
        session.patient_out_at,
    )

    _sync_room_occupancy(session)
    db.session.commit()

    audit_engine.log(
        action="procedure_session.times_updated",
        user=acting_user,
        target_type="ProcedureSession",
        target_id=session.id,
        details={"before": before, "after": _snapshot_times(session)},
    )
    return session


def update_sedation(acting_user, session: ProcedureSession, sedation_category: str) -> ProcedureSession:
    _require_edit(acting_user, session)
    _raise_if_not_editable(session)

    value = sedation_category or None
    if value is not None and value not in ALL_SEDATION_CATEGORIES:
        raise ValidationError(f"Invalid sedation category: {value}")

    before = session.sedation_category
    session.sedation_category = value
    db.session.commit()

    audit_engine.log(
        action="procedure_session.sedation_updated",
        user=acting_user,
        target_type="ProcedureSession",
        target_id=session.id,
        details={"before": before, "after": session.sedation_category},
    )
    return session


def update_checklist(
    acting_user,
    session: ProcedureSession,
    consent_confirmed: bool,
    identity_confirmed: bool,
    indication_confirmed: bool,
    anticoagulants_reviewed: bool,
) -> ProcedureSession:
    _require_edit(acting_user, session)
    _raise_if_not_editable(session)

    before = {
        "consent_confirmed": session.consent_confirmed,
        "identity_confirmed": session.identity_confirmed,
        "indication_confirmed": session.indication_confirmed,
        "anticoagulants_reviewed": session.anticoagulants_reviewed,
    }

    session.consent_confirmed = bool(consent_confirmed)
    session.identity_confirmed = bool(identity_confirmed)
    session.indication_confirmed = bool(indication_confirmed)
    session.anticoagulants_reviewed = bool(anticoagulants_reviewed)
    db.session.commit()

    audit_engine.log(
        action="procedure_session.checklist_updated",
        user=acting_user,
        target_type="ProcedureSession",
        target_id=session.id,
        details={
            "before": before,
            "after": {
                "consent_confirmed": session.consent_confirmed,
                "identity_confirmed": session.identity_confirmed,
                "indication_confirmed": session.indication_confirmed,
                "anticoagulants_reviewed": session.anticoagulants_reviewed,
            },
        },
    )
    return session


def set_outcome(acting_user, session: ProcedureSession, outcome: str) -> ProcedureSession:
    _require_edit(acting_user, session)
    _raise_if_not_editable(session)

    if outcome not in ALL_OUTCOMES:
        raise ValidationError(f"Invalid outcome: {outcome}")

    before = session.outcome
    session.outcome = outcome
    db.session.commit()

    audit_engine.log(
        action="procedure_session.outcome_set",
        user=acting_user,
        target_type="ProcedureSession",
        target_id=session.id,
        details={"before": before, "after": session.outcome},
    )
    if session.outcome == OUTCOME_COMPLETED:
        from app.modules.workforce.portfolio_events import on_procedure_completed

        on_procedure_completed(session, acting_user)
        from app.modules.dept_ops.events import on_procedure_completed as dept_ops_on_procedure_completed

        dept_ops_on_procedure_completed(session, acting_user)
    return session


def cancel_session(acting_user, session: ProcedureSession, reason: str) -> ProcedureSession:
    """
    Execution-phase cancellation (Sprint 2C feature 5). Records reason,
    cancelling user, and time on the session, then cancels the linked
    procedure via the frozen Sprint 2B service if it is not already
    terminal.
    """
    _require_edit(acting_user, session)

    if session.is_cancelled:
        raise ValidationError("This execution session is already cancelled.")

    reason_clean = (reason or "").strip()
    if not reason_clean:
        raise ValidationError("Cancellation reason is required.")

    now = _utcnow()
    session.is_cancelled = True
    session.cancellation_reason = reason_clean
    session.cancelled_by_id = getattr(acting_user, "id", None)
    session.cancelled_at = now

    _close_open_occupancy(session, now)
    db.session.commit()

    audit_engine.log(
        action="procedure_session.cancelled",
        user=acting_user,
        target_type="ProcedureSession",
        target_id=session.id,
        details={"reason": reason_clean, "cancelled_at": now.isoformat()},
    )

    procedure = session.procedure
    if procedure is not None and procedure.status not in TERMINAL_STATUSES:
        procedure_services.cancel_procedure(acting_user, procedure, reason=reason_clean)
        db.session.refresh(procedure)

    return session


def list_room_occupancy(acting_user, room_id: int = None, session_id: int = None):
    """Query occupancy periods for utilisation reporting."""
    _require_view(acting_user)
    query = RoomOccupancyPeriod.query
    if room_id is not None:
        query = query.filter_by(room_id=room_id)
    if session_id is not None:
        query = query.filter_by(procedure_session_id=session_id)
    return query.order_by(RoomOccupancyPeriod.occupied_from.desc()).all()
