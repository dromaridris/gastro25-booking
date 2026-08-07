"""Clinical metric result builder with data quality reporting."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ClinicalMetricResult:
    value: Any = None
    unit: str = "count"
    aggregation: str = "count"
    complete: bool = True
    incomplete: bool = False
    numerator: int | float | None = None
    denominator: int | float | None = None
    distribution: dict[str, int] | None = None
    breakdown: list[dict[str, Any]] | None = None
    source_record_count: int = 0
    eligible_record_count: int = 0
    records_with_required_data: int = 0
    required_fields: list[str] = field(default_factory=list)
    missing_required_fields: list[str] = field(default_factory=list)
    calculation_version: int = 1
    notes: str | None = None

    def to_dict(self) -> dict[str, Any]:
        completeness = 0.0
        if self.eligible_record_count:
            completeness = round(
                (self.records_with_required_data / self.eligible_record_count) * 100, 2
            )
        elif self.complete and self.value is not None:
            completeness = 100.0

        payload: dict[str, Any] = {
            "value": self.value,
            "unit": self.unit,
            "aggregation": self.aggregation,
            "complete": self.complete,
            "incomplete": self.incomplete,
            "data_quality": {
                "source_record_count": self.source_record_count,
                "eligible_record_count": self.eligible_record_count,
                "records_with_required_data": self.records_with_required_data,
                "completeness_percentage": completeness,
                "missing_required_fields": list(self.missing_required_fields),
                "required_fields": list(self.required_fields),
                "calculation_version": self.calculation_version,
            },
        }
        if self.numerator is not None:
            payload["numerator"] = self.numerator
        if self.denominator is not None:
            payload["denominator"] = self.denominator
        if self.distribution is not None:
            payload["distribution"] = self.distribution
        if self.breakdown is not None:
            payload["breakdown"] = self.breakdown
        if self.notes:
            payload["notes"] = self.notes
        return payload


def incomplete_result(
    *,
    required_fields: list[str],
    missing_fields: list[str],
    source_record_count: int = 0,
    eligible_record_count: int = 0,
    records_with_required_data: int = 0,
    unit: str = "ratio",
    aggregation: str = "rate",
    calculation_version: int = 1,
    notes: str | None = None,
) -> dict[str, Any]:
    """Return a metric result marked incomplete — never infer missing values."""
    return ClinicalMetricResult(
        value=None,
        unit=unit,
        aggregation=aggregation,
        complete=False,
        incomplete=True,
        source_record_count=source_record_count,
        eligible_record_count=eligible_record_count,
        records_with_required_data=records_with_required_data,
        required_fields=required_fields,
        missing_required_fields=missing_fields,
        calculation_version=calculation_version,
        notes=notes or "Required data fields unavailable — metric not calculated.",
    ).to_dict()


def complete_count(value: int, *, source_record_count: int, unit: str = "procedures") -> dict[str, Any]:
    return ClinicalMetricResult(
        value=value,
        unit=unit,
        aggregation="count",
        complete=True,
        source_record_count=source_record_count,
        eligible_record_count=source_record_count,
        records_with_required_data=source_record_count,
    ).to_dict()


def complete_rate(
    numerator: int,
    denominator: int,
    *,
    source_record_count: int,
    eligible_record_count: int,
    records_with_required_data: int,
    required_fields: list[str],
    calculation_version: int = 1,
) -> dict[str, Any]:
    rate = round(numerator / denominator, 4) if denominator else None
    missing = [] if records_with_required_data == eligible_record_count else required_fields
    return ClinicalMetricResult(
        value=rate,
        unit="ratio",
        aggregation="rate",
        complete=rate is not None and not missing,
        incomplete=rate is None or bool(missing),
        numerator=numerator,
        denominator=denominator,
        source_record_count=source_record_count,
        eligible_record_count=eligible_record_count,
        records_with_required_data=records_with_required_data,
        required_fields=required_fields,
        missing_required_fields=missing,
        calculation_version=calculation_version,
    ).to_dict()
