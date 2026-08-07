"""Observation resolver — canonical and legacy read paths."""

from __future__ import annotations

from app.modules.clinical_data_registry.adapters import history, labs, medications, patient as patient_adapter
from app.modules.clinical_data_registry.canonical_codes import (
    CanonicalCodeDefinition,
    canonical_for_legacy,
    definition_for_canonical,
    definition_for_legacy,
)
from app.modules.clinical_data_registry.constants import (
    SOURCE_TYPE_HISTORY_ANSWER,
    SOURCE_TYPE_HISTORY_DIAGNOSIS,
    SOURCE_TYPE_LAB_RESULT,
    SOURCE_TYPE_MEDICATION,
    SOURCE_TYPE_PATIENT_FIELD,
    TREND_DOWN,
    TREND_STABLE,
    TREND_UNKNOWN,
    TREND_UP,
)
from app.modules.clinical_data_registry.domain import ClinicalObservationRef, ObservationSeries, TrendResult
from app.modules.patients.models import Patient


def _compute_trend(latest: ClinicalObservationRef | None, previous: ClinicalObservationRef | None) -> TrendResult | None:
    if latest is None:
        return None
    if previous is None or latest.value_numeric is None or previous.value_numeric is None:
        return TrendResult(canonical_code=latest.canonical_code, trend=TREND_UNKNOWN)
    delta = latest.value_numeric - previous.value_numeric
    if delta > 0:
        trend = TREND_UP
    elif delta < 0:
        trend = TREND_DOWN
    else:
        trend = TREND_STABLE
    return TrendResult(
        canonical_code=latest.canonical_code,
        trend=trend,
        delta=delta,
        previous_value=previous.value_numeric,
        latest_value=latest.value_numeric,
    )


def _resolve_definition(
    *,
    canonical_code: str | None = None,
    source_type: str | None = None,
    source_key: str | None = None,
) -> CanonicalCodeDefinition | None:
    if canonical_code:
        found = definition_for_canonical(canonical_code)
        if found:
            return found
    if source_type and source_key:
        found = definition_for_legacy(source_type, source_key)
        if found:
            return found
        # Dynamic legacy codes not yet registered canonically.
        if source_type == SOURCE_TYPE_LAB_RESULT:
            return CanonicalCodeDefinition(
                f"lab.legacy.{source_key.replace('.', '_')}",
                "investigations",
                SOURCE_TYPE_LAB_RESULT,
                (source_key,),
            )
        if source_type == SOURCE_TYPE_HISTORY_ANSWER:
            return CanonicalCodeDefinition(
                f"history.answer.{source_key}",
                "clinical_history",
                SOURCE_TYPE_HISTORY_ANSWER,
                (source_key,),
            )
        if source_type == SOURCE_TYPE_HISTORY_DIAGNOSIS:
            return CanonicalCodeDefinition(
                f"diagnosis.{source_key.replace('.', '_')}",
                "clinical_history",
                SOURCE_TYPE_HISTORY_DIAGNOSIS,
                (source_key,),
            )
        if source_type == SOURCE_TYPE_PATIENT_FIELD:
            return CanonicalCodeDefinition(
                f"patient.{source_key}",
                "patients",
                SOURCE_TYPE_PATIENT_FIELD,
                (source_key,),
            )
        if source_type == SOURCE_TYPE_MEDICATION:
            return CanonicalCodeDefinition(
                f"med.{source_key}",
                "medications",
                SOURCE_TYPE_MEDICATION,
                (source_key,),
            )
    return None


def _resolve_lab_series(
    patient_id: int,
    definition: CanonicalCodeDefinition,
    *,
    encounter_id: int | None = None,
    limit: int = 50,
) -> list[ClinicalObservationRef]:
    return labs.fetch_lab_series(patient_id, definition, encounter_id=encounter_id, limit=limit)


def _resolve_single(
    patient: Patient,
    definition: CanonicalCodeDefinition,
    *,
    encounter_id: int | None = None,
    registry_context: dict | None = None,
) -> ClinicalObservationRef | None:
    registry_context = registry_context or {}
    complaint_code = registry_context.get("complaint_code")

    if definition.source_type == SOURCE_TYPE_LAB_RESULT:
        series = _resolve_lab_series(patient.id, definition, encounter_id=encounter_id, limit=1)
        return series[0] if series else None

    if definition.source_type == SOURCE_TYPE_PATIENT_FIELD:
        return patient_adapter.fetch_patient_field(patient, definition.source_keys[0], canonical_code=definition.code)

    if definition.source_type == SOURCE_TYPE_HISTORY_ANSWER:
        return history.fetch_history_answer(
            patient.id,
            definition.source_keys[0],
            canonical_code=definition.code,
            complaint_code=complaint_code,
        )

    if definition.source_type == SOURCE_TYPE_HISTORY_DIAGNOSIS:
        return history.fetch_confirmed_diagnosis(
            patient.id,
            canonical_code=definition.code,
            complaint_code=complaint_code or definition.source_keys[0] or None,
        )

    if definition.source_type == SOURCE_TYPE_MEDICATION:
        return medications.fetch_medication_entry(
            patient.id,
            definition.source_keys[0],
            canonical_code=definition.code,
        )

    return None


class ObservationResolver:
    """Read-only resolver. Owning modules retain write authority."""

    def resolve_latest(
        self,
        patient: Patient,
        *,
        canonical_code: str | None = None,
        source_type: str | None = None,
        source_key: str | None = None,
        encounter_id: int | None = None,
        registry_context: dict | None = None,
    ) -> ClinicalObservationRef | None:
        definition = _resolve_definition(
            canonical_code=canonical_code,
            source_type=source_type,
            source_key=source_key,
        )
        if definition is None:
            return None
        code = definition.code
        ref = _resolve_single(patient, definition, encounter_id=encounter_id, registry_context=registry_context)
        if ref is None:
            return None
        return ClinicalObservationRef(
            ref_id=ref.ref_id,
            canonical_code=code,
            patient_id=ref.patient_id,
            encounter_id=ref.encounter_id,
            value_numeric=ref.value_numeric,
            value_text=ref.value_text,
            unit=ref.unit,
            effective_at=ref.effective_at,
            recorded_at=ref.recorded_at,
            source_module=ref.source_module,
            source_type=ref.source_type,
            source_key=ref.source_key,
            author_id=ref.author_id,
            status=ref.status,
            version=ref.version,
            is_latest=True,
            abnormal_flag=ref.abnormal_flag,
        )

    def resolve_series(
        self,
        patient_id: int,
        canonical_code: str,
        *,
        encounter_id: int | None = None,
        limit: int = 50,
    ) -> ObservationSeries:
        definition = definition_for_canonical(canonical_code)
        if definition is None or definition.source_type != SOURCE_TYPE_LAB_RESULT:
            latest = None
            if definition is not None:
                patient = Patient.query.get(patient_id)
                if patient:
                    latest = self.resolve_latest(patient, canonical_code=canonical_code, encounter_id=encounter_id)
            observations = [latest] if latest else []
            previous = None
        else:
            observations = _resolve_lab_series(patient_id, definition, encounter_id=encounter_id, limit=limit)
            latest = observations[0] if observations else None
            previous = observations[1] if len(observations) > 1 else None

        trend = _compute_trend(latest, previous)
        return ObservationSeries(
            canonical_code=canonical_code,
            observations=observations,
            latest=latest,
            previous=previous,
            trend=trend,
        )

    def resolve_display_value(
        self,
        patient: Patient,
        *,
        canonical_code: str | None = None,
        source_type: str | None = None,
        source_key: str | None = None,
        registry_context: dict | None = None,
    ) -> str | None:
        ref = self.resolve_latest(
            patient,
            canonical_code=canonical_code,
            source_type=source_type,
            source_key=source_key,
            registry_context=registry_context,
        )
        return ref.display_value if ref else None

    def legacy_canonical_code(self, source_type: str, source_key: str) -> str | None:
        return canonical_for_legacy(source_type, source_key)
