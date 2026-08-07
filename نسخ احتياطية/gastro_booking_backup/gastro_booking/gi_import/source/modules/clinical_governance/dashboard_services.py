"""Clinical Governance dashboard — Sprint 7D."""

from __future__ import annotations

from app.engines import permission_engine
from app.modules.clinical_governance.audit_services import list_audits
from app.modules.clinical_governance.checklist_services import compliance_summary
from app.modules.clinical_governance.constants import AUDIT_PLANNED, AUDIT_IN_PROGRESS, INCIDENT_OPEN, INCIDENT_UNDER_REVIEW
from app.modules.clinical_governance.document_services import list_documents
from app.modules.clinical_governance.incident_services import list_incidents
from app.modules.clinical_governance.kpi_engine import quality_indicators
from app.modules.clinical_governance.mm_services import list_mm_cases
from app.modules.dept_ops.alert_services import collect_alerts
from app.modules.procedures.models import Procedure
from app.modules.workforce.analytics_engine import department_summary


def get_governance_dashboard(acting_user) -> dict:
    permission_engine.require(acting_user, "governance:view")
    open_incidents = list_incidents(acting_user, status=INCIDENT_OPEN)
    under_review = list_incidents(acting_user, status=INCIDENT_UNDER_REVIEW)
    mm_cases = list_mm_cases(acting_user)
    pending_audits = [a for a in list_audits(acting_user) if a.status in {AUDIT_PLANNED, AUDIT_IN_PROGRESS}]
    kpis = quality_indicators(acting_user) if permission_engine.check(acting_user, "governance:kpi_view") else {}
    checklist = compliance_summary(acting_user)
    documents = list_documents(acting_user, status="active")
    equipment_alerts = [a for a in collect_alerts(acting_user) if "equipment" in a.get("type", "") or "scope" in a.get("title", "").lower()]
    return {
        "quality_indicators": kpis,
        "open_incidents": open_incidents,
        "incidents_under_review": under_review,
        "mm_cases": mm_cases,
        "pending_audits": pending_audits,
        "checklist_compliance": checklist,
        "procedure_count": Procedure.query.filter_by(is_archived=False).count(),
        "workforce_summary": department_summary(),
        "equipment_issues": equipment_alerts,
        "active_documents": documents,
    }
