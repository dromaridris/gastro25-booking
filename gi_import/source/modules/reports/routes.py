from flask import Blueprint, flash, redirect, render_template, url_for
from flask_login import current_user, login_required

from app.core.exceptions import ValidationError
from app.core.route_helpers import handle_service_errors
from app.modules.reports import services
from app.modules.reports.forms import ArchiveReportForm, SectionEditForm, SupervisingConsultantForm
from app.modules.reports.models import SECTION_LABELS

bp = Blueprint("reports", __name__, url_prefix="/reports")


@bp.route("/")
@login_required
@handle_service_errors
def list_reports():
    reports = services.list_reports(current_user)
    return render_template("reports/list.html", reports=reports)


@bp.route("/for-session/<int:procedure_session_id>")
@login_required
@handle_service_errors
def open_for_session(procedure_session_id):
    report = services.get_or_create_report(current_user, procedure_session_id)
    return redirect(url_for("reports.view_report", report_id=report.id))


@bp.route("/<int:report_id>")
@login_required
@handle_service_errors
def view_report(report_id):
    report = services.get_report(current_user, report_id)
    header = services.build_live_header(report)
    sections = {s.section_key: s for s in report.sections}
    return render_template(
        "reports/detail.html",
        report=report,
        header=header,
        sections=sections,
        section_labels=SECTION_LABELS,
    )


@bp.route("/<int:report_id>/section/<section_key>", methods=["GET", "POST"])
@login_required
@handle_service_errors
def edit_section(report_id, section_key):
    report = services.get_report(current_user, report_id)
    if section_key not in SECTION_LABELS:
        flash("Unknown report section.", "danger")
        return redirect(url_for("reports.view_report", report_id=report.id))

    section = services.get_section(report, section_key)
    form = SectionEditForm(content=section.content)
    if form.validate_on_submit():
        try:
            services.update_section(current_user, report, section_key, form.content.data)
        except ValidationError as e:
            flash(str(e), "danger")
            return render_template(
                "reports/section_form.html",
                form=form,
                report=report,
                section_key=section_key,
                section_label=SECTION_LABELS[section_key],
            )

        flash(f"{SECTION_LABELS[section_key]} updated.", "success")
        return redirect(url_for("reports.view_report", report_id=report.id))

    return render_template(
        "reports/section_form.html",
        form=form,
        report=report,
        section_key=section_key,
        section_label=SECTION_LABELS[section_key],
    )


@bp.route("/<int:report_id>/supervising-consultant", methods=["GET", "POST"])
@login_required
@handle_service_errors
def edit_supervising_consultant(report_id):
    report = services.get_report(current_user, report_id)
    form = SupervisingConsultantForm(
        supervising_consultant_id=(
            str(report.supervising_consultant_id) if report.supervising_consultant_id else ""
        )
    )
    if form.validate_on_submit():
        try:
            services.update_supervising_consultant(
                current_user,
                report,
                int(form.supervising_consultant_id.data)
                if form.supervising_consultant_id.data
                else None,
            )
        except ValidationError as e:
            flash(str(e), "danger")
            return render_template("reports/supervising_consultant.html", form=form, report=report)

        flash("Supervising consultant updated.", "success")
        return redirect(url_for("reports.view_report", report_id=report.id))

    return render_template("reports/supervising_consultant.html", form=form, report=report)


@bp.route("/<int:report_id>/finalize", methods=["POST"])
@login_required
@handle_service_errors
def finalize_report(report_id):
    report = services.get_report(current_user, report_id)
    try:
        services.finalize_report(current_user, report)
        flash("Report finalized.", "success")
    except ValidationError as e:
        flash(str(e), "danger")
    return redirect(url_for("reports.view_report", report_id=report.id))


@bp.route("/<int:report_id>/lock", methods=["POST"])
@login_required
@handle_service_errors
def lock_report(report_id):
    report = services.get_report(current_user, report_id)
    try:
        services.lock_report(current_user, report)
        flash("Report locked.", "success")
    except ValidationError as e:
        flash(str(e), "danger")
    return redirect(url_for("reports.view_report", report_id=report.id))


@bp.route("/<int:report_id>/unlock", methods=["POST"])
@login_required
@handle_service_errors
def unlock_report(report_id):
    report = services.get_report(current_user, report_id)
    try:
        services.unlock_report(current_user, report)
        flash("Report unlocked and returned to draft for editing.", "success")
    except ValidationError as e:
        flash(str(e), "danger")
    return redirect(url_for("reports.view_report", report_id=report.id))


@bp.route("/<int:report_id>/print")
@login_required
@handle_service_errors
def print_report(report_id):
    report = services.get_report(current_user, report_id)
    header = services.build_print_header(report)
    return render_template(
        "reports/print.html",
        report=report,
        header=header,
        section_labels=SECTION_LABELS,
    )


@bp.route("/<int:report_id>/archive", methods=["GET", "POST"])
@login_required
@handle_service_errors
def archive_report(report_id):
    report = services.get_report(current_user, report_id)
    form = ArchiveReportForm()
    if form.validate_on_submit():
        try:
            services.archive_report(current_user, report, reason=form.reason.data)
        except ValidationError as e:
            flash(str(e), "danger")
            return render_template("reports/archive.html", form=form, report=report)

        flash("Report archived.", "success")
        return redirect(url_for("reports.list_reports"))

    return render_template("reports/archive.html", form=form, report=report)


@bp.route("/<int:report_id>/restore", methods=["POST"])
@login_required
@handle_service_errors
def restore_report(report_id):
    report = services.get_report(current_user, report_id)
    try:
        services.restore_report(current_user, report)
        flash("Report restored.", "success")
    except ValidationError as e:
        flash(str(e), "danger")
    return redirect(url_for("reports.view_report", report_id=report.id))
