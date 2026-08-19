"""Clinical Governance routes — Sprint 7D."""

from datetime import date, datetime

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.core.route_helpers import handle_service_errors
from app.modules.clinical_governance import (
    audit_services,
    checklist_services,
    dashboard_services,
    document_services,
    incident_services,
    kpi_engine,
    mm_services,
)
from app.modules.clinical_governance.constants import ALL_DOCUMENT_TYPES, ALL_INCIDENT_CATEGORIES

bp = Blueprint("clinical_governance", __name__, url_prefix="/governance")


@bp.route("/")
@login_required
@handle_service_errors
def home():
    data = dashboard_services.get_governance_dashboard(current_user)
    return render_template("clinical_governance/dashboard.html", **data)


@bp.route("/incidents")
@login_required
@handle_service_errors
def incidents():
    items = incident_services.list_incidents(current_user)
    return render_template("clinical_governance/incidents.html", incidents=items, categories=ALL_INCIDENT_CATEGORIES)


@bp.route("/incidents/new", methods=["GET", "POST"])
@login_required
@handle_service_errors
def create_incident():
    if request.method == "POST":
        incident_services.create_incident(
            current_user,
            incident_date=datetime.fromisoformat(request.form.get("incident_date")),
            category=request.form.get("category"),
            severity=request.form.get("severity"),
            description=request.form.get("description"),
            patient_id=request.form.get("patient_id", type=int),
            procedure_id=request.form.get("procedure_id", type=int),
            is_anonymous=bool(request.form.get("is_anonymous")),
        )
        flash("Incident reported.", "success")
        return redirect(url_for("clinical_governance.incidents"))
    return render_template("clinical_governance/incident_form.html", categories=ALL_INCIDENT_CATEGORIES)


@bp.route("/incidents/<int:incident_id>")
@login_required
@handle_service_errors
def incident_detail(incident_id):
    incident = incident_services.get_incident(current_user, incident_id)
    return render_template("clinical_governance/incident_detail.html", incident=incident)


@bp.route("/incidents/<int:incident_id>/review", methods=["POST"])
@login_required
@handle_service_errors
def review_incident(incident_id):
    incident = incident_services.get_incident(current_user, incident_id)
    incident_services.review_incident(
        current_user,
        incident,
        root_cause=request.form.get("root_cause"),
        corrective_action=request.form.get("corrective_action"),
        preventive_action=request.form.get("preventive_action"),
        status=request.form.get("status", "under_review"),
    )
    flash("Incident updated.", "success")
    return redirect(url_for("clinical_governance.incident_detail", incident_id=incident_id))


@bp.route("/mm")
@login_required
@handle_service_errors
def mm_cases():
    cases = mm_services.list_mm_cases(current_user)
    return render_template("clinical_governance/mm_cases.html", cases=cases)


@bp.route("/mm/new", methods=["POST"])
@login_required
@handle_service_errors
def create_mm_case():
    sched = request.form.get("presentation_date")
    mm_services.create_mm_case(
        current_user,
        case_summary=request.form.get("case_summary"),
        patient_id=request.form.get("patient_id", type=int),
        procedure_id=request.form.get("procedure_id", type=int),
        presentation_date=date.fromisoformat(sched) if sched else None,
    )
    flash("M&M case created.", "success")
    return redirect(url_for("clinical_governance.mm_cases"))


@bp.route("/mm/<int:case_id>", methods=["GET", "POST"])
@login_required
@handle_service_errors
def mm_detail(case_id):
    case = mm_services.get_mm_case(current_user, case_id)
    if request.method == "POST":
        mm_services.update_mm_discussion(
            current_user,
            case,
            discussion_notes=request.form.get("discussion_notes"),
            lessons_learned=request.form.get("lessons_learned"),
            recommendations=request.form.get("recommendations"),
            follow_up_actions=request.form.get("follow_up_actions"),
            status=request.form.get("status"),
        )
        flash("M&M case updated.", "success")
        return redirect(url_for("clinical_governance.mm_detail", case_id=case_id))
    return render_template("clinical_governance/mm_detail.html", case=case)


@bp.route("/kpis")
@login_required
@handle_service_errors
def kpis():
    indicators = kpi_engine.quality_indicators(current_user)
    return render_template("clinical_governance/kpis.html", kpis=indicators)


@bp.route("/audits")
@login_required
@handle_service_errors
def audits():
    items = audit_services.list_audits(current_user)
    return render_template("clinical_governance/audits.html", audits=items)


@bp.route("/audits/new", methods=["POST"])
@login_required
@handle_service_errors
def create_audit():
    start = request.form.get("timeline_start")
    end = request.form.get("timeline_end")
    audit_services.create_audit(
        current_user,
        title=request.form.get("title"),
        objective=request.form.get("objective"),
        methodology=request.form.get("methodology"),
        inclusion_criteria=request.form.get("inclusion_criteria"),
        timeline_start=date.fromisoformat(start) if start else None,
        timeline_end=date.fromisoformat(end) if end else None,
        research_study_id=request.form.get("research_study_id", type=int),
    )
    flash("Audit project created.", "success")
    return redirect(url_for("clinical_governance.audits"))


@bp.route("/checklists")
@login_required
@handle_service_errors
def checklists():
    summary = checklist_services.compliance_summary(current_user)
    return render_template("clinical_governance/checklists.html", summary=summary)


@bp.route("/documents")
@login_required
@handle_service_errors
def documents():
    items = document_services.list_documents(current_user)
    return render_template("clinical_governance/documents.html", documents=items, doc_types=ALL_DOCUMENT_TYPES)


@bp.route("/documents/new", methods=["POST"])
@login_required
@handle_service_errors
def create_document():
    expiry = request.form.get("expiry_date")
    document_services.create_document(
        current_user,
        title=request.form.get("title"),
        document_type=request.form.get("document_type"),
        version=request.form.get("version") or "1.0",
        content_summary=request.form.get("content_summary"),
        expiry_date=date.fromisoformat(expiry) if expiry else None,
    )
    flash("Document created.", "success")
    return redirect(url_for("clinical_governance.documents"))


@bp.route("/documents/<int:doc_id>/acknowledge", methods=["POST"])
@login_required
@handle_service_errors
def acknowledge_document(doc_id):
    document_services.acknowledge_document(current_user, doc_id)
    flash("Document acknowledged.", "success")
    return redirect(url_for("clinical_governance.documents"))
