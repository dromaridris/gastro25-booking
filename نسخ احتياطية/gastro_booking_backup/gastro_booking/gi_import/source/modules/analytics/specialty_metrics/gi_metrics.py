"""Gastroenterology specialty metric calculators."""

from __future__ import annotations

from typing import Any

from app.modules.analytics.data_access import AnalyticsDataAccess, AnalyticsFilters

from .calculators import ClinicalMetricResult, complete_count, complete_rate, incomplete_result
from .procedure_metrics import (
    ADR_REQUIRED_FIELDS,
    BOWEL_PREP_FIELDS,
    CANNULATION_FIELDS,
    CECAL_INTUBATION_FIELDS,
    ERCP_COMPLICATION_FIELDS,
    ERCP_THERAPY_FIELDS,
    GI_ALL_ENDOSCOPY_KEYS,
    GI_COLONOSCOPY_KEYS,
    GI_ERCP_KEYS,
    GI_UPPER_GI_KEYS,
    INCOMPLETE_COLONoscopy_FIELDS,
    ProcedureAnalyticsAccess,
    ProcedureAnalyticsFilters,
)

_access = ProcedureAnalyticsAccess()
_foundation_access = AnalyticsDataAccess()


def _as_procedure_filters(filters: AnalyticsFilters, **kwargs) -> ProcedureAnalyticsFilters:
    return ProcedureAnalyticsFilters(
        department_id=filters.department_id,
        physician_id=filters.physician_id,
        role_code=filters.role_code,
        procedure_type_id=filters.procedure_type_id,
        diagnosis_category=filters.diagnosis_category,
        date_from=filters.date_from,
        date_to=filters.date_to,
        **kwargs,
    )


def _volume_by_keys(filters: AnalyticsFilters, template_keys: frozenset[str], unit: str = "procedures") -> dict[str, Any]:
    pf = _as_procedure_filters(filters, report_template_keys=template_keys)
    count = _access.count_sessions(pf)
    return complete_count(count, source_record_count=count, unit=unit)


def gi_total_endoscopy_procedures(filters: AnalyticsFilters, _config: dict) -> dict[str, Any]:
    return _volume_by_keys(filters, GI_ALL_ENDOSCOPY_KEYS)


def gi_upper_gi_volume(filters: AnalyticsFilters, _config: dict) -> dict[str, Any]:
    return _volume_by_keys(filters, GI_UPPER_GI_KEYS)


def gi_colonoscopy_volume(filters: AnalyticsFilters, _config: dict) -> dict[str, Any]:
    return _volume_by_keys(filters, GI_COLONOSCOPY_KEYS)


def gi_ercp_volume(filters: AnalyticsFilters, _config: dict) -> dict[str, Any]:
    return _volume_by_keys(filters, GI_ERCP_KEYS)


def gi_diagnostic_procedures(filters: AnalyticsFilters, _config: dict) -> dict[str, Any]:
    pf = _as_procedure_filters(filters, report_template_keys=GI_ALL_ENDOSCOPY_KEYS, diagnostic_only=True)
    count = _access.count_sessions(pf)
    return complete_count(count, source_record_count=count)


def gi_therapeutic_procedures(filters: AnalyticsFilters, _config: dict) -> dict[str, Any]:
    pf = _as_procedure_filters(filters, report_template_keys=GI_ALL_ENDOSCOPY_KEYS, therapeutic_only=True)
    count = _access.count_sessions(pf)
    return complete_count(count, source_record_count=count)


def gi_diagnostic_therapeutic_ratio(filters: AnalyticsFilters, _config: dict) -> dict[str, Any]:
    pf = _as_procedure_filters(filters, report_template_keys=GI_ALL_ENDOSCOPY_KEYS)
    diagnostic, therapeutic = _access.count_diagnostic_therapeutic(pf)
    total = diagnostic + therapeutic
    if total == 0:
        return complete_rate(0, 0, source_record_count=0, eligible_record_count=0, records_with_required_data=0, required_fields=[])
    return complete_rate(
        diagnostic,
        total,
        source_record_count=total,
        eligible_record_count=total,
        records_with_required_data=total,
        required_fields=["procedure_sessions", "clinical_report_documents.payload"],
    )


def gi_colonoscopy_cecal_intubation_rate(filters: AnalyticsFilters, _config: dict) -> dict[str, Any]:
    pf = _as_procedure_filters(filters)
    records = _access.colonoscopy_quality_records(pf)
    if not records:
        return incomplete_result(
            required_fields=CECAL_INTUBATION_FIELDS,
            missing_fields=CECAL_INTUBATION_FIELDS,
            source_record_count=0,
            eligible_record_count=0,
            notes="No structured colonoscopy reports in period.",
        )
    positive, with_data = _access.metric_true_count(records, "caecum_intubation")
    records_with_data, missing = _access.aggregate_missing_fields(records, CECAL_INTUBATION_FIELDS)
    if with_data == 0:
        return incomplete_result(
            required_fields=CECAL_INTUBATION_FIELDS,
            missing_fields=missing or CECAL_INTUBATION_FIELDS,
            source_record_count=len(records),
            eligible_record_count=len(records),
            records_with_required_data=records_with_data,
        )
    return complete_rate(
        positive,
        with_data,
        source_record_count=len(records),
        eligible_record_count=len(records),
        records_with_required_data=records_with_data,
        required_fields=CECAL_INTUBATION_FIELDS,
        calculation_version=1,
    )


def gi_colonoscopy_adenoma_detection_rate(filters: AnalyticsFilters, _config: dict) -> dict[str, Any]:
    pf = _as_procedure_filters(filters)
    records = _access.colonoscopy_quality_records(pf)
    if not records:
        return incomplete_result(
            required_fields=ADR_REQUIRED_FIELDS,
            missing_fields=ADR_REQUIRED_FIELDS,
            source_record_count=0,
            eligible_record_count=0,
            notes="No structured colonoscopy reports in period.",
        )
    records_with_data, missing = _access.aggregate_missing_fields(records, ADR_REQUIRED_FIELDS)
    if records_with_data == 0:
        return incomplete_result(
            required_fields=ADR_REQUIRED_FIELDS,
            missing_fields=missing or ADR_REQUIRED_FIELDS,
            source_record_count=len(records),
            eligible_record_count=len(records),
            records_with_required_data=0,
            notes="Adenoma detection requires structured adenoma documentation — field not fully available.",
        )
    detected = sum(1 for record in records if _access._adenoma_documented(record.payload))
    return complete_rate(
        detected,
        records_with_data,
        source_record_count=len(records),
        eligible_record_count=len(records),
        records_with_required_data=records_with_data,
        required_fields=ADR_REQUIRED_FIELDS,
        calculation_version=1,
    )


def gi_colonoscopy_bowel_prep_distribution(filters: AnalyticsFilters, _config: dict) -> dict[str, Any]:
    pf = _as_procedure_filters(filters)
    records = _access.colonoscopy_quality_records(pf)
    if not records:
        return incomplete_result(
            required_fields=BOWEL_PREP_FIELDS,
            missing_fields=BOWEL_PREP_FIELDS,
            source_record_count=0,
            eligible_record_count=0,
            unit="distribution",
            aggregation="distribution",
        )
    records_with_data, missing = _access.aggregate_missing_fields(records, BOWEL_PREP_FIELDS)
    distribution = _access.bowel_prep_distribution(records)
    result = ClinicalMetricResult(
        value=distribution,
        unit="distribution",
        aggregation="distribution",
        complete=records_with_data > 0,
        incomplete=records_with_data == 0,
        distribution=distribution,
        source_record_count=len(records),
        eligible_record_count=len(records),
        records_with_required_data=records_with_data,
        required_fields=BOWEL_PREP_FIELDS,
        missing_required_fields=missing,
    )
    return result.to_dict()


def gi_colonoscopy_incomplete_rate(filters: AnalyticsFilters, _config: dict) -> dict[str, Any]:
    pf = _as_procedure_filters(filters)
    records = _access.colonoscopy_quality_records(pf)
    if not records:
        return incomplete_result(
            required_fields=INCOMPLETE_COLONoscopy_FIELDS,
            missing_fields=INCOMPLETE_COLONoscopy_FIELDS,
            source_record_count=0,
            eligible_record_count=0,
        )
    completed_true, with_data = _access.metric_true_count(records, "procedure_completed")
    incomplete_count = max(with_data - completed_true, 0) if with_data else 0
    records_with_data, missing = _access.aggregate_missing_fields(records, INCOMPLETE_COLONoscopy_FIELDS)
    if with_data == 0:
        return incomplete_result(
            required_fields=INCOMPLETE_COLONoscopy_FIELDS,
            missing_fields=missing or INCOMPLETE_COLONoscopy_FIELDS,
            source_record_count=len(records),
            eligible_record_count=len(records),
        )
    return complete_rate(
        incomplete_count,
        with_data,
        source_record_count=len(records),
        eligible_record_count=len(records),
        records_with_required_data=records_with_data,
        required_fields=INCOMPLETE_COLONoscopy_FIELDS,
    )


def gi_ercp_cannulation_success_rate(filters: AnalyticsFilters, _config: dict) -> dict[str, Any]:
    pf = _as_procedure_filters(filters)
    records = _access.ercp_records(pf)
    if not records:
        return incomplete_result(
            required_fields=CANNULATION_FIELDS,
            missing_fields=CANNULATION_FIELDS,
            source_record_count=0,
            eligible_record_count=0,
        )
    positive, with_data = _access.metric_true_count(records, "cannulation_success")
    records_with_data, missing = _access.aggregate_missing_fields(records, CANNULATION_FIELDS)
    if with_data == 0:
        return incomplete_result(
            required_fields=CANNULATION_FIELDS,
            missing_fields=missing or CANNULATION_FIELDS,
            source_record_count=len(records),
            eligible_record_count=len(records),
        )
    return complete_rate(
        positive,
        with_data,
        source_record_count=len(records),
        eligible_record_count=len(records),
        records_with_required_data=records_with_data,
        required_fields=CANNULATION_FIELDS,
    )


def gi_ercp_therapeutic_intervention_rate(filters: AnalyticsFilters, _config: dict) -> dict[str, Any]:
    pf = _as_procedure_filters(filters, report_template_keys=GI_ERCP_KEYS, therapeutic_only=True)
    therapeutic = _access.count_sessions(pf)
    pf_all = _as_procedure_filters(filters, report_template_keys=GI_ERCP_KEYS)
    total = _access.count_sessions(pf_all)
    records = _access.ercp_records(_as_procedure_filters(filters))
    records_with_data, missing = _access.aggregate_missing_fields(records, ERCP_THERAPY_FIELDS)
    if total == 0:
        return incomplete_result(
            required_fields=ERCP_THERAPY_FIELDS,
            missing_fields=ERCP_THERAPY_FIELDS,
            source_record_count=0,
            eligible_record_count=0,
        )
    return complete_rate(
        therapeutic,
        total,
        source_record_count=total,
        eligible_record_count=total,
        records_with_required_data=records_with_data,
        required_fields=ERCP_THERAPY_FIELDS,
    )


def gi_ercp_stone_extraction_count(filters: AnalyticsFilters, _config: dict) -> dict[str, Any]:
    records = _access.ercp_records(_as_procedure_filters(filters))
    count = _access.count_interventions(records, "stone_extraction")
    return complete_count(count, source_record_count=len(records), unit="interventions")


def gi_ercp_stent_placement_count(filters: AnalyticsFilters, _config: dict) -> dict[str, Any]:
    records = _access.ercp_records(_as_procedure_filters(filters))
    biliary = _access.count_interventions(records, "biliary_stent")
    pancreatic = _access.count_interventions(records, "pancreatic_stent")
    count = biliary + pancreatic
    return complete_count(count, source_record_count=len(records), unit="interventions")


def gi_ercp_complication_tracking(filters: AnalyticsFilters, _config: dict) -> dict[str, Any]:
    records = _access.ercp_records(_as_procedure_filters(filters))
    if not records:
        return incomplete_result(
            required_fields=ERCP_COMPLICATION_FIELDS,
            missing_fields=ERCP_COMPLICATION_FIELDS,
            source_record_count=0,
            eligible_record_count=0,
            unit="distribution",
            aggregation="distribution",
        )
    records_with_data, missing = _access.aggregate_missing_fields(records, ERCP_COMPLICATION_FIELDS)
    distribution = {
        "post_ercp_pancreatitis": 0,
        "bleeding": 0,
        "perforation": 0,
        "infection": 0,
        "other": 0,
        "none": 0,
    }
    for record in records:
        types = _access._payload_fields(record.payload).get("ercp.closure.complication_types") or []
        if not types:
            immediate = record.metrics.get("immediate_complication") == "True"
            if immediate:
                distribution["other"] += 1
            else:
                distribution["none"] += 1
            continue
        if not isinstance(types, list):
            types = [types]
        mapped = False
        for comp in types:
            code = str(comp).lower()
            if "pancreatitis" in code:
                distribution["post_ercp_pancreatitis"] += 1
                mapped = True
            elif "bleed" in code:
                distribution["bleeding"] += 1
                mapped = True
            elif "perforation" in code:
                distribution["perforation"] += 1
                mapped = True
            elif "infection" in code or "cholangitis" in code:
                distribution["infection"] += 1
                mapped = True
            else:
                distribution["other"] += 1
                mapped = True
        if not mapped:
            distribution["none"] += 1
    result = ClinicalMetricResult(
        value=distribution,
        unit="distribution",
        aggregation="distribution",
        complete=records_with_data > 0,
        incomplete=records_with_data == 0,
        distribution=distribution,
        source_record_count=len(records),
        eligible_record_count=len(records),
        records_with_required_data=records_with_data,
        required_fields=ERCP_COMPLICATION_FIELDS,
        missing_required_fields=missing,
    )
    return result.to_dict()


def gi_procedures_per_physician(filters: AnalyticsFilters, _config: dict) -> dict[str, Any]:
    pf = _as_procedure_filters(filters, report_template_keys=GI_ALL_ENDOSCOPY_KEYS)
    breakdown = _access.procedures_per_physician(pf)
    return ClinicalMetricResult(
        value=len(breakdown),
        unit="physicians",
        aggregation="breakdown",
        complete=True,
        breakdown=breakdown,
        source_record_count=sum(row["procedure_count"] for row in breakdown),
        eligible_record_count=sum(row["procedure_count"] for row in breakdown),
        records_with_required_data=sum(row["procedure_count"] for row in breakdown),
    ).to_dict()


def gi_monthly_procedure_trend(filters: AnalyticsFilters, _config: dict) -> dict[str, Any]:
    pf = _as_procedure_filters(filters, report_template_keys=GI_ALL_ENDOSCOPY_KEYS)
    trend = _access.monthly_session_counts(pf)
    total = sum(row["count"] for row in trend)
    return ClinicalMetricResult(
        value=total,
        unit="procedures",
        aggregation="monthly_trend",
        complete=True,
        breakdown=trend,
        source_record_count=total,
        eligible_record_count=total,
        records_with_required_data=total,
    ).to_dict()


def gi_department_workload(filters: AnalyticsFilters, _config: dict) -> dict[str, Any]:
    pf = _as_procedure_filters(filters, report_template_keys=GI_ALL_ENDOSCOPY_KEYS)
    completed = _access.count_completed_sessions(pf)
    total = _access.count_sessions(pf)
    return ClinicalMetricResult(
        value=total,
        unit="procedures",
        aggregation="workload",
        complete=True,
        numerator=completed,
        denominator=total,
        breakdown=[
            {"label": "completed", "count": completed},
            {"label": "all_sessions", "count": total},
        ],
        source_record_count=total,
        eligible_record_count=total,
        records_with_required_data=total,
    ).to_dict()


def gi_patient_volume_trend(filters: AnalyticsFilters, _config: dict) -> dict[str, Any]:
    pf = _as_procedure_filters(filters, report_template_keys=GI_ALL_ENDOSCOPY_KEYS)
    patients = _access.distinct_patient_count(pf)
    encounters = _foundation_access.count_distinct_patients_with_encounters(filters)
    return ClinicalMetricResult(
        value=patients,
        unit="patients",
        aggregation="distinct_count",
        complete=True,
        breakdown=[
            {"label": "procedure_patients", "count": patients},
            {"label": "encounter_patients", "count": encounters},
        ],
        source_record_count=patients,
        eligible_record_count=patients,
        records_with_required_data=patients,
    ).to_dict()
