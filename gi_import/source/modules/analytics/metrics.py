"""Metric calculation registry — foundation metrics only."""

from __future__ import annotations

from typing import Any, Callable

from .constants import (
    CATEGORY_COMPLETION,
    CATEGORY_VOLUME,
    METRIC_DOCUMENT_COMPLETION_RATE,
    METRIC_ENCOUNTER_COUNT,
    METRIC_FOLLOW_UP_COMPLETION_RATE,
    METRIC_PATIENT_VOLUME,
    METRIC_PROCEDURE_COUNT,
)
from .data_access import AnalyticsDataAccess, AnalyticsFilters

MetricCalculator = Callable[[AnalyticsFilters, dict], dict[str, Any]]

_data_access = AnalyticsDataAccess()


def _patient_volume(filters: AnalyticsFilters, _config: dict) -> dict[str, Any]:
    count = _data_access.count_distinct_patients_with_encounters(filters)
    return {"value": count, "unit": "patients", "aggregation": "distinct_count"}


def _encounter_count(filters: AnalyticsFilters, _config: dict) -> dict[str, Any]:
    count = _data_access.count_encounters(filters)
    return {"value": count, "unit": "encounters", "aggregation": "count"}


def _procedure_count(filters: AnalyticsFilters, _config: dict) -> dict[str, Any]:
    count = _data_access.count_procedure_sessions(filters)
    return {"value": count, "unit": "procedures", "aggregation": "count"}


def _follow_up_completion_rate(filters: AnalyticsFilters, _config: dict) -> dict[str, Any]:
    total = _data_access.count_follow_up_plans(filters)
    completed = _data_access.count_follow_up_plans(filters, completed_only=True)
    rate = round(completed / total, 4) if total else 0.0
    return {
        "value": rate,
        "unit": "ratio",
        "aggregation": "rate",
        "numerator": completed,
        "denominator": total,
    }


def _document_completion_rate(filters: AnalyticsFilters, _config: dict) -> dict[str, Any]:
    drafts = _data_access.count_document_drafts(filters)
    signed = _data_access.count_signed_documents(filters)
    rate = round(signed / drafts, 4) if drafts else 0.0
    return {
        "value": rate,
        "unit": "ratio",
        "aggregation": "rate",
        "numerator": signed,
        "denominator": drafts,
    }


METRIC_CALCULATORS: dict[str, MetricCalculator] = {
    METRIC_PATIENT_VOLUME: _patient_volume,
    METRIC_ENCOUNTER_COUNT: _encounter_count,
    METRIC_PROCEDURE_COUNT: _procedure_count,
    METRIC_FOLLOW_UP_COMPLETION_RATE: _follow_up_completion_rate,
    METRIC_DOCUMENT_COMPLETION_RATE: _document_completion_rate,
}


BUILTIN_METRIC_DEFINITIONS: list[dict] = [
    {
        "metric_id": METRIC_PATIENT_VOLUME,
        "name": "Patient Volume",
        "description": "Distinct patients with encounters in the selected period.",
        "category": CATEGORY_VOLUME,
        "calculation_logic_ref": "metrics._patient_volume",
        "data_sources": ["patients", "encounters"],
    },
    {
        "metric_id": METRIC_ENCOUNTER_COUNT,
        "name": "Encounter Count",
        "description": "Total clinical encounters in the selected period.",
        "category": CATEGORY_VOLUME,
        "calculation_logic_ref": "metrics._encounter_count",
        "data_sources": ["encounters"],
    },
    {
        "metric_id": METRIC_PROCEDURE_COUNT,
        "name": "Procedure Count",
        "description": "Total procedure execution sessions in the selected period.",
        "category": CATEGORY_VOLUME,
        "calculation_logic_ref": "metrics._procedure_count",
        "data_sources": ["procedure_execution", "procedures"],
    },
    {
        "metric_id": METRIC_FOLLOW_UP_COMPLETION_RATE,
        "name": "Follow-up Completion Rate",
        "description": "Ratio of completed follow-up plans to total follow-up plans.",
        "category": CATEGORY_COMPLETION,
        "calculation_logic_ref": "metrics._follow_up_completion_rate",
        "data_sources": ["patient_journey"],
    },
    {
        "metric_id": METRIC_DOCUMENT_COMPLETION_RATE,
        "name": "Document Completion Rate",
        "description": "Ratio of signed clinical documents to total document drafts.",
        "category": CATEGORY_COMPLETION,
        "calculation_logic_ref": "metrics._document_completion_rate",
        "data_sources": ["documentation_ai"],
    },
]


def get_calculator(logic_ref: str) -> MetricCalculator | None:
    """Resolve calculator from logic reference or metric_id alias."""
    from .quality_metrics.registry import get_quality_calculator
    from .specialty_metrics.registry import get_specialty_calculator

    quality_calc = get_quality_calculator(logic_ref)
    if quality_calc is not None:
        return quality_calc

    specialty_calc = get_specialty_calculator(logic_ref)
    if specialty_calc is not None:
        return specialty_calc
    if logic_ref in METRIC_CALCULATORS:
        return METRIC_CALCULATORS[logic_ref]
    suffix = logic_ref.rsplit(".", 1)[-1]
    quality_calc = get_quality_calculator(suffix)
    if quality_calc is not None:
        return quality_calc
    specialty_calc = get_specialty_calculator(suffix)
    if specialty_calc is not None:
        return specialty_calc
    for metric_id, calc in METRIC_CALCULATORS.items():
        if metric_id == suffix or calc.__name__ == suffix:
            return calc
    return None


def run_calculator(metric_id: str, logic_ref: str, filters: AnalyticsFilters, config: dict) -> dict[str, Any]:
    calculator = get_calculator(logic_ref) or get_calculator(metric_id)
    if calculator is None:
        raise ValueError(f"No calculator registered for metric '{metric_id}'")
    return calculator(filters, config)
