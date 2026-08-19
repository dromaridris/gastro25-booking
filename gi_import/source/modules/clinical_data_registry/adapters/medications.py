"""Medication read adapter — owner: medications module."""

from __future__ import annotations

from datetime import datetime

from app.modules.clinical_data_registry.constants import SOURCE_MODULE_MEDICATIONS
from app.modules.clinical_data_registry.domain import ClinicalObservationRef
from app.modules.medications.models import MedicationEntry


def fetch_medication_entry(
    patient_id: int,
    drug_code: str,
    *,
    canonical_code: str,
) -> ClinicalObservationRef | None:
    row = (
        MedicationEntry.query.filter_by(
            patient_id=patient_id,
            drug_code=drug_code,
            is_archived=False,
        )
        .order_by(MedicationEntry.documented_at.desc())
        .first()
    )
    if row is None:
        return None
    effective = row.started_on
    effective_at = datetime.combine(effective, datetime.min.time()) if effective else row.documented_at
    summary = " | ".join(filter(None, [row.dose_text, row.route, row.frequency_text]))
    return ClinicalObservationRef(
        ref_id=f"medications:medication_entry:{row.id}",
        canonical_code=canonical_code,
        patient_id=patient_id,
        encounter_id=row.encounter_id,
        value_numeric=None,
        value_text=summary or row.drug_code,
        unit=None,
        effective_at=effective_at,
        recorded_at=row.documented_at,
        source_module=SOURCE_MODULE_MEDICATIONS,
        source_type="medication_entry",
        source_key=drug_code,
        author_id=row.documented_by_id or row.created_by_id,
        status=row.status,
        version=(row.updated_at or row.created_at).isoformat(),
        is_latest=True,
    )
