"""Read-only procedure analytics access — reusable across specialties."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from sqlalchemy import func

from app.extensions import db
from app.modules.analytics.data_access import AnalyticsFilters
from app.modules.clinical_reports.models import ClinicalReportDocument, ClinicalReportMetric
from app.modules.procedure_execution.models import OUTCOME_COMPLETED, ProcedureSession
from app.modules.procedures.models import (
    REPORT_TEMPLATE_KEY_COLONOSCOPY,
    REPORT_TEMPLATE_KEY_COLONOSCOPY_V2,
    REPORT_TEMPLATE_KEY_ERCP,
    REPORT_TEMPLATE_KEY_FLEX_SIG_V2,
    REPORT_TEMPLATE_KEY_PROCTOSCOPY_V2,
    REPORT_TEMPLATE_KEY_UPPER_GI,
    REPORT_TEMPLATE_KEY_UPPER_GI_V2,
    Procedure,
    ProcedureType,
)
from app.modules.reports.models import Report, STATUS_FINALIZED, STATUS_LOCKED


GI_UPPER_GI_KEYS = frozenset(
    {REPORT_TEMPLATE_KEY_UPPER_GI, REPORT_TEMPLATE_KEY_UPPER_GI_V2}
)
GI_COLONOSCOPY_KEYS = frozenset(
    {
        REPORT_TEMPLATE_KEY_COLONOSCOPY,
        REPORT_TEMPLATE_KEY_COLONOSCOPY_V2,
        REPORT_TEMPLATE_KEY_FLEX_SIG_V2,
        REPORT_TEMPLATE_KEY_PROCTOSCOPY_V2,
    }
)
GI_ERCP_KEYS = frozenset({REPORT_TEMPLATE_KEY_ERCP})
GI_ALL_ENDOSCOPY_KEYS = GI_UPPER_GI_KEYS | GI_COLONOSCOPY_KEYS | GI_ERCP_KEYS

COLONOSCOPY_STRUCTURED_KEYS = frozenset(
    {REPORT_TEMPLATE_KEY_COLONOSCOPY_V2, REPORT_TEMPLATE_KEY_COLONOSCOPY}
)
ERCP_STRUCTURED_KEYS = GI_ERCP_KEYS

CECAL_INTUBATION_FIELDS = ["clinical_report_metrics.caecum_intubation"]
ADR_REQUIRED_FIELDS = [
    "clinical_report_metrics.caecum_intubation",
    "clinical_report_documents.payload.colonoscopy_v2.findings.adenoma_documented",
]
BOWEL_PREP_FIELDS = [
    "clinical_report_documents.payload.colonoscopy_v2.procedure.bbps_right",
    "clinical_report_documents.payload.colonoscopy_v2.procedure.bbps_transverse",
    "clinical_report_documents.payload.colonoscopy_v2.procedure.bbps_left",
]
INCOMPLETE_COLONoscopy_FIELDS = ["clinical_report_metrics.procedure_completed"]
CANNULATION_FIELDS = ["clinical_report_metrics.cannulation_success"]
ERCP_THERAPY_FIELDS = ["clinical_report_documents.payload.ercp.therapy.interventions"]
ERCP_COMPLICATION_FIELDS = [
    "clinical_report_documents.payload.ercp.closure.immediate_complication",
    "clinical_report_documents.payload.ercp.closure.complication_types",
]


@dataclass
class ProcedureAnalyticsFilters(AnalyticsFilters):
    report_template_keys: frozenset[str] | None = None
    indication_category: str | None = None
    outcome: str | None = None
    complication_type: str | None = None
    therapeutic_only: bool = False
    diagnostic_only: bool = False

    def to_dict(self) -> dict[str, Any]:
        base = super().to_dict()
        base.update(
            {
                "report_template_keys": sorted(self.report_template_keys) if self.report_template_keys else None,
                "indication_category": self.indication_category,
                "outcome": self.outcome,
                "complication_type": self.complication_type,
                "therapeutic_only": self.therapeutic_only,
                "diagnostic_only": self.diagnostic_only,
            }
        )
        return base


@dataclass
class ProcedureRecordView:
    session_id: int
    procedure_id: int
    patient_id: int
    endoscopist_id: int | None
    department_id: int
    created_at: datetime
    report_template_key: str | None
    session_outcome: str | None
    report_id: int | None
    document_id: int | None
    document_template_key: str | None
    payload: dict = field(default_factory=dict)
    metrics: dict[str, str] = field(default_factory=dict)


class ProcedureAnalyticsAccess:
    """Read-only procedure and structured report queries for analytics."""

    def _base_session_query(self, filters: ProcedureAnalyticsFilters):
        query = (
            db.session.query(ProcedureSession, Procedure, ProcedureType, Report, ClinicalReportDocument)
            .join(Procedure, Procedure.id == ProcedureSession.procedure_id)
            .join(ProcedureType, ProcedureType.id == Procedure.procedure_type_id)
            .outerjoin(Report, Report.procedure_session_id == ProcedureSession.id)
            .outerjoin(ClinicalReportDocument, ClinicalReportDocument.report_id == Report.id)
            .filter(ProcedureSession.is_archived.is_(False))
            .filter(Procedure.is_archived.is_(False))
        )
        if filters.department_id is not None:
            query = query.filter(ProcedureSession.department_id == filters.department_id)
        if filters.physician_id is not None:
            query = query.filter(ProcedureSession.endoscopist_id == filters.physician_id)
        if filters.procedure_type_id is not None:
            query = query.filter(Procedure.procedure_type_id == filters.procedure_type_id)
        if filters.date_from is not None:
            query = query.filter(ProcedureSession.created_at >= filters.date_from)
        if filters.date_to is not None:
            query = query.filter(ProcedureSession.created_at <= filters.date_to)
        if filters.report_template_keys:
            query = query.filter(ProcedureType.report_template_key.in_(filters.report_template_keys))
        if filters.outcome is not None:
            query = query.filter(ProcedureSession.outcome == filters.outcome)
        return query

    def fetch_procedure_records(self, filters: ProcedureAnalyticsFilters) -> list[ProcedureRecordView]:
        rows = self._base_session_query(filters).all()
        document_ids = [doc.id for _, _, _, _, doc in rows if doc is not None]
        metrics_by_doc: dict[int, dict[str, str]] = {}
        if document_ids:
            for metric in ClinicalReportMetric.query.filter(
                ClinicalReportMetric.document_id.in_(document_ids)
            ).all():
                metrics_by_doc.setdefault(metric.document_id, {})[metric.metric_key] = metric.metric_value or ""

        records: list[ProcedureRecordView] = []
        for session, procedure, ptype, report, document in rows:
            payload = document.get_payload() if document else {}
            metrics = metrics_by_doc.get(document.id, {}) if document else {}
            if filters.indication_category and not self._matches_indication(payload, filters.indication_category):
                continue
            if filters.complication_type and not self._matches_complication(payload, filters.complication_type):
                continue
            therapeutic = self._has_therapeutic_intervention(document.template_key if document else ptype.report_template_key, payload)
            if filters.therapeutic_only and not therapeutic:
                continue
            if filters.diagnostic_only and therapeutic:
                continue
            records.append(
                ProcedureRecordView(
                    session_id=session.id,
                    procedure_id=procedure.id,
                    patient_id=session.patient_id,
                    endoscopist_id=session.endoscopist_id,
                    department_id=session.department_id,
                    created_at=session.created_at,
                    report_template_key=ptype.report_template_key,
                    session_outcome=session.outcome,
                    report_id=report.id if report else None,
                    document_id=document.id if document else None,
                    document_template_key=document.template_key if document else None,
                    payload=payload,
                    metrics=metrics,
                )
            )
        return records

    def count_sessions(self, filters: ProcedureAnalyticsFilters) -> int:
        return len(self.fetch_procedure_records(filters))

    def count_by_template_keys(self, filters: ProcedureAnalyticsFilters, template_keys: frozenset[str]) -> int:
        scoped = ProcedureAnalyticsFilters(**{**filters.__dict__, "report_template_keys": template_keys})
        return self.count_sessions(scoped)

    def count_diagnostic_therapeutic(self, filters: ProcedureAnalyticsFilters) -> tuple[int, int]:
        records = self.fetch_procedure_records(filters)
        diagnostic = 0
        therapeutic = 0
        for record in records:
            if self._has_therapeutic_intervention(record.document_template_key or record.report_template_key, record.payload):
                therapeutic += 1
            else:
                diagnostic += 1
        return diagnostic, therapeutic

    def monthly_session_counts(self, filters: ProcedureAnalyticsFilters) -> list[dict[str, Any]]:
        records = self.fetch_procedure_records(filters)
        buckets: dict[str, int] = {}
        for record in records:
            key = record.created_at.strftime("%Y-%m")
            buckets[key] = buckets.get(key, 0) + 1
        return [{"month": month, "count": count} for month, count in sorted(buckets.items())]

    def procedures_per_physician(self, filters: ProcedureAnalyticsFilters) -> list[dict[str, Any]]:
        records = self.fetch_procedure_records(filters)
        counts: dict[int | None, int] = {}
        for record in records:
            counts[record.endoscopist_id] = counts.get(record.endoscopist_id, 0) + 1
        return [
            {"physician_id": physician_id, "procedure_count": count}
            for physician_id, count in sorted(counts.items(), key=lambda item: (-item[1], item[0] or 0))
        ]

    def colonoscopy_quality_records(self, filters: ProcedureAnalyticsFilters) -> list[ProcedureRecordView]:
        scoped = ProcedureAnalyticsFilters(
            department_id=filters.department_id,
            physician_id=filters.physician_id,
            role_code=filters.role_code,
            procedure_type_id=filters.procedure_type_id,
            diagnosis_category=filters.diagnosis_category,
            date_from=filters.date_from,
            date_to=filters.date_to,
            report_template_keys=COLONOSCOPY_STRUCTURED_KEYS,
        )
        return [
            record
            for record in self.fetch_procedure_records(scoped)
            if record.document_id is not None
        ]

    def ercp_records(self, filters: ProcedureAnalyticsFilters) -> list[ProcedureRecordView]:
        scoped = ProcedureAnalyticsFilters(
            department_id=filters.department_id,
            physician_id=filters.physician_id,
            role_code=filters.role_code,
            procedure_type_id=filters.procedure_type_id,
            diagnosis_category=filters.diagnosis_category,
            date_from=filters.date_from,
            date_to=filters.date_to,
            report_template_keys=ERCP_STRUCTURED_KEYS,
        )
        return [
            record
            for record in self.fetch_procedure_records(scoped)
            if record.document_id is not None
        ]

    def metric_true_count(self, records: list[ProcedureRecordView], metric_key: str) -> tuple[int, int]:
        eligible = len(records)
        positive = sum(1 for record in records if record.metrics.get(metric_key) == "True")
        with_data = sum(1 for record in records if metric_key in record.metrics)
        return positive, with_data if with_data else eligible

    def _payload_fields(self, payload: dict) -> dict:
        if not payload:
            return {}
        if payload.get("payload_version") == "2" and isinstance(payload.get("fields"), dict):
            return payload["fields"]
        return payload

    def _get_field(self, payload: dict, field_id: str) -> Any:
        fields = self._payload_fields(payload)
        return fields.get(field_id)

    def _has_therapeutic_intervention(self, template_key: str | None, payload: dict) -> bool:
        fields = self._payload_fields(payload)
        if template_key in COLONOSCOPY_STRUCTURED_KEYS:
            interventions = fields.get("colonoscopy_v2.interventions.interventions") or []
            return bool(interventions)
        if template_key in ERCP_STRUCTURED_KEYS:
            interventions = fields.get("ercp.therapy.interventions") or []
            return bool(interventions)
        return False

    def _matches_indication(self, payload: dict, indication_category: str) -> bool:
        fields = self._payload_fields(payload)
        indication = fields.get("colonoscopy_v2.context.indication_category") or fields.get(
            "ercp.context.indication_category"
        )
        if isinstance(indication, list):
            return indication_category in indication
        return indication == indication_category

    def _matches_complication(self, payload: dict, complication_type: str) -> bool:
        fields = self._payload_fields(payload)
        types = fields.get("ercp.closure.complication_types") or []
        if isinstance(types, list):
            return complication_type in types
        return types == complication_type

    def count_interventions(self, records: list[ProcedureRecordView], intervention_type: str) -> int:
        total = 0
        for record in records:
            fields = self._payload_fields(record.payload)
            interventions = fields.get("ercp.therapy.interventions") or []
            if not isinstance(interventions, list):
                continue
            for row in interventions:
                if isinstance(row, dict) and row.get("intervention_type") == intervention_type:
                    total += 1
        return total

    def bowel_prep_distribution(self, records: list[ProcedureRecordView]) -> dict[str, int]:
        distribution: dict[str, int] = {}
        for record in records:
            fields = self._payload_fields(record.payload)
            scores = [
                fields.get("colonoscopy_v2.procedure.bbps_right"),
                fields.get("colonoscopy_v2.procedure.bbps_transverse"),
                fields.get("colonoscopy_v2.procedure.bbps_left"),
            ]
            if not any(scores):
                bucket = "missing"
            else:
                numeric = [int(s) for s in scores if str(s).isdigit()]
                total = sum(numeric) if numeric else 0
                if total >= 8:
                    bucket = "adequate"
                elif total >= 5:
                    bucket = "intermediate"
                else:
                    bucket = "inadequate"
            distribution[bucket] = distribution.get(bucket, 0) + 1
        return distribution

    def has_field_data(self, record: ProcedureRecordView, field_ref: str) -> bool:
        if field_ref.startswith("clinical_report_metrics."):
            metric_key = field_ref.split(".", 1)[1]
            return metric_key in record.metrics
        if field_ref.startswith("clinical_report_documents.payload."):
            field_id = field_ref.split(".", 2)[2]
            value = self._get_field(record.payload, field_id)
            if field_id.endswith("adenoma_documented"):
                return self._adenoma_documented(record.payload)
            return value not in (None, "", [], {})
        return False

    def _adenoma_documented(self, payload: dict) -> bool:
        fields = self._payload_fields(payload)
        for key, value in fields.items():
            if "findings" in key and isinstance(value, str) and "adenoma" in value.lower():
                return True
            if "findings" in key and isinstance(value, list) and value:
                return True
        interventions = fields.get("colonoscopy_v2.interventions.interventions") or []
        for row in interventions:
            if isinstance(row, dict):
                intervention = str(row.get("intervention_type", "")).lower()
                if "polypectomy" in intervention or "emr" in intervention or "esd" in intervention:
                    return True
        return False

    def count_completed_sessions(self, filters: ProcedureAnalyticsFilters) -> int:
        scoped = ProcedureAnalyticsFilters(**{**filters.__dict__, "outcome": OUTCOME_COMPLETED})
        return self.count_sessions(scoped)

    def distinct_patient_count(self, filters: ProcedureAnalyticsFilters) -> int:
        records = self.fetch_procedure_records(filters)
        return len({record.patient_id for record in records})

    def aggregate_missing_fields(
        self, records: list[ProcedureRecordView], required_fields: list[str]
    ) -> tuple[int, list[str]]:
        if not records:
            return 0, list(required_fields)
        with_data = 0
        missing_counts: dict[str, int] = {field: 0 for field in required_fields}
        for record in records:
            record_complete = True
            for field_ref in required_fields:
                if not self.has_field_data(record, field_ref):
                    missing_counts[field_ref] += 1
                    record_complete = False
            if record_complete:
                with_data += 1
        missing = [field for field, count in missing_counts.items() if count > 0]
        return with_data, missing
