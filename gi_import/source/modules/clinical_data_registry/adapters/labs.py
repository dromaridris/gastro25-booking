"""Laboratory result read adapter — owner: investigations module."""

from __future__ import annotations

from datetime import datetime

from app.modules.clinical_data_registry.canonical_codes import CanonicalCodeDefinition
from app.modules.clinical_data_registry.constants import SOURCE_MODULE_INVESTIGATIONS, SOURCE_TYPE_LAB_RESULT
from app.modules.clinical_data_registry.domain import ClinicalObservationRef
from app.modules.investigations.models import LabResultSet, LabResultValue


def _effective_at(result_set: LabResultSet) -> datetime | None:
    return result_set.resulted_at or result_set.collected_at or result_set.created_at


def _to_ref(
    row: LabResultValue,
    result_set: LabResultSet,
    *,
    canonical_code: str,
    is_latest: bool,
) -> ClinicalObservationRef:
    numeric = float(row.numeric_value) if row.numeric_value is not None else None
    return ClinicalObservationRef(
        ref_id=f"investigations:lab_result_value:{row.id}",
        canonical_code=canonical_code,
        patient_id=result_set.patient_id,
        encounter_id=result_set.encounter_id,
        value_numeric=numeric,
        value_text=row.text_value,
        unit=row.unit,
        effective_at=_effective_at(result_set),
        recorded_at=row.created_at,
        source_module=SOURCE_MODULE_INVESTIGATIONS,
        source_type=SOURCE_TYPE_LAB_RESULT,
        source_key=row.test_code,
        author_id=row.created_by_id or result_set.created_by_id,
        status=result_set.status,
        version=(row.updated_at or row.created_at).isoformat(),
        is_latest=is_latest,
        abnormal_flag=row.abnormal_flag,
    )


def fetch_lab_series(
    patient_id: int,
    definition: CanonicalCodeDefinition,
    *,
    encounter_id: int | None = None,
    limit: int = 50,
) -> list[ClinicalObservationRef]:
    query = (
        LabResultValue.query.join(LabResultSet, LabResultValue.result_set_id == LabResultSet.id)
        .filter(
            LabResultSet.patient_id == patient_id,
            LabResultValue.test_code.in_(definition.source_keys),
            LabResultValue.is_archived.is_(False),
            LabResultSet.is_archived.is_(False),
        )
    )
    if encounter_id is not None:
        query = query.filter(LabResultSet.encounter_id == encounter_id)
    rows = query.order_by(LabResultSet.resulted_at.desc().nullslast(), LabResultValue.created_at.desc()).limit(limit).all()
    refs: list[ClinicalObservationRef] = []
    for idx, row in enumerate(rows):
        refs.append(
            _to_ref(
                row,
                row.result_set,
                canonical_code=definition.code,
                is_latest=idx == 0,
            )
        )
    return refs
