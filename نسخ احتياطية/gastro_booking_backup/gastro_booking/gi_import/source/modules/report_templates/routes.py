from flask import Blueprint, flash, redirect, render_template, url_for
from flask_login import current_user, login_required

from app.core.exceptions import ValidationError
from app.core.route_helpers import handle_service_errors
from app.modules.report_templates import services as template_services
from app.modules.report_templates.definitions import TEMPLATE_COLONOSCOPY, TEMPLATE_LABELS, TEMPLATE_UPPER_GI
from app.modules.report_templates.forms import (
    ColonoscopyFindingsForm,
    SupervisingConsultantForm,
    TextSectionForm,
    UpperGiFindingsForm,
)
from app.modules.reports import services as report_services
from app.modules.reports.models import SECTION_FINDINGS, SECTION_LABELS

bp = Blueprint("report_templates", __name__, url_prefix="/report-templates")


@bp.route("/")
@login_required
@handle_service_errors
def list_template_reports():
    reports = template_services.list_supported_reports(current_user)
    return render_template(
        "report_templates/list.html",
        reports=reports,
        template_labels=TEMPLATE_LABELS,
    )


@bp.route("/for-session/<int:procedure_session_id>")
@login_required
@handle_service_errors
def open_for_session(procedure_session_id):
    report = template_services.open_report_for_session(current_user, procedure_session_id)
    return redirect(url_for("report_templates.view_report", report_id=report.id))


@bp.route("/report/<int:report_id>")
@login_required
@handle_service_errors
def view_report(report_id):
    report = template_services.get_report(current_user, report_id)
    template_key = template_services.get_template_key_for_report(report)
    header = report_services.build_live_header(report)
    sections = {s.section_key: s for s in report.sections}
    return render_template(
        "report_templates/detail.html",
        report=report,
        template_key=template_key,
        template_label=TEMPLATE_LABELS[template_key],
        header=header,
        sections=sections,
        section_labels=SECTION_LABELS,
    )


@bp.route("/report/<int:report_id>/section/<section_key>", methods=["GET", "POST"])
@login_required
@handle_service_errors
def edit_section(report_id, section_key):
    report = template_services.get_report(current_user, report_id)
    template_key = template_services.get_template_key_for_report(report)

    if section_key not in SECTION_LABELS:
        flash("Unknown report section.", "danger")
        return redirect(url_for("report_templates.view_report", report_id=report.id))

    if section_key == SECTION_FINDINGS:
        return _edit_findings(report, template_key)

    section = report_services.get_section(report, section_key)
    form = TextSectionForm(content=section.content)
    if form.validate_on_submit():
        try:
            template_services.update_text_section(
                current_user, report, section_key, form.content.data
            )
        except ValidationError as e:
            flash(str(e), "danger")
            return render_template(
                "report_templates/section_form.html",
                form=form,
                report=report,
                template_key=template_key,
                section_key=section_key,
                section_label=SECTION_LABELS[section_key],
            )
        flash(f"{SECTION_LABELS[section_key]} updated.", "success")
        return redirect(url_for("report_templates.view_report", report_id=report.id))

    return render_template(
        "report_templates/section_form.html",
        form=form,
        report=report,
        template_key=template_key,
        section_key=section_key,
        section_label=SECTION_LABELS[section_key],
    )


def _edit_findings(report, template_key):
    data = template_services.get_findings_data(report, template_key)
    if template_key == TEMPLATE_COLONOSCOPY:
        form = ColonoscopyFindingsForm(data=data)
    else:
        form = UpperGiFindingsForm(data=data)

    if form.validate_on_submit():
        try:
            payload = _findings_payload(form, template_key)
            template_services.update_findings_section(current_user, report, template_key, payload)
        except ValidationError as e:
            flash(str(e), "danger")
            template_name = (
                "report_templates/findings_colonoscopy.html"
                if template_key == TEMPLATE_COLONOSCOPY
                else "report_templates/findings_upper_gi.html"
            )
            return render_template(
                template_name,
                form=form,
                report=report,
                template_key=template_key,
            )
        flash("Findings updated.", "success")
        return redirect(url_for("report_templates.view_report", report_id=report.id))

    template_name = (
        "report_templates/findings_colonoscopy.html"
        if template_key == TEMPLATE_COLONOSCOPY
        else "report_templates/findings_upper_gi.html"
    )
    return render_template(
        template_name,
        form=form,
        report=report,
        template_key=template_key,
    )


def _findings_payload(form, template_key):
    if template_key == TEMPLATE_COLONOSCOPY:
        return {
            "caecum_reached": form.caecum_reached.data,
            "ileum_intubated": form.ileum_intubated.data,
            "bbps_right": form.bbps_right.data,
            "bbps_transverse": form.bbps_transverse.data,
            "bbps_left": form.bbps_left.data,
            "withdrawal_time_minutes": form.withdrawal_time_minutes.data,
            "polyp_findings": form.polyp_findings.data,
            "mucosal_findings": form.mucosal_findings.data,
            "other_findings": form.other_findings.data,
        }
    return {
        "oesophagus_findings": form.oesophagus_findings.data,
        "stomach_findings": form.stomach_findings.data,
        "duodenum_findings": form.duodenum_findings.data,
        "d2_reached": form.d2_reached.data,
        "other_findings": form.other_findings.data,
    }


@bp.route("/report/<int:report_id>/supervising-consultant", methods=["GET", "POST"])
@login_required
@handle_service_errors
def edit_supervising_consultant(report_id):
    report = template_services.get_report(current_user, report_id)
    form = SupervisingConsultantForm(
        supervising_consultant_id=(
            str(report.supervising_consultant_id) if report.supervising_consultant_id else ""
        )
    )
    if form.validate_on_submit():
        try:
            report_services.update_supervising_consultant(
                current_user,
                report,
                int(form.supervising_consultant_id.data)
                if form.supervising_consultant_id.data
                else None,
            )
        except ValidationError as e:
            flash(str(e), "danger")
            return render_template(
                "report_templates/supervising_consultant.html", form=form, report=report
            )
        flash("Supervising consultant updated.", "success")
        return redirect(url_for("report_templates.view_report", report_id=report.id))

    return render_template("report_templates/supervising_consultant.html", form=form, report=report)


@bp.route("/report/<int:report_id>/finalize", methods=["POST"])
@login_required
@handle_service_errors
def finalize_report(report_id):
    report = template_services.get_report(current_user, report_id)
    try:
        report_services.finalize_report(current_user, report)
        flash("Report finalized.", "success")
    except ValidationError as e:
        flash(str(e), "danger")
    return redirect(url_for("report_templates.view_report", report_id=report.id))


@bp.route("/report/<int:report_id>/lock", methods=["POST"])
@login_required
@handle_service_errors
def lock_report(report_id):
    report = template_services.get_report(current_user, report_id)
    try:
        report_services.lock_report(current_user, report)
        flash("Report locked.", "success")
    except ValidationError as e:
        flash(str(e), "danger")
    return redirect(url_for("report_templates.view_report", report_id=report.id))


@bp.route("/report/<int:report_id>/unlock", methods=["POST"])
@login_required
@handle_service_errors
def unlock_report(report_id):
    report = template_services.get_report(current_user, report_id)
    try:
        report_services.unlock_report(current_user, report)
        flash("Report unlocked and returned to draft for editing.", "success")
    except ValidationError as e:
        flash(str(e), "danger")
    return redirect(url_for("report_templates.view_report", report_id=report.id))


@bp.route("/report/<int:report_id>/print")
@login_required
@handle_service_errors
def print_report(report_id):
    report = template_services.get_report(current_user, report_id)
    template_key = template_services.get_template_key_for_report(report)
    header = report_services.build_print_header(report)
    template_name = template_services.print_template_name(template_key)
    return render_template(
        template_name,
        report=report,
        header=header,
        section_labels=SECTION_LABELS,
        template_label=TEMPLATE_LABELS[template_key],
    )
