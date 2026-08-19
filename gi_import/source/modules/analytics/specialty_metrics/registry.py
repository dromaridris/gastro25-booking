"""Specialty metric registry — registers calculators and seeds definitions."""

from __future__ import annotations

from typing import Any, Callable

from app.extensions import db
from app.modules.analytics.constants import METRIC_STATUS_ACTIVE
from app.modules.analytics.data_access import AnalyticsFilters
from app.modules.analytics.models import MetricDefinition

from . import gi_metrics
from .specialty_models import SpecialtyMetricDefinition

SPECIALTY_GASTROENTEROLOGY = "gastroenterology"

CATEGORY_ENDOSCOPY_ACTIVITY = "endoscopy_activity"
CATEGORY_QUALITY_INDICATOR = "quality_indicator"
CATEGORY_ERCP_ANALYTICS = "ercp_analytics"
CATEGORY_DEPARTMENT_ACTIVITY = "department_activity"

SpecialtyCalculator = Callable[[AnalyticsFilters, dict], dict[str, Any]]

SPECIALTY_CALCULATORS: dict[str, SpecialtyCalculator] = {}


def _register(metric_id: str, calculator: SpecialtyCalculator) -> None:
    SPECIALTY_CALCULATORS[metric_id] = calculator


def register_specialty_calculators() -> None:
    """Register GI specialty calculators into the shared registry."""
    mapping = {
        "gi.endoscopy.total_procedures": gi_metrics.gi_total_endoscopy_procedures,
        "gi.endoscopy.upper_gi_volume": gi_metrics.gi_upper_gi_volume,
        "gi.endoscopy.colonoscopy_volume": gi_metrics.gi_colonoscopy_volume,
        "gi.endoscopy.ercp_volume": gi_metrics.gi_ercp_volume,
        "gi.endoscopy.diagnostic_procedures": gi_metrics.gi_diagnostic_procedures,
        "gi.endoscopy.therapeutic_procedures": gi_metrics.gi_therapeutic_procedures,
        "gi.endoscopy.diagnostic_therapeutic_ratio": gi_metrics.gi_diagnostic_therapeutic_ratio,
        "gi.colonoscopy.cecal_intubation_rate": gi_metrics.gi_colonoscopy_cecal_intubation_rate,
        "gi.colonoscopy.adenoma_detection_rate": gi_metrics.gi_colonoscopy_adenoma_detection_rate,
        "gi.colonoscopy.bowel_prep_quality_distribution": gi_metrics.gi_colonoscopy_bowel_prep_distribution,
        "gi.colonoscopy.incomplete_rate": gi_metrics.gi_colonoscopy_incomplete_rate,
        "gi.ercp.cannulation_success_rate": gi_metrics.gi_ercp_cannulation_success_rate,
        "gi.ercp.therapeutic_intervention_rate": gi_metrics.gi_ercp_therapeutic_intervention_rate,
        "gi.ercp.stone_extraction_count": gi_metrics.gi_ercp_stone_extraction_count,
        "gi.ercp.stent_placement_count": gi_metrics.gi_ercp_stent_placement_count,
        "gi.ercp.complication_tracking": gi_metrics.gi_ercp_complication_tracking,
        "gi.dept.procedures_per_physician": gi_metrics.gi_procedures_per_physician,
        "gi.dept.monthly_procedure_trend": gi_metrics.gi_monthly_procedure_trend,
        "gi.dept.workload": gi_metrics.gi_department_workload,
        "gi.dept.patient_volume_trend": gi_metrics.gi_patient_volume_trend,
    }
    for metric_id, calculator in mapping.items():
        _register(metric_id, calculator)


GI_SPECIALTY_METRICS: list[dict] = [
    {
        "metric_id": "gi.endoscopy.total_procedures",
        "name": "Total Endoscopy Procedures",
        "specialty": SPECIALTY_GASTROENTEROLOGY,
        "category": CATEGORY_ENDOSCOPY_ACTIVITY,
        "description": "Total GI endoscopy procedure sessions in the selected period.",
        "calculation_reference": "gi_metrics.gi_total_endoscopy_procedures",
        "required_data_sources": ["procedure_execution", "procedures"],
    },
    {
        "metric_id": "gi.endoscopy.upper_gi_volume",
        "name": "Upper GI Endoscopy Volume",
        "specialty": SPECIALTY_GASTROENTEROLOGY,
        "category": CATEGORY_ENDOSCOPY_ACTIVITY,
        "description": "Upper GI endoscopy sessions by procedure template key.",
        "calculation_reference": "gi_metrics.gi_upper_gi_volume",
        "required_data_sources": ["procedure_execution", "procedures"],
    },
    {
        "metric_id": "gi.endoscopy.colonoscopy_volume",
        "name": "Colonoscopy Volume",
        "specialty": SPECIALTY_GASTROENTEROLOGY,
        "category": CATEGORY_ENDOSCOPY_ACTIVITY,
        "description": "Colonoscopy and related lower GI endoscopy sessions.",
        "calculation_reference": "gi_metrics.gi_colonoscopy_volume",
        "required_data_sources": ["procedure_execution", "procedures"],
    },
    {
        "metric_id": "gi.endoscopy.ercp_volume",
        "name": "ERCP Volume",
        "specialty": SPECIALTY_GASTROENTEROLOGY,
        "category": CATEGORY_ENDOSCOPY_ACTIVITY,
        "description": "ERCP procedure sessions in the selected period.",
        "calculation_reference": "gi_metrics.gi_ercp_volume",
        "required_data_sources": ["procedure_execution", "procedures"],
    },
    {
        "metric_id": "gi.endoscopy.diagnostic_procedures",
        "name": "Diagnostic Procedures",
        "specialty": SPECIALTY_GASTROENTEROLOGY,
        "category": CATEGORY_ENDOSCOPY_ACTIVITY,
        "description": "Endoscopy sessions without documented therapeutic intervention.",
        "calculation_reference": "gi_metrics.gi_diagnostic_procedures",
        "required_data_sources": ["procedure_execution", "clinical_reports"],
    },
    {
        "metric_id": "gi.endoscopy.therapeutic_procedures",
        "name": "Therapeutic Procedures",
        "specialty": SPECIALTY_GASTROENTEROLOGY,
        "category": CATEGORY_ENDOSCOPY_ACTIVITY,
        "description": "Endoscopy sessions with documented therapeutic intervention.",
        "calculation_reference": "gi_metrics.gi_therapeutic_procedures",
        "required_data_sources": ["procedure_execution", "clinical_reports"],
    },
    {
        "metric_id": "gi.endoscopy.diagnostic_therapeutic_ratio",
        "name": "Diagnostic/Therapeutic Ratio",
        "specialty": SPECIALTY_GASTROENTEROLOGY,
        "category": CATEGORY_ENDOSCOPY_ACTIVITY,
        "description": "Ratio of diagnostic to total endoscopy sessions.",
        "calculation_reference": "gi_metrics.gi_diagnostic_therapeutic_ratio",
        "required_data_sources": ["procedure_execution", "clinical_reports"],
    },
    {
        "metric_id": "gi.colonoscopy.cecal_intubation_rate",
        "name": "Cecal Intubation Rate",
        "specialty": SPECIALTY_GASTROENTEROLOGY,
        "category": CATEGORY_QUALITY_INDICATOR,
        "description": "Foundation cecal intubation rate from structured colonoscopy QI metrics.",
        "calculation_reference": "gi_metrics.gi_colonoscopy_cecal_intubation_rate",
        "required_data_sources": ["clinical_reports", "clinical_report_metrics"],
    },
    {
        "metric_id": "gi.colonoscopy.adenoma_detection_rate",
        "name": "Adenoma Detection Rate",
        "specialty": SPECIALTY_GASTROENTEROLOGY,
        "category": CATEGORY_QUALITY_INDICATOR,
        "description": "Foundation adenoma detection rate — incomplete when adenoma documentation unavailable.",
        "calculation_reference": "gi_metrics.gi_colonoscopy_adenoma_detection_rate",
        "required_data_sources": ["clinical_reports", "clinical_report_metrics"],
    },
    {
        "metric_id": "gi.colonoscopy.bowel_prep_quality_distribution",
        "name": "Bowel Preparation Quality Distribution",
        "specialty": SPECIALTY_GASTROENTEROLOGY,
        "category": CATEGORY_QUALITY_INDICATOR,
        "description": "BBPS-based bowel preparation quality distribution.",
        "calculation_reference": "gi_metrics.gi_colonoscopy_bowel_prep_distribution",
        "required_data_sources": ["clinical_reports"],
    },
    {
        "metric_id": "gi.colonoscopy.incomplete_rate",
        "name": "Incomplete Colonoscopy Rate",
        "specialty": SPECIALTY_GASTROENTEROLOGY,
        "category": CATEGORY_QUALITY_INDICATOR,
        "description": "Foundation incomplete colonoscopy rate from structured completion QI metrics.",
        "calculation_reference": "gi_metrics.gi_colonoscopy_incomplete_rate",
        "required_data_sources": ["clinical_reports", "clinical_report_metrics"],
    },
    {
        "metric_id": "gi.ercp.cannulation_success_rate",
        "name": "Cannulation Success Rate",
        "specialty": SPECIALTY_GASTROENTEROLOGY,
        "category": CATEGORY_ERCP_ANALYTICS,
        "description": "Biliary cannulation success rate from structured ERCP reports.",
        "calculation_reference": "gi_metrics.gi_ercp_cannulation_success_rate",
        "required_data_sources": ["clinical_reports", "clinical_report_metrics"],
    },
    {
        "metric_id": "gi.ercp.therapeutic_intervention_rate",
        "name": "Therapeutic Intervention Rate",
        "specialty": SPECIALTY_GASTROENTEROLOGY,
        "category": CATEGORY_ERCP_ANALYTICS,
        "description": "ERCP sessions with therapeutic intervention documented.",
        "calculation_reference": "gi_metrics.gi_ercp_therapeutic_intervention_rate",
        "required_data_sources": ["clinical_reports"],
    },
    {
        "metric_id": "gi.ercp.stone_extraction_count",
        "name": "Stone Extraction Count",
        "specialty": SPECIALTY_GASTROENTEROLOGY,
        "category": CATEGORY_ERCP_ANALYTICS,
        "description": "Number of documented stone extraction interventions.",
        "calculation_reference": "gi_metrics.gi_ercp_stone_extraction_count",
        "required_data_sources": ["clinical_reports"],
    },
    {
        "metric_id": "gi.ercp.stent_placement_count",
        "name": "Stent Placement Count",
        "specialty": SPECIALTY_GASTROENTEROLOGY,
        "category": CATEGORY_ERCP_ANALYTICS,
        "description": "Number of documented biliary and pancreatic stent placements.",
        "calculation_reference": "gi_metrics.gi_ercp_stent_placement_count",
        "required_data_sources": ["clinical_reports"],
    },
    {
        "metric_id": "gi.ercp.complication_tracking",
        "name": "ERCP Complication Tracking",
        "specialty": SPECIALTY_GASTROENTEROLOGY,
        "category": CATEGORY_ERCP_ANALYTICS,
        "description": "Distribution of ERCP complications including PEP, bleeding, perforation, and infection.",
        "calculation_reference": "gi_metrics.gi_ercp_complication_tracking",
        "required_data_sources": ["clinical_reports"],
    },
    {
        "metric_id": "gi.dept.procedures_per_physician",
        "name": "Procedures per Physician",
        "specialty": SPECIALTY_GASTROENTEROLOGY,
        "category": CATEGORY_DEPARTMENT_ACTIVITY,
        "description": "Endoscopy workload breakdown by endoscopist.",
        "calculation_reference": "gi_metrics.gi_procedures_per_physician",
        "required_data_sources": ["procedure_execution", "workforce_identity"],
    },
    {
        "metric_id": "gi.dept.monthly_procedure_trend",
        "name": "Monthly Procedure Trend",
        "specialty": SPECIALTY_GASTROENTEROLOGY,
        "category": CATEGORY_DEPARTMENT_ACTIVITY,
        "description": "Monthly endoscopy volume trend for the department.",
        "calculation_reference": "gi_metrics.gi_monthly_procedure_trend",
        "required_data_sources": ["procedure_execution"],
    },
    {
        "metric_id": "gi.dept.workload",
        "name": "Department Workload",
        "specialty": SPECIALTY_GASTROENTEROLOGY,
        "category": CATEGORY_DEPARTMENT_ACTIVITY,
        "description": "Total and completed endoscopy session workload.",
        "calculation_reference": "gi_metrics.gi_department_workload",
        "required_data_sources": ["procedure_execution"],
    },
    {
        "metric_id": "gi.dept.patient_volume_trend",
        "name": "Patient Volume Trend",
        "specialty": SPECIALTY_GASTROENTEROLOGY,
        "category": CATEGORY_DEPARTMENT_ACTIVITY,
        "description": "Distinct patients with endoscopy sessions versus encounter volume.",
        "calculation_reference": "gi_metrics.gi_patient_volume_trend",
        "required_data_sources": ["procedure_execution", "encounters", "patients"],
    },
]


def get_specialty_calculator(metric_id_or_ref: str) -> SpecialtyCalculator | None:
    if metric_id_or_ref in SPECIALTY_CALCULATORS:
        return SPECIALTY_CALCULATORS[metric_id_or_ref]
    suffix = metric_id_or_ref.rsplit(".", 1)[-1]
    for metric_id, calculator in SPECIALTY_CALCULATORS.items():
        if metric_id.endswith(suffix) or calculator.__name__ == suffix:
            return calculator
    return None


def seed_specialty_metrics_if_empty() -> int:
    """Register specialty metrics through MetricDefinition framework."""
    created = 0
    for spec in GI_SPECIALTY_METRICS:
        specialty_existing = SpecialtyMetricDefinition.query.filter_by(metric_id=spec["metric_id"]).first()
        if specialty_existing:
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
            db.session.add(metric)
            db.session.flush()
        else:
            metric.name = spec["name"]
            metric.description = spec.get("description")
            metric.category = spec["category"]
            metric.calculation_logic_ref = spec["calculation_reference"]
            metric.data_sources = spec.get("required_data_sources", [])

        specialty = SpecialtyMetricDefinition(
            metric_id=spec["metric_id"],
            metric_definition_id=metric.id,
            specialty=spec["specialty"],
            category=spec["category"],
            description=spec.get("description"),
            calculation_reference=spec["calculation_reference"],
            status=METRIC_STATUS_ACTIVE,
            version=1,
        )
        specialty.required_data_sources = spec.get("required_data_sources", [])
        specialty.configuration = spec.get("configuration", {})
        db.session.add(specialty)
        created += 1

    if created:
        db.session.commit()
    return created


def ensure_specialty_metrics_seeded() -> int:
    return seed_specialty_metrics_if_empty()


def list_specialty_metrics(specialty: str | None = None) -> list[dict[str, Any]]:
    query = SpecialtyMetricDefinition.query.filter_by(is_archived=False)
    if specialty:
        query = query.filter_by(specialty=specialty)
    rows = query.order_by(SpecialtyMetricDefinition.metric_id).all()
    return [specialty_metric_to_dict(row) for row in rows]


def specialty_metric_to_dict(row: SpecialtyMetricDefinition) -> dict[str, Any]:
    return {
        "metric_id": row.metric_id,
        "specialty": row.specialty,
        "department_id": row.specialty_department_id,
        "category": row.category,
        "description": row.description,
        "calculation_reference": row.calculation_reference,
        "required_data_sources": row.required_data_sources,
        "version": row.version,
        "status": row.status,
        "configuration": row.configuration,
    }
