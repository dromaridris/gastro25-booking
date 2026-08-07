"""CDR domain objects — read-only observation references with provenance."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class ClinicalObservationRef:
    """Resolved clinical datum with medico-legal provenance."""

    ref_id: str
    canonical_code: str
    patient_id: int
    encounter_id: int | None
    value_numeric: float | None
    value_text: str | None
    unit: str | None
    effective_at: datetime | None
    recorded_at: datetime | None
    source_module: str
    source_type: str
    source_key: str
    author_id: int | None
    status: str
    version: str
    is_latest: bool = False
    abnormal_flag: str | None = None

    @property
    def display_value(self) -> str | None:
        if self.value_numeric is not None:
            numeric = self.value_numeric
            if numeric == int(numeric):
                return str(int(numeric))
            return str(numeric)
        return self.value_text

    def as_dict(self) -> dict[str, Any]:
        return {
            "ref_id": self.ref_id,
            "canonical_code": self.canonical_code,
            "patient_id": self.patient_id,
            "encounter_id": self.encounter_id,
            "value_numeric": self.value_numeric,
            "value_text": self.value_text,
            "unit": self.unit,
            "effective_at": self.effective_at.isoformat() if self.effective_at else None,
            "recorded_at": self.recorded_at.isoformat() if self.recorded_at else None,
            "source_module": self.source_module,
            "source_type": self.source_type,
            "source_key": self.source_key,
            "author_id": self.author_id,
            "status": self.status,
            "version": self.version,
            "is_latest": self.is_latest,
            "abnormal_flag": self.abnormal_flag,
        }


@dataclass(frozen=True)
class TrendResult:
    canonical_code: str
    trend: str
    delta: float | None = None
    previous_value: float | None = None
    latest_value: float | None = None


@dataclass(frozen=True)
class ObservationSeries:
    canonical_code: str
    observations: list[ClinicalObservationRef] = field(default_factory=list)
    latest: ClinicalObservationRef | None = None
    previous: ClinicalObservationRef | None = None
    trend: TrendResult | None = None


@dataclass(frozen=True)
class TimelineEntry:
    occurred_at: datetime
    canonical_code: str
    label: str
    source_module: str
    status: str
    ref_id: str
    trend: str | None = None
    value_summary: str | None = None
