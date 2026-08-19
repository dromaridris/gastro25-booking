from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.core.exceptions import ValidationError
from app.core.route_helpers import handle_service_errors
from app.modules.clinical_reports.fields.payload import StructuredPayload
from app.modules.clinical_reports.platform.ui_helpers import strip_hidden_phase_fields, template_view_path
from app.modules.clinical_reports.platform.ui_registry import get_ui_module
from app.modules.clinical_reports import services as cr_services
from app.modules.clinical_reports import image_services as cr_image_services
from app.modules.clinical_reports.models import WF_FINALIZE, WF_REVIEW
from app.modules.reports import services as report_services
from app.modules.reports.forms import SupervisingConsultantForm
from app.modules.reports.models import SECTION_LABELS

bp = Blueprint("clinical_reports", __name__, url_prefix="/clinical-reports")


def _ui_for(template_key: str):
    return get_ui_module(template_key)


@bp.route("/")
@login_required
@handle_service_errors
def list_reports():
    reports = cr_services.list_structured_reports(current_user)
    return render_template("clinical_reports/list.html", reports=reports)


@bp.route("/for-session/<int:procedure_session_id>")
@login_required
@handle_service_errors
def open_for_session(procedure_session_id):
    report, _document = cr_services.open_report_for_session(current_user, procedure_session_id)
    return redirect(url_for("clinical_reports.view_report", report_id=report.id))


@bp.route("/report/<int:report_id>")
@login_required
@handle_service_errors
def view_report(report_id):
    report, document, template_key = cr_services.get_report_bundle(current_user, report_id)
    ui = _ui_for(template_key)
    ctx = cr_services.workflow_context(report, document, template_key)
    header = report_services.build_live_header(report)
    sections = {s.section_key: s for s in report.sections}
    template_ctx = {
        "report": report,
        "document": document,
        "header": header,
        "sections": sections,
        "section_labels": SECTION_LABELS,
        "phase_labels": ui.phase_labels(),
        "editable_phase_states": ui.EDITABLE_PHASE_STATES,
        **ctx,
    }
    if document.workflow_state == WF_REVIEW:
        return render_template(template_view_path(template_key, "review.html"), **template_ctx)
    if document.workflow_state == WF_FINALIZE:
        return render_template(template_view_path(template_key, "finalize.html"), **template_ctx)
    return render_template(template_view_path(template_key, "detail.html"), **template_ctx)


@bp.route("/report/<int:report_id>/phase/<phase_state>", methods=["GET", "POST"])
@login_required
@handle_service_errors
def edit_phase(report_id, phase_state):
    report, document, template_key = cr_services.get_report_bundle(current_user, report_id)
    ui = _ui_for(template_key)
    if phase_state not in ui.PHASE_FORMS:
        flash("Unknown workflow phase.", "danger")
        return redirect(url_for("clinical_reports.view_report", report_id=report_id))

    if not report.is_editable:
        flash("This report is not editable.", "warning")
        return redirect(url_for("clinical_reports.view_report", report_id=report_id))

    phase_key, form_class, bind_fn = ui.PHASE_FORMS[phase_state]
    sp = StructuredPayload(document.get_payload(), template_key=template_key)
    form = form_class()
    if bind_fn:
        bind_fn(form, sp.get_legacy_phase(phase_key))

    if form.validate_on_submit():
        from app.modules.clinical_reports.fields.registry import get_fsd

        fsd = get_fsd(template_key)
        phase_data = strip_hidden_phase_fields(
            fsd,
            phase_key,
            ui.extract_phase_data(phase_key),
            document.get_payload(),
        )
        try:
            cr_services.update_phase_payload(
                current_user, report, document, phase_key, phase_data
            )
        except ValidationError as e:
            flash(str(e), "danger")
            return render_template(
                template_view_path(template_key, "phase_form.html"),
                **ui.phase_template_context(report, document, phase_state, sp, form),
            )
        flash(f"{ui.phase_labels()[phase_state]} saved.", "success")
        return redirect(url_for("clinical_reports.view_report", report_id=report.id))

    return render_template(
        template_view_path(template_key, "phase_form.html"),
        **ui.phase_template_context(report, document, phase_state, sp, form),
    )


@bp.route("/report/<int:report_id>/images", methods=["POST"])
@login_required
@handle_service_errors
def upload_report_images(report_id):
    report, document, _template_key = cr_services.get_report_bundle(current_user, report_id)
    if not report.is_editable:
        flash("This report is not editable.", "warning")
        return redirect(url_for("clinical_reports.view_report", report_id=report.id))

    files = request.files.getlist("images")
    try:
        saved = cr_image_services.upload_report_images(current_user, report, document, files)
    except ValidationError as e:
        flash(str(e), "danger")
        return redirect(url_for("clinical_reports.view_report", report_id=report.id))

    for attachment in saved:
        label = attachment.original_filename or "Image"
        flash(f"Image uploaded: {label}", "success")

    skipped = len([f for f in files if f and getattr(f, "filename", None)]) - len(saved)
    if skipped > 0:
        flash(
            f"{skipped} image(s) were not uploaded because the report reached its limit.",
            "warning",
        )
    return redirect(url_for("clinical_reports.view_report", report_id=report.id))


@bp.route("/report/<int:report_id>/images/<int:attachment_id>/delete", methods=["POST"])
@login_required
@handle_service_errors
def delete_report_image(report_id, attachment_id):
    report, document, _template_key = cr_services.get_report_bundle(current_user, report_id)
    if not report.is_editable:
        flash("This report is not editable.", "warning")
        return redirect(url_for("clinical_reports.view_report", report_id=report.id))

    try:
        cr_image_services.delete_report_image(current_user, report, document, attachment_id)
    except ValidationError as e:
        flash(str(e), "danger")
        return redirect(url_for("clinical_reports.view_report", report_id=report.id))

    flash("Image deleted.", "success")
    return redirect(url_for("clinical_reports.view_report", report_id=report.id))


@bp.route("/report/<int:report_id>/timeline", methods=["GET", "POST"])
@login_required
@handle_service_errors
def edit_timeline(report_id):
    report, document, template_key = cr_services.get_report_bundle(current_user, report_id)
    ui = _ui_for(template_key)
    ctx = cr_services.workflow_context(report, document, template_key)
    form = ui.TIMELINE_FORM()
    existing = {ev.event_key: ev for ev in ctx["timeline_events"]}

    if form.validate_on_submit() and report.is_editable:
        event_times = {}
        for event_def in ctx["timeline_defs"]:
            key = event_def["key"]
            event_times[key] = request.form.get(f"occurred_at_{key}") or None
        cr_services.save_timeline_events(current_user, report, document, event_times)
        flash("Timeline saved.", "success")
        return redirect(url_for("clinical_reports.view_report", report_id=report.id))

    return render_template(
        template_view_path(template_key, "timeline.html"),
        form=form,
        report=report,
        document=document,
        existing=existing,
        **ctx,
    )


@bp.route("/report/<int:report_id>/acknowledge-validation", methods=["POST"])
@login_required
@handle_service_errors
def acknowledge_validation(report_id):
    report, document, _template_key = cr_services.get_report_bundle(current_user, report_id)
    rule_ids = request.form.getlist("rule_id")
    cr_services.acknowledge_validation(current_user, report, document, rule_ids)
    flash("Validation warnings acknowledged.", "success")
    return redirect(url_for("clinical_reports.view_report", report_id=report.id))


@bp.route("/report/<int:report_id>/transition", methods=["POST"])
@login_required
@handle_service_errors
def transition(report_id):
    report, document, template_key = cr_services.get_report_bundle(current_user, report_id)
    ui = _ui_for(template_key)
    to_state = request.form.get("to_state")
    try:
        cr_services.transition_workflow(current_user, report, document, to_state)
        flash(f"Advanced to {ui.phase_labels().get(to_state, to_state)}.", "success")
    except ValidationError as e:
        flash(str(e), "danger")
    return redirect(url_for("clinical_reports.view_report", report_id=report.id))


@bp.route("/report/<int:report_id>/quick-fill", methods=["POST"])
@login_required
@handle_service_errors
def quick_fill(report_id):
    report, document, _template_key = cr_services.get_report_bundle(current_user, report_id)
    profile_key = request.form.get("profile_key")
    try:
        cr_services.apply_quick_fill(current_user, report, document, profile_key)
        flash("Quick-fill profile applied.", "success")
    except ValidationError as e:
        flash(str(e), "danger")
    return redirect(url_for("clinical_reports.view_report", report_id=report.id))


@bp.route("/report/<int:report_id>/regenerate", methods=["POST"])
@login_required
@handle_service_errors
def regenerate(report_id):
    report, document, _template_key = cr_services.get_report_bundle(current_user, report_id)
    cr_services.regenerate_narrative(current_user, report, document)
    flash("Narrative regenerated from structured data.", "success")
    return redirect(url_for("clinical_reports.view_report", report_id=report.id))


@bp.route("/report/<int:report_id>/finalize", methods=["POST"])
@login_required
@handle_service_errors
def finalize_report(report_id):
    report, document, _template_key = cr_services.get_report_bundle(current_user, report_id)
    try:
        cr_services.finalize_report(current_user, report, document)
        flash("Report finalized.", "success")
    except ValidationError as e:
        flash(str(e), "danger")
    return redirect(url_for("clinical_reports.view_report", report_id=report.id))


@bp.route("/report/<int:report_id>/lock", methods=["POST"])
@login_required
@handle_service_errors
def lock_report(report_id):
    report, _document, _template_key = cr_services.get_report_bundle(current_user, report_id)
    try:
        report_services.lock_report(current_user, report)
        flash("Report locked.", "success")
    except ValidationError as e:
        flash(str(e), "danger")
    return redirect(url_for("clinical_reports.view_report", report_id=report.id))


@bp.route("/report/<int:report_id>/unlock", methods=["POST"])
@login_required
@handle_service_errors
def unlock_report(report_id):
    report, document, _template_key = cr_services.get_report_bundle(current_user, report_id)
    try:
        report_services.unlock_report(current_user, report)
        if document is not None:
            cr_services.reset_document_after_unlock(document)
        flash("Report unlocked and returned to review for editing.", "success")
    except ValidationError as e:
        flash(str(e), "danger")
    return redirect(url_for("clinical_reports.view_report", report_id=report.id))


@bp.route("/report/<int:report_id>/supervising-consultant", methods=["GET", "POST"])
@login_required
@handle_service_errors
def edit_supervising_consultant(report_id):
    report, _document, _template_key = cr_services.get_report_bundle(current_user, report_id)
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
                "clinical_reports/supervising_consultant.html", form=form, report=report
            )
        flash("Supervising consultant updated.", "success")
        return redirect(url_for("clinical_reports.view_report", report_id=report.id))

    return render_template("clinical_reports/supervising_consultant.html", form=form, report=report)


@bp.route("/report/<int:report_id>/print")
@login_required
@handle_service_errors
def print_report(report_id):
    report, document, template_key = cr_services.get_report_bundle(current_user, report_id)
    header = report_services.build_print_header(report)
    ctx = cr_services.workflow_context(report, document, template_key)
    sections = {s.section_key: s for s in report.sections}
    return render_template(
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
