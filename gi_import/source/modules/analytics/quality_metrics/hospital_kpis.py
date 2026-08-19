"""Hospital operational KPI calculators."""

from __future__ import annotations

from typing import Any

from app.modules.analytics.data_access import AnalyticsDataAccess, AnalyticsFilters
from app.modules.analytics.specialty_metrics.calculators import ClinicalMetricResult, incomplete_result

from .calculators import attach_benchmarking, with_target_from_config
from .quality_access import QualityDataAccess

_access = QualityDataAccess()
_foundation = AnalyticsDataAccess()


def hospital_patient_volume_trend(filters: AnalyticsFilters, config: dict) -> dict[str, Any]:
    trend = _access.monthly_encounter_counts(filters)
    patients = _foundation.count_distinct_patients_with_encounters(filters)
    result = ClinicalMetricResult(
        value=patients,
        unit="patients",
        aggregation="monthly_trend",
        complete=True,
        breakdown=trend,
        source_record_count=patients,
        eligible_record_count=patients,
        records_with_required_data=patients,
    ).to_dict()
    return attach_benchmarking(result, historical_trend=trend)


def hospital_encounter_workload(filters: AnalyticsFilters, config: dict) -> dict[str, Any]:
    dept_count = _access.count_encounters(filters)
    hospital_count = _access.hospital_encounter_count(filters)
    trend = _access.monthly_encounter_counts(filters)
    result = ClinicalMetricResult(
        value=dept_count,
        unit="encounters",
        aggregation="count",
        complete=True,
        breakdown=trend,
        source_record_count=dept_count,
        eligible_record_count=dept_count,
        records_with_required_data=dept_count,
    ).to_dict()
    return attach_benchmarking(
        result,
        historical_trend=trend,
        department_comparison={
            "department_count": dept_count,
            "hospital_count": hospital_count,
        },
    )


def hospital_procedure_workload(filters: AnalyticsFilters, config: dict) -> dict[str, Any]:
    count = _foundation.count_procedure_sessions(filters)
    trend = _access.monthly_procedure_counts(filters)
    result = ClinicalMetricResult(
        value=count,
        unit="procedures",
        aggregation="monthly_trend",
        complete=True,
        breakdown=trend,
        source_record_count=count,
        eligible_record_count=count,
        records_with_required_data=count,
    ).to_dict()
    return attach_benchmarking(result, historical_trend=trend)


def hospital_waiting_time_foundation(filters: AnalyticsFilters, config: dict) -> dict[str, Any]:
    days, total = _access.waiting_time_days(filters)
    if total == 0:
        return incomplete_result(
            required_fields=["waiting_list_entries.listed_at"],
            missing_fields=["waiting_list_entries.listed_at"],
            source_record_count=0,
            eligible_record_count=0,
            unit="days",
            aggregation="average",
            notes="No active waiting list entries — foundation metric only.",
        )
    average = round(sum(days) / len(days), 2) if days else None
    result = ClinicalMetricResult(
        value=average,
        unit="days",
        aggregation="average",
        complete=average is not None,
        source_record_count=total,
        eligible_record_count=total,
        records_with_required_data=len(days),
        required_fields=["waiting_list_entries.listed_at"],
    ).to_dict()
    return with_target_from_config(result, config)


def hospital_report_turnaround_time(filters: AnalyticsFilters, config: dict) -> dict[str, Any]:
    from .clinical_quality import procedure_report_finalization_time

    return procedure_report_finalization_time(filters, config)


def hospital_documentation_delay(filters: AnalyticsFilters, config: dict) -> dict[str, Any]:
    hours, total = _access.documentation_delay_hours(filters)
    if total == 0:
        return incomplete_result(
            required_fields=["signed_clinical_documents.signed_at", "clinical_encounters.created_at"],
            missing_fields=["signed_clinical_documents.signed_at"],
            source_record_count=0,
            eligible_record_count=0,
            unit="hours",
            aggregation="average",
        )
    average = round(sum(hours) / len(hours), 2) if hours else None
    result = ClinicalMetricResult(
        value=average,
        unit="hours",
        aggregation="average",
        complete=average is not None,
        source_record_count=total,
        eligible_record_count=total,
        records_with_required_data=len(hours),
        required_fields=["signed_clinical_documents.signed_at", "clinical_encounters.created_at"],
    ).to_dict()
    return with_target_from_config(result, config)
