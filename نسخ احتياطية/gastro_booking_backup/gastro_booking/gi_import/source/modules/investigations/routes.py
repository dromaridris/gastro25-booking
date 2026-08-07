import os
import uuid

from flask import Blueprint, flash, redirect, render_template, request, url_for, current_app
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename

from app.core.exceptions import ValidationError
from app.core.route_helpers import handle_service_errors
from app.modules.encounters import services as encounter_services
from app.modules.investigations import services
from app.modules.investigations.forms import ImagingOrderForm, ImagingStudyForm, LabOrderForm
from app.modules.investigations.models import ORDER_STATUS_COLLECTED, ORDER_STATUS_REQUESTED
from app.storage.local_backend import get_storage_backend

bp = Blueprint("investigations", __name__, url_prefix="/investigations")

ALLOWED_IMAGING_TYPES = {"application/pdf", "image/jpeg", "image/png"}


@bp.route("/orders/<int:order_id>")
@login_required
@handle_service_errors
def view_order(order_id):
    order = services.get_order(current_user, order_id)
    return render_template("investigations/order_detail.html", order=order)


@bp.route("/encounters/<int:encounter_id>/orders/lab", methods=["GET", "POST"])
@login_required
@handle_service_errors
def new_lab_order(encounter_id):
    encounter = encounter_services.get_encounter(current_user, encounter_id)
    services.ensure_catalogue_seeded()
    form = LabOrderForm()
    form.panel_id.choices = [(0, "-- No panel --")] + [(p.id, p.name) for p in services.list_panels(current_user)]
    lab_tests = services.list_lab_catalogue(current_user)

    if form.validate_on_submit():
        selected_tests = [int(x) for x in request.form.getlist("catalogue_item_ids")]
        panel_id = form.panel_id.data if form.panel_id.data else None
        try:
            order = services.create_lab_order(
                current_user,
                encounter,
                panel_id=panel_id,
                catalogue_item_ids=selected_tests,
                clinical_indication=form.clinical_indication.data,
                priority=form.priority.data,
            )
        except ValidationError as e:
            flash(str(e), "danger")
        else:
            flash("Laboratory order placed.", "success")
            return redirect(url_for("investigations.view_order", order_id=order.id))

    return render_template(
        "investigations/lab_order_form.html",
        form=form,
        encounter=encounter,
        lab_tests=lab_tests,
        selected_ids=set(int(x) for x in request.form.getlist("catalogue_item_ids")),
    )


@bp.route("/encounters/<int:encounter_id>/orders/imaging", methods=["GET", "POST"])
@login_required
@handle_service_errors
def new_imaging_order(encounter_id):
    encounter = encounter_services.get_encounter(current_user, encounter_id)
    services.ensure_catalogue_seeded()
    form = ImagingOrderForm()
    form.catalogue_item_id.choices = [(0, "-- Select --")] + [
        (i.id, i.name) for i in services.list_imaging_catalogue(current_user)
    ]

    if form.validate_on_submit():
        try:
            order = services.create_imaging_order(
                current_user,
                encounter,
                catalogue_item_id=form.catalogue_item_id.data,
                clinical_indication=form.clinical_indication.data,
                priority=form.priority.data,
            )
        except ValidationError as e:
            flash(str(e), "danger")
        else:
            flash("Imaging order placed.", "success")
            return redirect(url_for("investigations.view_order", order_id=order.id))

    return render_template("investigations/imaging_order_form.html", form=form, encounter=encounter)


@bp.route("/orders/<int:order_id>/collect", methods=["POST"])
@login_required
@handle_service_errors
def mark_order_collected(order_id):
    order = services.get_order(current_user, order_id)
    try:
        services.transition_order_status(current_user, order, ORDER_STATUS_COLLECTED)
        flash("Order marked collected.", "success")
    except ValidationError as e:
        flash(str(e), "danger")
    return redirect(url_for("investigations.view_order", order_id=order.id))


@bp.route("/orders/<int:order_id>/review", methods=["POST"])
@login_required
@handle_service_errors
def review_order(order_id):
    from app.modules.investigations.models import ORDER_STATUS_REVIEWED

    order = services.get_order(current_user, order_id)
    try:
        services.transition_order_status(current_user, order, ORDER_STATUS_REVIEWED)
        flash("Order marked reviewed.", "success")
    except ValidationError as e:
        flash(str(e), "danger")
    return redirect(url_for("investigations.view_order", order_id=order.id))


@bp.route("/orders/<int:order_id>/results/lab", methods=["GET", "POST"])
@login_required
@handle_service_errors
def enter_lab_results_for_order(order_id):
    order = services.get_order(current_user, order_id)
    encounter = encounter_services.get_encounter(current_user, order.encounter_id)
    lab_tests = services.list_lab_catalogue(current_user)

    if request.method == "POST":
        if order.status == ORDER_STATUS_REQUESTED:
            services.transition_order_status(current_user, order, ORDER_STATUS_COLLECTED)
        result_set = services.create_lab_result_set(current_user, encounter, order_id=order.id)
        values = {}
        for test in lab_tests:
            raw = request.form.get(f"value_{test.id}", "")
            if raw:
                values[test.id] = raw
        try:
            services.save_lab_values(current_user, result_set, values)
            if "mark_available" in request.form:
                services.mark_lab_result_available(current_user, result_set)
                flash("Laboratory results saved and marked available.", "success")
            else:
                flash("Laboratory results saved as draft.", "success")
        except ValidationError as e:
            flash(str(e), "danger")
        else:
            return redirect(url_for("investigations.view_lab_result", result_set_id=result_set.id))

    return render_template(
        "investigations/lab_result_form.html",
        encounter=encounter,
        order=order,
        lab_tests=lab_tests,
        result_set=None,
    )


@bp.route("/encounters/<int:encounter_id>/results/lab/new", methods=["GET", "POST"])
@login_required
@handle_service_errors
def new_lab_results(encounter_id):
    encounter = encounter_services.get_encounter(current_user, encounter_id)
    lab_tests = services.list_lab_catalogue(current_user)

    if request.method == "POST":
        result_set = services.create_lab_result_set(current_user, encounter)
        values = {}
        for test in lab_tests:
            raw = request.form.get(f"value_{test.id}", "")
            if raw:
                values[test.id] = raw
        try:
            services.save_lab_values(current_user, result_set, values)
            if "mark_available" in request.form:
                services.mark_lab_result_available(current_user, result_set)
            flash("Laboratory results saved.", "success")
        except ValidationError as e:
            flash(str(e), "danger")
        else:
            return redirect(url_for("investigations.view_lab_result", result_set_id=result_set.id))

    return render_template(
        "investigations/lab_result_form.html",
        encounter=encounter,
        order=None,
        lab_tests=lab_tests,
        result_set=None,
    )


@bp.route("/results/lab/<int:result_set_id>")
@login_required
@handle_service_errors
def view_lab_result(result_set_id):
    result_set = services.get_lab_result_set(current_user, result_set_id)
    return render_template("investigations/lab_result_detail.html", result_set=result_set)


@bp.route("/results/lab/<int:result_set_id>/review", methods=["POST"])
@login_required
@handle_service_errors
def review_lab_result(result_set_id):
    result_set = services.get_lab_result_set(current_user, result_set_id)
    try:
        services.review_lab_result_set(current_user, result_set)
        flash("Laboratory results reviewed.", "success")
    except ValidationError as e:
        flash(str(e), "danger")
    return redirect(url_for("investigations.view_lab_result", result_set_id=result_set.id))


@bp.route("/encounters/<int:encounter_id>/imaging/new", methods=["GET", "POST"])
@login_required
@handle_service_errors
def new_imaging_study(encounter_id):
    encounter = encounter_services.get_encounter(current_user, encounter_id)
    form = ImagingStudyForm()
    form.catalogue_item_id.choices = [(0, "-- Select --")] + [
        (i.id, i.name) for i in services.list_imaging_catalogue(current_user)
    ]

    if form.validate_on_submit():
        try:
            study = services.create_imaging_study(
                current_user,
                encounter,
                catalogue_item_id=form.catalogue_item_id.data,
                study_date=form.study_date.data,
                body_region=form.body_region.data,
                findings_summary=form.findings_summary.data,
                impression=form.impression.data,
            )
            upload = request.files.get("report_file")
            if upload and upload.filename:
                if upload.content_type not in ALLOWED_IMAGING_TYPES:
                    raise ValidationError("Unsupported file type. Use PDF, JPEG, or PNG.")
                ext = os.path.splitext(secure_filename(upload.filename))[1] or ".pdf"
                key = f"imaging/{encounter.patient_id}/{study.id}/{uuid.uuid4().hex}{ext}"
                storage = get_storage_backend(current_app.config)
                storage.save(key, upload.stream)
                services.attach_imaging_file(
                    current_user, study, key, upload.content_type, secure_filename(upload.filename)
                )
            if "mark_available" in request.form:
                services.mark_imaging_available(current_user, study)
            flash("Imaging study saved.", "success")
            return redirect(url_for("investigations.view_imaging", study_id=study.id))
        except ValidationError as e:
            flash(str(e), "danger")

    return render_template("investigations/imaging_form.html", form=form, encounter=encounter, study=None)


@bp.route("/imaging/<int:study_id>")
@login_required
@handle_service_errors
def view_imaging(study_id):
    study = services.get_imaging_study(current_user, study_id)
    return render_template("investigations/imaging_detail.html", study=study)


@bp.route("/imaging/<int:study_id>/review", methods=["POST"])
@login_required
@handle_service_errors
def review_imaging(study_id):
    study = services.get_imaging_study(current_user, study_id)
    try:
        services.review_imaging_study(current_user, study)
        flash("Imaging study reviewed.", "success")
    except ValidationError as e:
        flash(str(e), "danger")
    return redirect(url_for("investigations.view_imaging", study_id=study.id))
