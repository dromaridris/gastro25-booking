"""Branding integration routes — PDF, favicon."""

from flask import Blueprint, Response, url_for
from flask_login import current_user, login_required

from app.core.route_helpers import handle_service_errors
from app.modules.branding_integration.favicon_service import generate_favicon_bytes
from app.modules.branding_integration.pdf_service import render_template_to_pdf

bp = Blueprint("branding_integration", __name__)


@bp.route("/favicon.ico")
def favicon():
    return Response(generate_favicon_bytes(), mimetype="image/png")


@bp.route("/pdf/reports/<int:report_id>")
@login_required
@handle_service_errors
def pdf_generic_report(report_id):
    from app.modules.reports.models import SECTION_LABELS
    from app.modules.reports import services as report_services

    report = report_services.get_report(current_user, report_id)
    header = report_services.build_print_header(report)
    pdf = render_template_to_pdf(
        "reports/print.html",
        report=report,
        header=header,
        section_labels=SECTION_LABELS,
    )
    return Response(
        pdf,
        mimetype="application/pdf",
        headers={"Content-Disposition": f'inline; filename="report-{report.report_number}.pdf"'},
    )


@bp.route("/pdf/clinical-reports/<int:report_id>")
@login_required
@handle_service_errors
def pdf_clinical_report(report_id):
    from app.modules.clinical_reports import services as cr_services
    from app.modules.clinical_reports.constants import SECTION_LABELS
    from app.modules.clinical_reports.template_registry import template_view_path
    from app.modules.reports import services as report_services

    report, document, template_key = cr_services.get_report_bundle(current_user, report_id)
    header = report_services.build_print_header(report)
    ctx = cr_services.workflow_context(report, document, template_key)
    sections = {s.section_key: s for s in report.sections}
    pdf = render_template_to_pdf(
        template_view_path(template_key, "print.html"),
        report=report,
        header=header,
        sections=sections,
        section_labels=SECTION_LABELS,
        template_label=ctx["template_label"],
        metrics=ctx["metrics"],
        qi_labels=ctx["qi_labels"],
        timeline_defs=ctx["timeline_defs"],
        timeline_by_key=ctx["timeline_by_key"],
        has_timeline_times=ctx["has_timeline_times"],
    )
    return Response(
        pdf,
        mimetype="application/pdf",
        headers={"Content-Disposition": f'inline; filename="clinical-{report.report_number}.pdf"'},
    )


@bp.route("/pdf/template-reports/<int:report_id>")
@login_required
@handle_service_errors
def pdf_template_report(report_id):
    from app.modules.report_templates.definitions import TEMPLATE_LABELS
    from app.modules.report_templates import services as template_services
    from app.modules.reports import services as report_services
    from app.modules.reports.models import SECTION_LABELS

    report = template_services.get_report(current_user, report_id)
    template_key = template_services.get_template_key_for_report(report)
    header = report_services.build_print_header(report)
    template_name = template_services.print_template_name(template_key)
    pdf = render_template_to_pdf(
        template_name,
        report=report,
        header=header,
        section_labels=SECTION_LABELS,
        template_label=TEMPLATE_LABELS[template_key],
    )
    return Response(
        pdf,
        mimetype="application/pdf",
        headers={"Content-Disposition": f'inline; filename="template-{report.report_number}.pdf"'},
    )
