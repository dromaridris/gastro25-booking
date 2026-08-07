"""Patient safety metric calculators — documented events only."""

from __future__ import annotations

from typing import Any

from app.modules.analytics.data_access import AnalyticsFilters
from app.modules.analytics.specialty_metrics.calculators import ClinicalMetricResult, complete_count, incomplete_result

from .calculators import with_target_from_config
from .quality_access import QualityDataAccess

_access = QualityDataAccess()


def safety_adverse_event_tracking(filters: AnalyticsFilters, config: dict) -> dict[str, Any]:
    total, by_category = _access.incident_stats(filters)
    result = ClinicalMetricResult(
        value=total,
        unit="incidents",
        aggregation="count",
        complete=True,
        distribution=by_category,
        source_record_count=total,
        eligible_record_count=total,
        records_with_required_data=total,
        required_fields=["clinical_incidents"],
        notes="Counts documented clinical incidents only — never inferred.",
    ).to_dict()
    return with_target_from_config(result, config)


def safety_complication_reporting(filters: AnalyticsFilters, config: dict) -> dict[str, Any]:
    from .clinical_quality import procedure_complication_reporting_rate

    return procedure_complication_reporting_rate(filters, config)


def safety_incident_documentation(filters: AnalyticsFilters, config: dict) -> dict[str, Any]:
    total, by_category = _access.incident_stats(filters)
    if total == 0:
        return incomplete_result(
            required_fields=["clinical_incidents.description", "clinical_incidents.category"],
            missing_fields=["clinical_incidents"],
            source_record_count=0,
            eligible_record_count=0,
            unit="incidents",
            aggregation="count",
            notes="No documented incidents in period.",
        )
    result = ClinicalMetricResult(
        value=total,
        unit="incidents",
        aggregation="count",
        complete=True,
        distribution=by_category,
        source_record_count=total,
        eligible_record_count=total,
        records_with_required_data=total,
        required_fields=["clinical_incidents.description", "clinical_incidents.category"],
    ).to_dict()
    return with_target_from_config(result, config)


def safety_escalation_tracking(filters: AnalyticsFilters, config: dict) -> dict[str, Any]:
    count = _access.escalation_count(filters)
    result = complete_count(count, source_record_count=count, unit="escalations")
    result["notes"] = "Counts documented follow-up escalations only."
    return with_target_from_config(result, config)
