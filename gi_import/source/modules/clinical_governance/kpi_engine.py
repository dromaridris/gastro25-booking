"""Quality indicator (KPI) engine — Sprint 7D. Aggregates from existing modules only."""

from __future__ import annotations

from datetime import date, datetime, timedelta

from app.engines import permission_engine
from app.modules.clinical_governance.constants import CHECKLIST_ENDOSCOPY_SAFETY
from app.modules.clinical_reports.models import ClinicalReportDocument, ClinicalReportMetric
from app.modules.dept_ops.models import WaitingListEntry
from app.modules.dept_ops.waiting_list_services import waiting_duration_days
from app.modules.procedure_execution.models import OUTCOME_COMPLETED, ProcedureSession
from app.modules.procedures.models import (
    REPORT_TEMPLATE_KEY_COLONOSCOPY,
    REPORT_TEMPLATE_KEY_ERCP,
    REPORT_TEMPLATE_KEY_UPPER_GI,
    STATUS_CANCELLED,
    Procedure,
    ProcedureType,
)
from app.modules.reports.models import Report, STATUS_FINALIZED, STATUS_LOCKED
from app.modules.workforce.analytics_engine import department_summary, user_kpis


def _require(user, permission: str) -> None:
    permission_engine.require(user, permission)


def _metric_rate(metric_key: str, template_key: str | None = None) -> dict:
    query = ClinicalReportMetric.query.join(ClinicalReportDocument).filter(
        ClinicalReportMetric.metric_key == metric_key,
        ClinicalReportMetric.is_archived.is_(False),
    )
    if template_key:
        query = query.filter(ClinicalReportDocument.template_key == template_key)
    metrics = query.all()
    if not metrics:
        return {"count": 0, "rate_pct": None, "metric_key": metric_key}
    yes_count = sum(1 for m in metrics if str(m.metric_value).lower() in {"yes", "true", "1", "100"})
    total = len(metrics)
    return {"count": total, "rate_pct": round(yes_count * 100 / total, 1), "metric_key": metric_key}


def upper_gi_kpis() -> dict:
    completion = _metric_rate("procedure_completed", REPORT_TEMPLATE_KEY_UPPER_GI)
    biopsy = _metric_rate("biopsy_performed", REPORT_TEMPLATE_KEY_UPPER_GI)
    return {
        "completion_rate_pct": completion["rate_pct"],
        "biopsy_rate_pct": biopsy["rate_pct"],
        "sample_size": completion["count"],
    }


def colonoscopy_kpis() -> dict:
    cecal = _metric_rate("cecal_intubation", REPORT_TEMPLATE_KEY_COLONOSCOPY)
    adr = _metric_rate("adenoma_detection", REPORT_TEMPLATE_KEY_COLONOSCOPY)
    prep = _metric_rate("bowel_preparation_adequate", REPORT_TEMPLATE_KEY_COLONOSCOPY)
    return {
        "cecal_intubation_rate_pct": cecal["rate_pct"],
        "adenoma_detection_rate_pct": adr["rate_pct"],
        "bowel_prep_adequate_pct": prep["rate_pct"],
        "sample_size": cecal["count"],
    }


def ercp_kpis() -> dict:
    cannulation = _metric_rate("cannulation_success", REPORT_TEMPLATE_KEY_ERCP)
    stone = _metric_rate("stone_clearance", REPORT_TEMPLATE_KEY_ERCP)
    complication = _metric_rate("complication_occurred", REPORT_TEMPLATE_KEY_ERCP)
    pep = _metric_rate("post_ercp_pancreatitis", REPORT_TEMPLATE_KEY_ERCP)
    return {
        "cannulation_success_pct": cannulation["rate_pct"],
        "stone_clearance_pct": stone["rate_pct"],
        "complication_rate_pct": complication["rate_pct"],
        "post_ercp_pancreatitis_pct": pep["rate_pct"],
        "sample_size": cannulation["count"],
    }


def waiting_list_kpis() -> dict:
    active = WaitingListEntry.query.filter_by(is_archived=False, status="active").all()
    durations = [waiting_duration_days(e) for e in active]
    urgent = [e for e in active if e.priority in {"urgent", "emergency"}]
    urgent_delays = [waiting_duration_days(e) for e in urgent if waiting_duration_days(e) > 14]
    total_procedures = Procedure.query.filter_by(is_archived=False).count()
    cancelled = Procedure.query.filter_by(is_archived=False, status=STATUS_CANCELLED).count()
    return {
        "average_waiting_days": round(sum(durations) / len(durations), 1) if durations else 0,
        "urgent_delay_count": len(urgent_delays),
        "active_waiting_count": len(active),
        "cancellation_rate_pct": round(cancelled * 100 / total_procedures, 1) if total_procedures else 0,
    }


def report_kpis() -> dict:
    finalized = Report.query.filter(
        Report.status.in_([STATUS_FINALIZED, STATUS_LOCKED]), Report.is_archived.is_(False)
    ).all()
    turnarounds = []
    for r in finalized:
        if r.finalized_at and r.created_at:
            turnarounds.append((r.finalized_at - r.created_at).total_seconds() / 3600)
    return {
        "report_turnaround_hours": round(sum(turnarounds) / len(turnarounds), 1) if turnarounds else None,
        "finalized_count": len(finalized),
    }


def workforce_kpis() -> dict:
    summary = department_summary()
    consultant_procedures = sum(s["kpis"]["procedures"] for s in summary["trainees"])
    return {
        "trainee_procedure_total": consultant_procedures,
        "trainee_count": summary["trainee_count"],
        "department_totals": summary["department_totals"],
        "trainee_breakdown": [
            {"user_id": s["user"].id, "procedures": s["kpis"]["procedures"], "reports": s["kpis"]["reports_authored"]}
            for s in summary["trainees"]
        ],
    }


def quality_indicators(acting_user) -> dict:
    _require(acting_user, "governance:kpi_view")
    return {
        "upper_gi": upper_gi_kpis(),
        "colonoscopy": colonoscopy_kpis(),
        "ercp": ercp_kpis(),
        "waiting_list": waiting_list_kpis(),
        "reports": report_kpis(),
        "workforce": workforce_kpis(),
    }
