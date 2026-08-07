"""Longitudinal investigation timeline — unified read view."""

from __future__ import annotations

from datetime import datetime, time

from app.modules.clinical_data_registry.canonical_codes import CANONICAL_REGISTRY
from app.modules.clinical_data_registry.constants import SOURCE_TYPE_LAB_RESULT
from app.modules.clinical_data_registry.domain import TimelineEntry
from app.modules.clinical_data_registry.resolver import ObservationResolver
from app.modules.investigations.models import ImagingStudy, InvestigationOrder, LabResultSet, LabResultValue


class InvestigationTimelineService:
    def __init__(self, resolver: ObservationResolver | None = None):
        self._resolver = resolver or ObservationResolver()

    def build_patient_timeline(self, patient_id: int, *, limit: int = 200) -> list[TimelineEntry]:
        entries: list[TimelineEntry] = []

        lab_rows = (
            LabResultValue.query.join(LabResultSet, LabResultValue.result_set_id == LabResultSet.id)
            .filter(
                LabResultSet.patient_id == patient_id,
                LabResultValue.is_archived.is_(False),
                LabResultSet.is_archived.is_(False),
            )
            .order_by(LabResultSet.resulted_at.desc().nullslast(), LabResultValue.created_at.desc())
            .limit(limit)
            .all()
        )
        for row in lab_rows:
            result_set = row.result_set
            occurred = result_set.resulted_at or result_set.collected_at or row.created_at
            canonical = self._resolver.legacy_canonical_code(SOURCE_TYPE_LAB_RESULT, row.test_code) or row.test_code
            series = self._resolver.resolve_series(patient_id, canonical) if canonical in CANONICAL_REGISTRY else None
            trend = series.trend.trend if series and series.trend else None
            value = row.text_value if row.numeric_value is None else str(row.numeric_value)
            unit = f" {row.unit}" if row.unit else ""
            entries.append(
                TimelineEntry(
                    occurred_at=occurred,
                    canonical_code=canonical,
                    label=row.test_code,
                    source_module="investigations",
                    status=result_set.status,
                    ref_id=f"investigations:lab_result_value:{row.id}",
                    trend=trend,
                    value_summary=f"{value}{unit}".strip(),
                )
            )

        imaging_rows = (
            ImagingStudy.query.filter_by(patient_id=patient_id, is_archived=False)
            .order_by(ImagingStudy.study_date.desc(), ImagingStudy.created_at.desc())
            .limit(limit)
            .all()
        )
        for row in imaging_rows:
            occurred = datetime.combine(row.study_date, time.min) if row.study_date else row.created_at
            entries.append(
                TimelineEntry(
                    occurred_at=occurred,
                    canonical_code=row.catalogue_item.code if row.catalogue_item else f"img.{row.id}",
                    label=row.catalogue_item.name if row.catalogue_item else "Imaging study",
                    source_module="investigations",
                    status=row.status,
                    ref_id=f"investigations:imaging_study:{row.id}",
                    value_summary=row.impression or row.findings_summary,
                )
            )

        orders = (
            InvestigationOrder.query.filter_by(patient_id=patient_id, is_archived=False)
            .order_by(InvestigationOrder.ordered_at.desc())
            .limit(limit)
            .all()
        )
        for order in orders:
            entries.append(
                TimelineEntry(
                    occurred_at=order.ordered_at,
                    canonical_code=f"order.{order.order_kind}",
                    label=f"{order.order_kind.title()} order",
                    source_module="investigations",
                    status=order.status,
                    ref_id=f"investigations:investigation_order:{order.id}",
                    value_summary=order.clinical_indication,
                )
            )

        entries.sort(key=lambda e: e.occurred_at, reverse=True)
        return entries[:limit]
