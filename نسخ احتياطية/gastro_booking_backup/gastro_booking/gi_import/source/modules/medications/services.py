"""Medication services — Sprint 4B-MED."""

from datetime import date

from app.core.base_model import utcnow
from app.core.exceptions import NotFoundError, ValidationError
from app.engines import audit_engine, permission_engine
from app.extensions import db
from app.modules.encounters.models import ClinicalEncounter
from app.modules.medications.catalogue_seed import seed_medication_catalogue_if_empty
from app.modules.medications.models import (
    ALL_ENTRY_TYPES,
    ENTRY_TYPE_HOME,
    MedicationCatalogueItem,
    MedicationEntry,
    STATUS_ACTIVE,
    STATUS_DRAFT,
    STATUS_REVIEWED,
    STATUS_STOPPED,
    TERMINAL_STATUSES,
)
from app.modules.patients.models import Patient


def ensure_catalogue_seeded() -> None:
    seed_medication_catalogue_if_empty()


def _require(acting_user, code: str, target_id=None):
    permission_engine.require(
        acting_user, code, audit_context={"target_type": "Medication", "target_id": target_id}
    )


def get_entry(acting_user, entry_id: int) -> MedicationEntry:
    _require(acting_user, "medication:view", entry_id)
    entry = MedicationEntry.query.get(entry_id)
    if entry is None or entry.is_archived:
        raise NotFoundError(f"No medication entry with id {entry_id}")
    return entry


def list_catalogue(acting_user):
    _require(acting_user, "medication:view")
    ensure_catalogue_seeded()
    return (
        MedicationCatalogueItem.query.filter_by(is_archived=False)
        .order_by(MedicationCatalogueItem.sort_order, MedicationCatalogueItem.name)
        .all()
    )


def list_entries_for_encounter(acting_user, encounter_id: int):
    _require(acting_user, "medication:view")
    return (
        MedicationEntry.query.filter_by(encounter_id=encounter_id, is_archived=False)
        .order_by(MedicationEntry.documented_at.desc())
        .all()
    )


def create_medication_entry(
    acting_user,
    encounter: ClinicalEncounter,
    catalogue_item_id: int,
    entry_type: str = ENTRY_TYPE_HOME,
    dose_text: str = None,
    route: str = None,
    frequency_text: str = None,
    indication: str = None,
    started_on: date = None,
    notes: str = None,
    mark_active: bool = True,
) -> MedicationEntry:
    _require(acting_user, "medication:document")
    ensure_catalogue_seeded()

    if entry_type not in ALL_ENTRY_TYPES:
        raise ValidationError(f"Invalid entry type: {entry_type}")

    item = MedicationCatalogueItem.query.get(catalogue_item_id)
    if item is None or item.is_archived:
        raise ValidationError("Invalid medication selected.")

    entry = MedicationEntry(
        encounter_id=encounter.id,
        patient_id=encounter.patient_id,
        catalogue_item_id=item.id,
        drug_code=item.code,
        entry_type=entry_type,
        status=STATUS_ACTIVE if mark_active else STATUS_DRAFT,
        dose_text=(dose_text or "").strip() or None,
        route=(route or item.default_route or "").strip() or None,
        frequency_text=(frequency_text or "").strip() or None,
        indication=(indication or "").strip() or None,
        started_on=started_on or date.today(),
        notes=(notes or "").strip() or None,
        documented_by_id=getattr(acting_user, "id", None),
        department_id=encounter.department_id,
        created_by_id=getattr(acting_user, "id", None),
    )
    db.session.add(entry)
    db.session.commit()

    audit_engine.log(
        action="medication.entry_created",
        user=acting_user,
        target_type="MedicationEntry",
        target_id=entry.id,
        details={"drug_code": item.code, "entry_type": entry_type, "status": entry.status},
    )
    return entry


def activate_entry(acting_user, entry: MedicationEntry) -> MedicationEntry:
    _require(acting_user, "medication:document", entry.id)
    if entry.status in TERMINAL_STATUSES:
        raise ValidationError("Entry is in a terminal status.")
    entry.status = STATUS_ACTIVE
    db.session.commit()
    audit_engine.log(
        action="medication.entry_activated",
        user=acting_user,
        target_type="MedicationEntry",
        target_id=entry.id,
        details={},
    )
    return entry


def stop_entry(acting_user, entry: MedicationEntry, stopped_on: date = None, notes: str = None) -> MedicationEntry:
    _require(acting_user, "medication:document", entry.id)
    if entry.status in TERMINAL_STATUSES:
        raise ValidationError("Entry is already stopped or reviewed.")
    entry.status = STATUS_STOPPED
    entry.stopped_on = stopped_on or date.today()
    if notes is not None:
        entry.notes = notes.strip() or entry.notes
    db.session.commit()
    audit_engine.log(
        action="medication.entry_stopped",
        user=acting_user,
        target_type="MedicationEntry",
        target_id=entry.id,
        details={"stopped_on": str(entry.stopped_on)},
    )
    return entry


def review_entry(acting_user, entry: MedicationEntry) -> MedicationEntry:
    _require(acting_user, "medication:review", entry.id)
    if entry.status != STATUS_ACTIVE:
        raise ValidationError("Only active entries can be marked reviewed.")
    entry.status = STATUS_REVIEWED
    entry.reviewed_at = utcnow()
    entry.reviewed_by_id = getattr(acting_user, "id", None)
    db.session.commit()
    audit_engine.log(
        action="medication.entry_reviewed",
        user=acting_user,
        target_type="MedicationEntry",
        target_id=entry.id,
        details={},
    )
    return entry


def patient_medication_timeline(acting_user, patient_id: int) -> list[dict]:
    _require(acting_user, "medication:view")
    patient = Patient.query.get(patient_id)
    if patient is None:
        raise NotFoundError(f"No patient with id {patient_id}")

    events: list[dict] = []
    for entry in MedicationEntry.query.filter_by(patient_id=patient_id, is_archived=False).all():
        label = entry.catalogue_item.name if entry.catalogue_item else entry.drug_code
        summary_parts = []
        if entry.dose_text:
            summary_parts.append(entry.dose_text)
        if entry.frequency_text:
            summary_parts.append(entry.frequency_text)
        events.append(
            {
                "kind": "medication",
                "timestamp": entry.documented_at,
                "label": label,
                "status": entry.status,
                "entry_type": entry.entry_type,
                "summary": " · ".join(summary_parts) if summary_parts else "—",
                "id": entry.id,
            }
        )
    events.sort(key=lambda e: e["timestamp"] or utcnow(), reverse=True)
    return events


def active_medications_for_patient(acting_user, patient_id: int) -> list[MedicationEntry]:
    _require(acting_user, "medication:view")
    return (
        MedicationEntry.query.filter_by(patient_id=patient_id, status=STATUS_ACTIVE, is_archived=False)
        .order_by(MedicationEntry.started_on.desc())
        .all()
    )
