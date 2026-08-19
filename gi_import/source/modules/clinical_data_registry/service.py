"""Clinical Data Registry — public read API."""

from __future__ import annotations

from app.modules.clinical_data_registry.domain import ClinicalObservationRef, ObservationSeries, TimelineEntry
from app.modules.clinical_data_registry.resolver import ObservationResolver
from app.modules.clinical_data_registry.timeline import InvestigationTimelineService
from app.modules.patients.models import Patient


class ClinicalDataRegistry:
    """
    Read-only Single Source of Truth facade.

    Every clinical datum has exactly one owning module. CDR resolves and exposes
    observations with provenance; it never duplicates or writes clinical values.
    """

    def __init__(
        self,
        resolver: ObservationResolver | None = None,
        timeline_service: InvestigationTimelineService | None = None,
    ):
        self._resolver = resolver or ObservationResolver()
        self._timeline = timeline_service or InvestigationTimelineService(self._resolver)

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
        return self._resolver.resolve_latest(
            patient,
            canonical_code=canonical_code,
            source_type=source_type,
            source_key=source_key,
            encounter_id=encounter_id,
            registry_context=registry_context,
        )

    def resolve_series(
        self,
        patient_id: int,
        canonical_code: str,
        *,
        encounter_id: int | None = None,
        limit: int = 50,
    ) -> ObservationSeries:
        return self._resolver.resolve_series(
            patient_id,
            canonical_code,
            encounter_id=encounter_id,
            limit=limit,
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
        return self._resolver.resolve_display_value(
            patient,
            canonical_code=canonical_code,
            source_type=source_type,
            source_key=source_key,
            registry_context=registry_context,
        )

    def patient_timeline(self, patient_id: int, *, limit: int = 200) -> list[TimelineEntry]:
        return self._timeline.build_patient_timeline(patient_id, limit=limit)


_registry: ClinicalDataRegistry | None = None


def get_clinical_data_registry() -> ClinicalDataRegistry:
    global _registry
    if _registry is None:
        _registry = ClinicalDataRegistry()
    return _registry


def set_clinical_data_registry(registry: ClinicalDataRegistry) -> None:
    global _registry
    _registry = registry
