"""Quality metric registry — registers calculators and seeds definitions."""

from __future__ import annotations

from typing import Any, Callable

from app.extensions import db
from app.modules.analytics.constants import METRIC_STATUS_ACTIVE
from app.modules.analytics.data_access import AnalyticsFilters
from app.modules.analytics.models import MetricDefinition

from . import clinical_quality, hospital_kpis, safety_metrics
from .quality_models import SCOPE_DEPARTMENT, SCOPE_HOSPITAL, SCOPE_SPECIALTY, QualityMetricDefinition

SPECIALTY_GASTROENTEROLOGY = "gastroenterology"

CATEGORY_PATIENT_CARE = "patient_care"
CATEGORY_PROCEDURE_QUALITY = "procedure_quality"
CATEGORY_ENDOSCOPY_QUALITY = "endoscopy_quality"
CATEGORY_HOSPITAL_OPERATIONAL = "hospital_operational"
CATEGORY_PATIENT_SAFETY = "patient_safety"

QualityCalculator = Callable[[AnalyticsFilters, dict], dict[str, Any]]

QUALITY_CALCULATORS: dict[str, QualityCalculator] = {}


def _register(metric_id: str, calculator: QualityCalculator) -> None:
    QUALITY_CALCULATORS[metric_id] = calculator


def register_quality_calculators() -> None:
    mapping = {
        "quality.patient.follow_up_completion_rate": clinical_quality.patient_follow_up_completion_rate,
        "quality.patient.documentation_completeness": clinical_quality.patient_documentation_completeness,
        "quality.patient.pending_encounter_rate": clinical_quality.patient_pending_encounter_rate,
        "quality.patient.lost_to_follow_up_rate": clinical_quality.patient_lost_to_follow_up_rate,
        "quality.procedure.completion_rate": clinical_quality.procedure_completion_rate,
        "quality.procedure.complication_reporting_rate": clinical_quality.procedure_complication_reporting_rate,
        "quality.procedure.documentation_completeness": clinical_quality.procedure_documentation_completeness,
        "quality.procedure.report_finalization_time": clinical_quality.procedure_report_finalization_time,
        "quality.endoscopy.adr_readiness": clinical_quality.endoscopy_adr_readiness,
        "quality.endoscopy.cecal_intubation_tracking": clinical_quality.endoscopy_cecal_intubation_tracking,
        "quality.endoscopy.bowel_prep_documentation": clinical_quality.endoscopy_bowel_prep_documentation,
        "quality.endoscopy.complication_monitoring": clinical_quality.endoscopy_complication_monitoring,
        "kpi.hospital.patient_volume_trend": hospital_kpis.hospital_patient_volume_trend,
        "kpi.hospital.encounter_workload": hospital_kpis.hospital_encounter_workload,
        "kpi.hospital.procedure_workload": hospital_kpis.hospital_procedure_workload,
        "kpi.hospital.waiting_time_foundation": hospital_kpis.hospital_waiting_time_foundation,
        "kpi.hospital.report_turnaround_time": hospital_kpis.hospital_report_turnaround_time,
        "kpi.hospital.documentation_delay": hospital_kpis.hospital_documentation_delay,
        "quality.safety.adverse_event_tracking": safety_metrics.safety_adverse_event_tracking,
        "quality.safety.complication_reporting": safety_metrics.safety_complication_reporting,
        "quality.safety.incident_documentation": safety_metrics.safety_incident_documentation,
        "quality.safety.escalation_tracking": safety_metrics.safety_escalation_tracking,
    }
    for metric_id, calculator in mapping.items():
        _register(metric_id, calculator)


QUALITY_METRIC_DEFINITIONS: list[dict] = [
    {
        "metric_id": "quality.patient.follow_up_completion_rate",
        "name": "Follow-up Completion Rate",
        "category": CATEGORY_PATIENT_CARE,
        "scope_level": SCOPE_DEPARTMENT,
        "description": "Ratio of completed follow-up plans to total follow-up plans.",
        "calculation_reference": "clinical_quality.patient_follow_up_completion_rate",
        "required_data_sources": ["patient_journey"],
        "target_value": 0.85,
    },
    {
        "metric_id": "quality.patient.documentation_completeness",
        "name": "Documentation Completeness",
        "category": CATEGORY_PATIENT_CARE,
        "scope_level": SCOPE_DEPARTMENT,
        "description": "Ratio of complete required document sections to total required sections.",
        "calculation_reference": "clinical_quality.patient_documentation_completeness",
        "required_data_sources": ["documentation_ai"],
        "target_value": 0.9,
    },
    {
        "metric_id": "quality.patient.pending_encounter_rate",
        "name": "Pending Encounter Rate",
        "category": CATEGORY_PATIENT_CARE,
        "scope_level": SCOPE_DEPARTMENT,
        "description": "Ratio of open encounters to total encounters.",
        "calculation_reference": "clinical_quality.patient_pending_encounter_rate",
        "required_data_sources": ["encounters"],
    },
    {
        "metric_id": "quality.patient.lost_to_follow_up_rate",
        "name": "Lost-to-Follow-up Rate",
        "category": CATEGORY_PATIENT_CARE,
        "scope_level": SCOPE_DEPARTMENT,
        "description": "Ratio of lost or missed follow-up cases to total follow-up plans.",
        "calculation_reference": "clinical_quality.patient_lost_to_follow_up_rate",
        "required_data_sources": ["patient_journey"],
    },
    {
        "metric_id": "quality.procedure.completion_rate",
        "name": "Procedure Completion Rate",
        "category": CATEGORY_PROCEDURE_QUALITY,
        "scope_level": SCOPE_DEPARTMENT,
        "description": "Ratio of completed procedure sessions to total sessions.",
        "calculation_reference": "clinical_quality.procedure_completion_rate",
        "required_data_sources": ["procedure_execution"],
        "target_value": 0.95,
    },
    {
        "metric_id": "quality.procedure.complication_reporting_rate",
        "name": "Complication Reporting Rate",
        "category": CATEGORY_PROCEDURE_QUALITY,
        "scope_level": SCOPE_DEPARTMENT,
        "description": "Ratio of documented complications to structured reports with complication fields.",
        "calculation_reference": "clinical_quality.procedure_complication_reporting_rate",
        "required_data_sources": ["clinical_reports", "clinical_report_metrics"],
    },
    {
        "metric_id": "quality.procedure.documentation_completeness",
        "name": "Procedure Documentation Completeness",
        "category": CATEGORY_PROCEDURE_QUALITY,
        "scope_level": SCOPE_DEPARTMENT,
        "description": "Documentation section completeness for clinical documents.",
        "calculation_reference": "clinical_quality.procedure_documentation_completeness",
        "required_data_sources": ["documentation_ai"],
    },
    {
        "metric_id": "quality.procedure.report_finalization_time",
        "name": "Report Finalization Time",
        "category": CATEGORY_PROCEDURE_QUALITY,
        "scope_level": SCOPE_DEPARTMENT,
        "description": "Average hours from report creation to finalization.",
        "calculation_reference": "clinical_quality.procedure_report_finalization_time",
        "required_data_sources": ["reports"],
    },
    {
        "metric_id": "quality.endoscopy.adr_readiness",
        "name": "ADR Tracking Readiness",
        "category": CATEGORY_ENDOSCOPY_QUALITY,
        "scope_level": SCOPE_SPECIALTY,
        "specialty": SPECIALTY_GASTROENTEROLOGY,
        "description": "Foundation adenoma detection readiness — incomplete when required fields unavailable.",
        "calculation_reference": "clinical_quality.endoscopy_adr_readiness",
        "required_data_sources": ["clinical_reports", "specialty_metrics"],
    },
    {
        "metric_id": "quality.endoscopy.cecal_intubation_tracking",
        "name": "Cecal Intubation Quality Tracking",
        "category": CATEGORY_ENDOSCOPY_QUALITY,
        "scope_level": SCOPE_SPECIALTY,
        "specialty": SPECIALTY_GASTROENTEROLOGY,
        "description": "Cecal intubation quality tracking from structured colonoscopy reports.",
        "calculation_reference": "clinical_quality.endoscopy_cecal_intubation_tracking",
        "required_data_sources": ["clinical_reports", "specialty_metrics"],
    },
    {
        "metric_id": "quality.endoscopy.bowel_prep_documentation",
        "name": "Bowel Preparation Documentation",
        "category": CATEGORY_ENDOSCOPY_QUALITY,
        "scope_level": SCOPE_SPECIALTY,
        "specialty": SPECIALTY_GASTROENTEROLOGY,
        "description": "Bowel preparation documentation distribution from structured reports.",
        "calculation_reference": "clinical_quality.endoscopy_bowel_prep_documentation",
        "required_data_sources": ["clinical_reports"],
    },
    {
        "metric_id": "quality.endoscopy.complication_monitoring",
        "name": "Endoscopy Complication Monitoring",
        "category": CATEGORY_ENDOSCOPY_QUALITY,
        "scope_level": SCOPE_SPECIALTY,
        "specialty": SPECIALTY_GASTROENTEROLOGY,
        "description": "Documented endoscopy complication distribution.",
        "calculation_reference": "clinical_quality.endoscopy_complication_monitoring",
        "required_data_sources": ["clinical_reports", "specialty_metrics"],
    },
    {
        "metric_id": "kpi.hospital.patient_volume_trend",
        "name": "Patient Volume Trend",
        "category": CATEGORY_HOSPITAL_OPERATIONAL,
        "scope_level": SCOPE_HOSPITAL,
        "description": "Distinct patient volume with monthly encounter trend.",
        "calculation_reference": "hospital_kpis.hospital_patient_volume_trend",
        "required_data_sources": ["patients", "encounters"],
    },
    {
        "metric_id": "kpi.hospital.encounter_workload",
        "name": "Encounter Workload",
        "category": CATEGORY_HOSPITAL_OPERATIONAL,
        "scope_level": SCOPE_HOSPITAL,
        "description": "Department encounter workload with hospital comparison.",
        "calculation_reference": "hospital_kpis.hospital_encounter_workload",
        "required_data_sources": ["encounters"],
    },
    {
        "metric_id": "kpi.hospital.procedure_workload",
        "name": "Procedure Workload",
        "category": CATEGORY_HOSPITAL_OPERATIONAL,
        "scope_level": SCOPE_HOSPITAL,
        "description": "Procedure session workload with monthly trend.",
        "calculation_reference": "hospital_kpis.hospital_procedure_workload",
        "required_data_sources": ["procedure_execution"],
    },
    {
        "metric_id": "kpi.hospital.waiting_time_foundation",
        "name": "Waiting Time Foundation",
        "category": CATEGORY_HOSPITAL_OPERATIONAL,
        "scope_level": SCOPE_HOSPITAL,
        "description": "Average waiting list duration for active entries — foundation metric.",
        "calculation_reference": "hospital_kpis.hospital_waiting_time_foundation",
        "required_data_sources": ["dept_ops"],
    },
    {
        "metric_id": "kpi.hospital.report_turnaround_time",
        "name": "Report Turnaround Time",
        "category": CATEGORY_HOSPITAL_OPERATIONAL,
        "scope_level": SCOPE_HOSPITAL,
        "description": "Average report finalization turnaround in hours.",
        "calculation_reference": "hospital_kpis.hospital_report_turnaround_time",
        "required_data_sources": ["reports"],
    },
    {
        "metric_id": "kpi.hospital.documentation_delay",
        "name": "Documentation Delay",
        "category": CATEGORY_HOSPITAL_OPERATIONAL,
        "scope_level": SCOPE_HOSPITAL,
        "description": "Average hours from encounter creation to signed clinical document.",
        "calculation_reference": "hospital_kpis.hospital_documentation_delay",
        "required_data_sources": ["documentation_ai", "encounters"],
    },
    {
        "metric_id": "quality.safety.adverse_event_tracking",
        "name": "Adverse Event Tracking",
        "category": CATEGORY_PATIENT_SAFETY,
        "scope_level": SCOPE_HOSPITAL,
        "description": "Count of documented clinical incidents by category.",
        "calculation_reference": "safety_metrics.safety_adverse_event_tracking",
        "required_data_sources": ["clinical_governance"],
    },
    {
        "metric_id": "quality.safety.complication_reporting",
        "name": "Complication Reporting",
        "category": CATEGORY_PATIENT_SAFETY,
        "scope_level": SCOPE_DEPARTMENT,
        "description": "Documented complication reporting rate from structured reports.",
        "calculation_reference": "safety_metrics.safety_complication_reporting",
        "required_data_sources": ["clinical_reports"],
    },
    {
        "metric_id": "quality.safety.incident_documentation",
        "name": "Incident Documentation",
        "category": CATEGORY_PATIENT_SAFETY,
        "scope_level": SCOPE_HOSPITAL,
        "description": "Documented clinical incident count in period.",
        "calculation_reference": "safety_metrics.safety_incident_documentation",
        "required_data_sources": ["clinical_governance"],
    },
    {
        "metric_id": "quality.safety.escalation_tracking",
        "name": "Escalation Tracking",
        "category": CATEGORY_PATIENT_SAFETY,
        "scope_level": SCOPE_DEPARTMENT,
        "description": "Documented follow-up escalations only.",
        "calculation_reference": "safety_metrics.safety_escalation_tracking",
        "required_data_sources": ["patient_journey"],
    },
]


def get_quality_calculator(metric_id_or_ref: str) -> QualityCalculator | None:
    if metric_id_or_ref in QUALITY_CALCULATORS:
        return QUALITY_CALCULATORS[metric_id_or_ref]
    suffix = metric_id_or_ref.rsplit(".", 1)[-1]
    for metric_id, calculator in QUALITY_CALCULATORS.items():
        if metric_id.endswith(suffix) or calculator.__name__ == suffix:
            return calculator
    return None


def seed_quality_metrics_if_empty() -> int:
    created = 0
    for spec in QUALITY_METRIC_DEFINITIONS:
        if QualityMetricDefinition.query.filter_by(metric_id=spec["metric_id"]).first():
            continue

        metric = MetricDefinition.query.filter_by(metric_id=spec["metric_id"]).first()
        if metric is None:
            metric = MetricDefinition(
                metric_id=spec["metric_id"],
                name=spec["name"],
                description=spec.get("description"),
                category=spec["category"],
                calculation_logic_ref=spec["calculation_reference"],
                status=METRIC_STATUS_ACTIVE,
                version=1,
            )
            metric.data_sources = spec.get("required_data_sources", [])
            if spec.get("target_value") is not None:
                metric.config = {"target_value": spec["target_value"]}
            db.session.add(metric)
            db.session.flush()
        else:
            metric.name = spec["name"]
            metric.description = spec.get("description")
            metric.category = spec["category"]
            metric.calculation_logic_ref = spec["calculation_reference"]
            metric.data_sources = spec.get("required_data_sources", [])

        quality = QualityMetricDefinition(
            metric_id=spec["metric_id"],
            metric_definition_id=metric.id,
            name=spec["name"],
            category=spec["category"],
            scope_level=spec.get("scope_level", SCOPE_DEPARTMENT),
            specialty=spec.get("specialty"),
            description=spec.get("description"),
            calculation_reference=spec["calculation_reference"],
            target_value=spec.get("target_value"),
            status=METRIC_STATUS_ACTIVE,
            version=1,
        )
        quality.required_data_sources = spec.get("required_data_sources", [])
        quality.configuration = spec.get("configuration", {})
        db.session.add(quality)
        created += 1

    if created:
        db.session.commit()
    return created


def ensure_quality_metrics_seeded() -> int:
    return seed_quality_metrics_if_empty()


def list_quality_metrics(
    *,
    category: str | None = None,
    scope_level: str | None = None,
    specialty: str | None = None,
) -> list[dict[str, Any]]:
    query = QualityMetricDefinition.query.filter_by(is_archived=False)
    if category:
        query = query.filter_by(category=category)
    if scope_level:
        query = query.filter_by(scope_level=scope_level)
    if specialty:
        query = query.filter_by(specialty=specialty)
    return [quality_metric_to_dict(row) for row in query.order_by(QualityMetricDefinition.metric_id).all()]


def quality_metric_to_dict(row: QualityMetricDefinition) -> dict[str, Any]:
    return {
        "metric_id": row.metric_id,
        "name": row.name,
        "category": row.category,
        "scope_level": row.scope_level,
        "specialty": row.specialty,
        "department_id": row.quality_department_id,
        "description": row.description,
        "calculation_reference": row.calculation_reference,
        "required_data_sources": row.required_data_sources,
        "target_value": row.target_value,
        "version": row.version,
        "status": row.status,
        "configuration": row.configuration,
    }
