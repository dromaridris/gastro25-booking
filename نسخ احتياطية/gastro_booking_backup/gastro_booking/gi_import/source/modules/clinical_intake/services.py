"""Clinical Intake services — complaint selection and structured intake records."""

from __future__ import annotations

from typing import Any

from app.core.exceptions import NotFoundError, ValidationError
from app.engines import audit_engine
from app.extensions import db
from app.modules.clinical_intake.catalogue_seed import seed_chief_complaint_library_if_empty
from app.modules.clinical_intake.hooks import run_intake_extensions
from app.modules.clinical_intake.models import (
    INTAKE_STATUS_CONFIRMED,
    INTAKE_STATUS_MODIFIED,
    ClinicalIntakeRecord,
    ChiefComplaintEntry,
    normalize_text,
)
from app.modules.clinical_intake.permissions import require_intake_use, require_intake_view
from app.modules.clinical_intake.search import ComplaintSearchEngine
from app.modules.clinical_intake.validators import (
    build_unknown_normalization,
    validate_complaint_required,
    validate_no_duplicate_intake,
    validate_normalized_entry,
    validate_priority,
)
from app.modules.encounters.models import ENCOUNTER_STATUS_OPEN, ClinicalEncounter


def ensure_library_seeded() -> int:
    return seed_chief_complaint_library_if_empty()


def search_complaints(
    acting_user,
    query: str,
    *,
    specialty_code: str | None = None,
    limit: int = 10,
) -> list[dict[str, Any]]:
    require_intake_view(acting_user)
    ensure_library_seeded()
    engine = ComplaintSearchEngine(specialty_code=specialty_code)
    return [item.to_dict() for item in engine.search(query, limit=limit)]


def get_intake_for_encounter(acting_user, encounter_id: int) -> ClinicalIntakeRecord | None:
    require_intake_view(acting_user, encounter_id=encounter_id)
    return ClinicalIntakeRecord.query.filter_by(
        encounter_id=encounter_id, is_archived=False
    ).first()


def _get_open_encounter(encounter_id: int) -> ClinicalEncounter:
    encounter = ClinicalEncounter.query.get(encounter_id)
    if encounter is None or encounter.is_archived:
        raise NotFoundError(f"No encounter with id {encounter_id}")
    if encounter.status != ENCOUNTER_STATUS_OPEN:
        raise ValidationError("Clinical intake can only be created for open encounters.")
    return encounter


def _resolve_complaint(
    *,
    chief_complaint: str,
    complaint_entry_id: int | None,
    allow_unknown: bool,
    specialty_code: str | None,
) -> tuple[ChiefComplaintEntry | None, str, str, bool]:
    ensure_library_seeded()
    normalized_input = normalize_text(chief_complaint)

    entry: ChiefComplaintEntry | None = None
    if complaint_entry_id is not None:
        entry = ChiefComplaintEntry.query.filter_by(
            id=complaint_entry_id, is_active=True, is_archived=False
        ).first()
        if entry is None:
            raise ValidationError("Selected complaint is not a valid library entry.")

    if entry is None:
        match = ComplaintSearchEngine(specialty_code=specialty_code).resolve(chief_complaint)
        if match is not None:
            entry = ChiefComplaintEntry.query.get(match.complaint_id)

    if entry is not None:
        return entry, entry.display_name, entry.normalized_name, False

    if allow_unknown:
        return None, chief_complaint.strip(), build_unknown_normalization(chief_complaint), True

    raise ValidationError("Unknown complaint. Select a library entry or enable unknown complaint handling.")


def create_intake(
    acting_user,
    *,
    encounter_id: int,
    chief_complaint: str,
    complaint_entry_id: int | None = None,
    symptom_onset: str | None = None,
    priority: str | None = None,
    allow_unknown: bool = False,
    specialty_code: str | None = None,
) -> ClinicalIntakeRecord:
    require_intake_use(acting_user, encounter_id=encounter_id)
    encounter = _get_open_encounter(encounter_id)
    validate_no_duplicate_intake(encounter.id)

    complaint_text = validate_complaint_required(chief_complaint)
    entry, display, normalized, is_unknown = _resolve_complaint(
        chief_complaint=complaint_text,
        complaint_entry_id=complaint_entry_id,
        allow_unknown=allow_unknown,
        specialty_code=specialty_code,
    )
    validate_normalized_entry(
        normalized_complaint=normalized,
        is_unknown=is_unknown,
        complaint_entry_id=entry.id if entry else None,
    )

    record = ClinicalIntakeRecord(
        encounter_id=encounter.id,
        patient_id=encounter.patient_id,
        complaint_entry_id=entry.id if entry else None,
        chief_complaint=display,
        normalized_complaint=normalized,
        complaint_category=entry.category.name if entry and entry.category else None,
        symptom_onset=(symptom_onset or "").strip() or None,
        priority=validate_priority(priority),
        status=INTAKE_STATUS_CONFIRMED,
        is_unknown_complaint=is_unknown,
        department_id=encounter.department_id,
        created_by_id=getattr(acting_user, "id", None),
    )
    db.session.add(record)
    db.session.commit()

    extension_results = run_intake_extensions(
        "complaint_selected",
        record,
        acting_user=acting_user,
        encounter=encounter,
    )
    if extension_results:
        record.extension_payload = {"complaint_selected": extension_results}
        db.session.commit()

    audit_engine.log(
        action="clinical_intake.complaint_selected",
        user=acting_user,
        target_type="ClinicalIntakeRecord",
        target_id=record.id,
        details={
            "encounter_id": encounter.id,
            "patient_id": encounter.patient_id,
            "chief_complaint": record.chief_complaint,
            "normalized_complaint": record.normalized_complaint,
            "complaint_entry_id": record.complaint_entry_id,
            "is_unknown_complaint": record.is_unknown_complaint,
        },
    )
    audit_engine.log(
        action="clinical_intake.normalization_result",
        user=acting_user,
        target_type="ClinicalIntakeRecord",
        target_id=record.id,
        details={
            "encounter_id": encounter.id,
            "input": complaint_text,
            "normalized_complaint": record.normalized_complaint,
            "matched_library": record.complaint_entry_id is not None,
        },
    )
    return record


def update_intake(
    acting_user,
    intake_id: int,
    *,
    chief_complaint: str | None = None,
    complaint_entry_id: int | None = None,
    symptom_onset: str | None = None,
    priority: str | None = None,
    allow_unknown: bool = False,
    specialty_code: str | None = None,
) -> ClinicalIntakeRecord:
    require_intake_use(acting_user)
    record = ClinicalIntakeRecord.query.get(intake_id)
    if record is None or record.is_archived:
        raise NotFoundError(f"No clinical intake with id {intake_id}")

    encounter = _get_open_encounter(record.encounter_id)
    previous = record.chief_complaint

    if chief_complaint is not None:
        complaint_text = validate_complaint_required(chief_complaint)
        entry, display, normalized, is_unknown = _resolve_complaint(
            chief_complaint=complaint_text,
            complaint_entry_id=complaint_entry_id,
            allow_unknown=allow_unknown,
            specialty_code=specialty_code,
        )
        validate_normalized_entry(
            normalized_complaint=normalized,
            is_unknown=is_unknown,
            complaint_entry_id=entry.id if entry else None,
        )
        record.complaint_entry_id = entry.id if entry else None
        record.chief_complaint = display
        record.normalized_complaint = normalized
        record.complaint_category = entry.category.name if entry and entry.category else None
        record.is_unknown_complaint = is_unknown
        record.status = INTAKE_STATUS_MODIFIED

    if symptom_onset is not None:
        record.symptom_onset = symptom_onset.strip() or None
    if priority is not None:
        record.priority = validate_priority(priority)

    db.session.commit()

    audit_engine.log(
        action="clinical_intake.complaint_modified",
        user=acting_user,
        target_type="ClinicalIntakeRecord",
        target_id=record.id,
        details={
            "encounter_id": encounter.id,
            "previous_complaint": previous,
            "chief_complaint": record.chief_complaint,
            "normalized_complaint": record.normalized_complaint,
        },
    )
    return record


def intake_to_dict(record: ClinicalIntakeRecord) -> dict[str, Any]:
    return {
        "id": record.id,
        "encounter_id": record.encounter_id,
        "patient_id": record.patient_id,
        "complaint_entry_id": record.complaint_entry_id,
        "chief_complaint": record.chief_complaint,
        "normalized_complaint": record.normalized_complaint,
        "complaint_category": record.complaint_category,
        "symptom_onset": record.symptom_onset,
        "priority": record.priority,
        "status": record.status,
        "is_unknown_complaint": record.is_unknown_complaint,
        "created_by_id": record.created_by_id,
        "created_at": record.created_at.isoformat() if record.created_at else None,
        "extension_payload": record.extension_payload,
    }
