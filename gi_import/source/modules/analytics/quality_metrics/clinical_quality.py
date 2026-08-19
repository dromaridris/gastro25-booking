"""Clinical quality indicator calculators."""

from __future__ import annotations

from typing import Any

from app.modules.analytics.data_access import AnalyticsDataAccess, AnalyticsFilters
from app.modules.analytics.specialty_metrics.calculators import (
    ClinicalMetricResult,
    complete_count,
    complete_rate,
    incomplete_result,
)

from .calculators import attach_benchmarking, with_target_from_config
from .quality_access import QualityDataAccess

_access = QualityDataAccess()
_foundation = AnalyticsDataAccess()


def patient_follow_up_completion_rate(filters: AnalyticsFilters, config: dict) -> dict[str, Any]:
    total = _access.count_follow_up_plans(filters)
    completed = _access.count_completed_follow_ups(filters)
    if total == 0:
        result = incomplete_result(
            required_fields=["follow_up_plans"],
            missing_fields=["follow_up_plans"],
            source_record_count=0,
            eligible_record_count=0,
            notes="No follow-up plans in period.",
        )
    else:
        result = complete_rate(
            completed,
            total,
            source_record_count=total,
            eligible_record_count=total,
            records_with_required_data=total,
            required_fields=["follow_up_plans.status"],
        )
    return with_target_from_config(result, config)


def patient_documentation_completeness(filters: AnalyticsFilters, config: dict) -> dict[str, Any]:
    complete, total, drafts = _access.documentation_completeness_stats(filters)
    if total == 0:
        return incomplete_result(
            required_fields=["document_sections.is_complete"],
            missing_fields=["document_sections.is_complete"],
            source_record_count=drafts,
            eligible_record_count=0,
            notes="No required document sections in period.",
        )
    result = complete_rate(
        complete,
        total,
        source_record_count=drafts,
        eligible_record_count=total,
        records_with_required_data=complete,
        required_fields=["document_sections.is_complete"],
    )
    return with_target_from_config(result, config)


def patient_pending_encounter_rate(filters: AnalyticsFilters, config: dict) -> dict[str, Any]:
    total = _access.count_encounters(filters)
    open_count = _access.count_open_encounters(filters)
    if total == 0:
        return incomplete_result(
            required_fields=["clinical_encounters.status"],
            missing_fields=["clinical_encounters.status"],
            source_record_count=0,
            eligible_record_count=0,
        )
    result = complete_rate(
        open_count,
        total,
        source_record_count=total,
        eligible_record_count=total,
        records_with_required_data=total,
        required_fields=["clinical_encounters.status"],
    )
    return with_target_from_config(result, config)


def patient_lost_to_follow_up_rate(filters: AnalyticsFilters, config: dict) -> dict[str, Any]:
    total = _access.count_follow_up_plans(filters)
    lost = _access.count_lost_to_follow_up(filters)
    if total == 0:
        return incomplete_result(
            required_fields=["clinical_outcome_records.outcome", "follow_up_plans.status"],
            missing_fields=["follow_up_plans"],
            source_record_count=0,
            eligible_record_count=0,
        )
    result = complete_rate(
        lost,
        total,
        source_record_count=total,
        eligible_record_count=total,
        records_with_required_data=total,
        required_fields=["clinical_outcome_records.outcome", "follow_up_plans.status"],
    )
    return with_target_from_config(result, config)


def procedure_completion_rate(filters: AnalyticsFilters, config: dict) -> dict[str, Any]:
    completed, total = _access.procedure_completion_stats(filters)
    if total == 0:
        return incomplete_result(
            required_fields=["procedure_sessions.outcome"],
            missing_fields=["procedure_sessions.outcome"],
            source_record_count=0,
            eligible_record_count=0,
        )
    result = complete_rate(
        completed,
        total,
        source_record_count=total,
        eligible_record_count=total,
        records_with_required_data=total,
        required_fields=["procedure_sessions.outcome"],
    )
    return with_target_from_config(result, config)


def procedure_complication_reporting_rate(filters: AnalyticsFilters, config: dict) -> dict[str, Any]:
    reported, documented = _access.complication_reporting_stats(filters)
    if documented == 0:
        return incomplete_result(
            required_fields=["clinical_report_metrics.immediate_complication"],
            missing_fields=["clinical_report_metrics.immediate_complication"],
            source_record_count=0,
            eligible_record_count=0,
            notes="No documented complication fields in period.",
        )
    result = complete_rate(
        reported,
        documented,
        source_record_count=documented,
        eligible_record_count=documented,
        records_with_required_data=documented,
        required_fields=["clinical_report_metrics.immediate_complication"],
    )
    return with_target_from_config(result, config)


def procedure_documentation_completeness(filters: AnalyticsFilters, config: dict) -> dict[str, Any]:
    return patient_documentation_completeness(filters, config)


def procedure_report_finalization_time(filters: AnalyticsFilters, config: dict) -> dict[str, Any]:
    hours, total = _access.report_finalization_hours(filters)
    if total == 0:
        return incomplete_result(
            required_fields=["reports.finalized_at"],
            missing_fields=["reports.finalized_at"],
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
        required_fields=["reports.finalized_at"],
        missing_required_fields=[] if hours else ["reports.finalized_at"],
    ).to_dict()
    return with_target_from_config(result, config)


def endoscopy_adr_readiness(filters: AnalyticsFilters, config: dict) -> dict[str, Any]:
    from app.modules.analytics.specialty_metrics import gi_metrics

    return gi_metrics.gi_colonoscopy_adenoma_detection_rate(filters, config)


def endoscopy_cecal_intubation_tracking(filters: AnalyticsFilters, config: dict) -> dict[str, Any]:
    from app.modules.analytics.specialty_metrics import gi_metrics

    return gi_metrics.gi_colonoscopy_cecal_intubation_rate(filters, config)


def endoscopy_bowel_prep_documentation(filters: AnalyticsFilters, config: dict) -> dict[str, Any]:
    from app.modules.analytics.specialty_metrics import gi_metrics

    return gi_metrics.gi_colonoscopy_bowel_prep_quality_distribution(filters, config)


def endoscopy_complication_monitoring(filters: AnalyticsFilters, config: dict) -> dict[str, Any]:
    from app.modules.analytics.specialty_metrics import gi_metrics

    return gi_metrics.gi_ercp_complication_tracking(filters, config)
