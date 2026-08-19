"""Quality metric result helpers with benchmarking foundation."""

from __future__ import annotations

from typing import Any

from app.modules.analytics.specialty_metrics.calculators import (
    ClinicalMetricResult,
    complete_count,
    complete_rate,
    incomplete_result,
)


def attach_benchmarking(
    result: dict[str, Any],
    *,
    target_value: float | None = None,
    historical_trend: list[dict[str, Any]] | None = None,
    department_comparison: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Add internal benchmarking metadata — no external benchmarking."""
    benchmarking: dict[str, Any] = {}
    value = result.get("value")

    if target_value is not None and isinstance(value, (int, float)):
        benchmarking["target_value"] = target_value
        if value >= target_value:
            benchmarking["target_comparison"] = "met"
        else:
            benchmarking["target_comparison"] = "below_target"
        benchmarking["delta_from_target"] = round(value - target_value, 4)

    if historical_trend is not None:
        benchmarking["historical_trend"] = historical_trend

    if department_comparison is not None:
        benchmarking["department_comparison"] = department_comparison

    if benchmarking:
        result["benchmarking"] = benchmarking
    return result


def with_target_from_config(result: dict[str, Any], config: dict) -> dict[str, Any]:
    target = config.get("target_value")
    if target is not None:
        attach_benchmarking(result, target_value=float(target))
    return result
