"""Patient demographics read adapter — owner: patients module."""

from __future__ import annotations

from app.modules.clinical_data_registry.constants import SOURCE_MODULE_PATIENTS
from app.modules.clinical_data_registry.domain import ClinicalObservationRef
from app.modules.patients.models import Patient


def fetch_patient_field(patient: Patient, field_name: str, *, canonical_code: str) -> ClinicalObservationRef | None:
    value = getattr(patient, field_name, None)
    if value is None:
        return None
    return ClinicalObservationRef(
        ref_id=f"patients:patient:{patient.id}:{field_name}",
        canonical_code=canonical_code,
        patient_id=patient.id,
        encounter_id=None,
        value_numeric=float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else None,
        value_text=str(value),
        unit=None,
        effective_at=patient.updated_at or patient.created_at,
        recorded_at=patient.created_at,
        source_module=SOURCE_MODULE_PATIENTS,
        source_type="patient_field",
        source_key=field_name,
        author_id=patient.created_by_id,
        status="active",
        version=(patient.updated_at or patient.created_at).isoformat(),
        is_latest=True,
    )
