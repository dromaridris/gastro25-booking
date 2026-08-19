"""Event hooks — Sprint 7C full operational automation."""

from __future__ import annotations

from app.extensions import db
from app.modules.dept_ops.constants import SCOPE_AVAILABLE, SCOPE_AWAITING_CLEANING, SCOPE_IN_PROCEDURE
from app.modules.dept_ops.models import Endoscope
from app.modules.procedures.models import STATUS_FINISHED, STATUS_IN_ROOM


def on_procedure_status_changed(procedure, acting_user) -> None:
    from app.modules.dept_ops.room_services import sync_room_state_for_procedure

    sync_room_state_for_procedure(procedure, acting_user)
    if procedure.status == STATUS_IN_ROOM and procedure.room_id:
        _occupy_room(procedure, acting_user)
    elif procedure.status == STATUS_FINISHED:
        _release_room(procedure, acting_user)
    db.session.commit()


def on_room_assigned(procedure, acting_user) -> None:
    from app.modules.dept_ops.room_services import sync_room_state_for_procedure

    sync_room_state_for_procedure(procedure, acting_user)
    if procedure.status == STATUS_IN_ROOM:
        _occupy_room(procedure, acting_user)
    db.session.commit()


def on_procedure_completed(session, acting_user) -> None:
    from app.modules.dept_ops.consumable_services import deduct_planned_consumables
    from app.modules.dept_ops.reprocessing_services import start_reprocessing_for_session

    procedure = session.procedure
    if procedure:
        _release_room(procedure, acting_user)
    start_reprocessing_for_session(session, acting_user)
    if procedure:
        deduct_planned_consumables(acting_user, procedure.id)
    from app.modules.dept_ops.workforce_integration import on_procedure_team_updated

    on_procedure_team_updated(session, acting_user)
    db.session.commit()


def _occupy_room(procedure, acting_user) -> None:
    from app.modules.dept_ops.room_services import get_or_create_room_state, update_room_status
    from app.modules.dept_ops.constants import ROOM_OCCUPIED

    state = get_or_create_room_state(procedure.room_id)
    if state.status != ROOM_OCCUPIED:
        update_room_status(acting_user, procedure.room_id, ROOM_OCCUPIED, notes=f"Procedure {procedure.id} in room")
        state.current_procedure_id = procedure.id


def _release_room(procedure, acting_user) -> None:
    from app.modules.dept_ops.constants import ROOM_AVAILABLE
    from app.modules.dept_ops.room_services import get_or_create_room_state, update_room_status

    if not procedure.room_id:
        return
    state = get_or_create_room_state(procedure.room_id)
    state.current_procedure_id = None
    update_room_status(acting_user, procedure.room_id, ROOM_AVAILABLE, notes=f"Procedure {procedure.id} released")


def on_reprocessing_completed(scope, acting_user) -> None:
    from app.modules.dept_ops.scope_services import update_scope_status

    update_scope_status(acting_user, scope, SCOPE_AVAILABLE, notes="Reprocessing complete — available for use")
