"""Analytics query engine — executes metrics with filters and traceability."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from .aggregation import PeriodWindow, resolve_period
from .constants import METRIC_STATUS_ACTIVE, PERIOD_CUSTOM
from .data_access import AnalyticsDataAccess, AnalyticsFilters
from .metrics import run_calculator
from .models import MetricDefinition


class AnalyticsQueryEngine:
    """Runs registered metrics against read-only data sources."""

    def __init__(self) -> None:
        self._data_access = AnalyticsDataAccess()

    def build_filters(
        self,
        *,
        department_id: int | None = None,
        physician_id: int | None = None,
        role_code: str | None = None,
        procedure_type_id: int | None = None,
        diagnosis_category: str | None = None,
        period: PeriodWindow | None = None,
    ) -> AnalyticsFilters:
        return AnalyticsFilters(
            department_id=department_id,
            physician_id=physician_id,
            role_code=role_code,
            procedure_type_id=procedure_type_id,
            diagnosis_category=diagnosis_category,
            date_from=period.start if period else None,
            date_to=period.end if period else None,
        )

    def execute_metric(
        self,
        metric: MetricDefinition,
        *,
        period_type: str = PERIOD_CUSTOM,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        department_id: int | None = None,
        physician_id: int | None = None,
        role_code: str | None = None,
        procedure_type_id: int | None = None,
        diagnosis_category: str | None = None,
    ) -> dict[str, Any]:
        if metric.status != METRIC_STATUS_ACTIVE:
            raise ValueError(f"Metric '{metric.metric_id}' is not active.")

        period = resolve_period(
            period_type,
            date_from=date_from,
            date_to=date_to,
        )
        filters = self.build_filters(
            department_id=department_id,
            physician_id=physician_id,
            role_code=role_code,
            procedure_type_id=procedure_type_id,
            diagnosis_category=diagnosis_category,
            period=period,
        )

        result = run_calculator(metric.metric_id, metric.calculation_logic_ref, filters, metric.config)
        summary = self._data_access.build_summary(filters)

        return {
            "metric_id": metric.metric_id,
            "metric_version": metric.version,
            "period": period.to_dict(),
            "filters": filters.to_dict(),
            "result": result,
            "traceability": {
                "calculation_logic_ref": metric.calculation_logic_ref,
                "data_sources": metric.data_sources,
                "source_counts": {
                    "patients": summary.patients,
                    "encounters": summary.encounters,
                    "procedures": summary.procedures,
                    "follow_up_plans": summary.follow_up_plans,
                    "document_drafts": summary.document_drafts,
                    "signed_documents": summary.signed_documents,
                },
            },
        }
