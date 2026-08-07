"""Clinical Encounter services — Sprint 4A-LAB."""

from app.core.base_model import utcnow
from app.core.exceptions import NotFoundError, ValidationError
from app.engines import audit_engine, permission_engine
from app.extensions import db
from app.modules.encounters.models import (
    ALL_ENCOUNTER_TYPES,
    ENCOUNTER_STATUS_CLOSED,
    ENCOUNTER_STATUS_OPEN,
    ENCOUNTER_TYPE_OPD,
    ClinicalEncounter,
)
from app.modules.patients.models import Patient


def _require_view(acting_user, target_id=None):
    permission_engine.require(
        acting_user, "encounter:view", audit_context={"target_type": "ClinicalEncounter", "target_id": target_id}
    )


def _require_create(acting_user):
    permission_engine.require(
        acting_user, "encounter:create", audit_context={"target_type": "ClinicalEncounter"}
    )


def get_encounter(acting_user, encounter_id: int) -> ClinicalEncounter:
    _require_view(acting_user, encounter_id)
    encounter = ClinicalEncounter.query.get(encounter_id)
    if encounter is None or encounter.is_archived:
        raise NotFoundError(f"No encounter with id {encounter_id}")
    return encounter


def list_encounters_for_patient(acting_user, patient_id: int, include_archived: bool = False):
    _require_view(acting_user)
    query = ClinicalEncounter.query.filter_by(patient_id=patient_id)
    if not include_archived:
        query = query.filter_by(is_archived=False)
    return query.order_by(ClinicalEncounter.started_at.desc()).all()


def list_open_encounters(acting_user):
    _require_view(acting_user)
    return (
        ClinicalEncounter.query.filter_by(status=ENCOUNTER_STATUS_OPEN, is_archived=False)
        .order_by(ClinicalEncounter.started_at.desc())
        .limit(100)
        .all()
    )


def create_encounter(
    acting_user,
    patient_id: int,
    encounter_type: str = ENCOUNTER_TYPE_OPD,
    appointment_id: int = None,
    summary: str = None,
) -> ClinicalEncounter:
    _require_create(acting_user)
    if encounter_type not in ALL_ENCOUNTER_TYPES:
        raise ValidationError(f"Invalid encounter type: {encounter_type}")

    patient = Patient.query.get(patient_id)
    if patient is None or patient.is_archived:
        raise NotFoundError(f"No patient with id {patient_id}")

    encounter = ClinicalEncounter(
        patient_id=patient.id,
        appointment_id=appointment_id,
        encounter_type=encounter_type,
        status=ENCOUNTER_STATUS_OPEN,
        summary=(summary or "").strip() or None,
        department_id=patient.department_id,
        created_by_id=getattr(acting_user, "id", None),
    )
    db.session.add(encounter)
    db.session.commit()

    audit_engine.log(
        action="encounter.created",
        user=acting_user,
        target_type="ClinicalEncounter",
        target_id=encounter.id,
        details={"patient_id": patient.id, "encounter_type": encounter_type},
    )
    return encounter


def close_encounter(acting_user, encounter: ClinicalEncounter) -> ClinicalEncounter:
    _require_create(acting_user)
    if encounter.status == ENCOUNTER_STATUS_CLOSED:
        raise ValidationError("Encounter is already closed.")
    encounter.status = ENCOUNTER_STATUS_CLOSED
    encounter.closed_at = utcnow()
    db.session.commit()

    audit_engine.log(
        action="encounter.closed",
        user=acting_user,
        target_type="ClinicalEncounter",
        target_id=encounter.id,
        details={},
    )
    from app.modules.workforce.portfolio_events import on_encounter_closed

    on_encounter_closed(encounter, acting_user)
    return encounter
