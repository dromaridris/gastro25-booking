"""Research Platform routes — Sprint 5A-RES / 6B variable framework."""

from flask import Blueprint, Response, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.core.route_helpers import handle_service_errors
from app.modules.patients import services as patient_services
from app.modules.research import services
from app.modules.research import study_services
from app.modules.research import variable_framework

bp = Blueprint("research", __name__, url_prefix="/research")


@bp.route("/")
@login_required
@handle_service_errors
def list_registries():
    registries = services.list_registries(current_user)
    return render_template("research/list.html", registries=registries)


@bp.route("/registries/<registry_code>")
@login_required
@handle_service_errors
def registry_detail(registry_code):
    registry = services.get_registry(current_user, registry_code)
    variables = services.list_variables(current_user, registry_code)
    groups = variable_framework.list_groups(current_user, registry_code)
    enrollments = services.list_enrollments(current_user, registry_code)
    _, preview_rows = services.build_dataset(current_user, registry_code)
    return render_template(
        "research/detail.html",
        registry=registry,
        variables=variables,
        groups=groups,
        enrollments=enrollments,
        preview_rows=preview_rows[:20],
    )


@bp.route("/registries/<registry_code>/variables/new", methods=["GET", "POST"])
@login_required
@handle_service_errors
def create_variable(registry_code):
    if request.method == "POST":
        variable_framework.create_variable(
            current_user,
            registry_code=registry_code,
            code=request.form["code"],
            stable_id=request.form.get("stable_id") or request.form["code"],
            name=request.form["name"],
            source_type=request.form["source_type"],
            source_key=request.form["source_key"],
            data_type=request.form.get("data_type", "text"),
            value_origin=request.form.get("value_origin", "clinical_reference"),
            source_module=request.form.get("source_module") or None,
            group_code=request.form.get("group_code") or None,
            category=request.form.get("category") or None,
            description=request.form.get("description") or None,
            is_required=bool(request.form.get("is_required")),
        )
        flash("Research variable created.", "success")
        return redirect(url_for("research.registry_detail", registry_code=registry_code))
    return render_template("research/variable_form.html", registry_code=registry_code, variable=None)


@bp.route("/variables/<variable_code>/edit", methods=["GET", "POST"])
@login_required
@handle_service_errors
def edit_variable(variable_code):
    variable = variable_framework.get_variable(current_user, variable_code)
    if request.method == "POST":
        variable_framework.update_variable(
            current_user,
            variable_code,
            name=request.form["name"],
            description=request.form.get("description") or None,
            is_required=bool(request.form.get("is_required")),
            is_active=bool(request.form.get("is_active", True)),
        )
        flash("Research variable updated.", "success")
        return redirect(url_for("research.registry_detail", registry_code=variable.registry_code))
    versions = variable_framework.list_variable_versions(current_user, variable_code)
    return render_template(
        "research/variable_form.html",
        registry_code=variable.registry_code,
        variable=variable,
        versions=versions,
    )


@bp.route("/registries/<registry_code>/enroll", methods=["POST"])
@login_required
@handle_service_errors
def enroll_patient(registry_code):
    patient_id = request.form.get("patient_id", type=int)
    if not patient_id:
        flash("Patient ID required.", "danger")
        return redirect(url_for("research.registry_detail", registry_code=registry_code))
    services.enroll_patient(current_user, registry_code, patient_id)
    flash("Patient enrolled.", "success")
    return redirect(url_for("research.registry_detail", registry_code=registry_code))


@bp.route("/registries/<registry_code>/withdraw/<int:enrollment_id>", methods=["POST"])
@login_required
@handle_service_errors
def withdraw_enrollment(registry_code, enrollment_id):
    services.withdraw_enrollment(current_user, enrollment_id)
    flash("Enrollment withdrawn.", "success")
    return redirect(url_for("research.registry_detail", registry_code=registry_code))


@bp.route("/registries/<registry_code>/export.csv")
@login_required
@handle_service_errors
def export_csv(registry_code):
    csv_data = services.export_dataset_csv(current_user, registry_code)
    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={registry_code}_dataset.csv"},
    )


@bp.route("/patients/<int:patient_id>/enroll/<registry_code>", methods=["POST"])
@login_required
@handle_service_errors
def enroll_from_patient(patient_id, registry_code):
    patient_services.get_patient(current_user, patient_id)
    services.enroll_patient(current_user, registry_code, patient_id)
    flash("Patient enrolled in registry.", "success")
    return redirect(url_for("patients.view_patient", patient_id=patient_id))


# ---------------------------------------------------------------------------
# Sprint 6C — Research studies
# ---------------------------------------------------------------------------


@bp.route("/studies")
@login_required
@handle_service_errors
def list_studies():
    studies = study_services.list_studies(current_user)
    return render_template("research/studies/list.html", studies=studies)


@bp.route("/studies/new", methods=["GET", "POST"])
@login_required
@handle_service_errors
def create_study():
    registries = services.list_registries(current_user)
    if request.method == "POST":
        study = study_services.create_study(
            current_user,
            study_code=request.form["study_code"],
            title=request.form["title"],
            registry_code=request.form["registry_code"],
            description=request.form.get("description") or None,
            ethics_approval_number=request.form.get("ethics_approval_number") or None,
            auto_enroll_enabled=bool(request.form.get("auto_enroll_enabled")),
        )
        flash("Research study created.", "success")
        return redirect(url_for("research.study_detail", study_code=study.study_code))
    return render_template("research/studies/form.html", registries=registries, study=None)


@bp.route("/studies/<study_code>")
@login_required
@handle_service_errors
def study_detail(study_code):
    study = study_services.get_study(current_user, study_code)
    cases = study_services.list_cases(current_user, study_code)
    return render_template("research/studies/detail.html", study=study, cases=cases)


@bp.route("/studies/<study_code>/enroll", methods=["POST"])
@login_required
@handle_service_errors
def enroll_study_case(study_code):
    patient_id = request.form.get("patient_id", type=int)
    if not patient_id:
        flash("Patient ID required.", "danger")
        return redirect(url_for("research.study_detail", study_code=study_code))
    study_services.enroll_case(current_user, study_code, patient_id)
    flash("Patient enrolled in study.", "success")
    return redirect(url_for("research.study_detail", study_code=study_code))


@bp.route("/studies/<study_code>/screen", methods=["POST"])
@login_required
@handle_service_errors
def screen_study_patient(study_code):
    patient_id = request.form.get("patient_id", type=int)
    if not patient_id:
        flash("Patient ID required.", "danger")
        return redirect(url_for("research.study_detail", study_code=study_code))
    entry = study_services.screen_patient(current_user, study_code, patient_id)
    flash(f"Screening outcome: {entry.outcome}.", "info")
    return redirect(url_for("research.study_detail", study_code=study_code))


@bp.route("/studies/<study_code>/export.<export_format>")
@login_required
@handle_service_errors
def export_study(study_code, export_format):
    fmt, payload = study_services.export_study(
        current_user,
        study_code,
        export_format=export_format,
        freeze_snapshot=bool(request.args.get("snapshot")),
        snapshot_name=request.args.get("snapshot_name"),
    )
    if fmt == "xlsx":
        return Response(
            payload,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={study_code}_export.xlsx"},
        )
    return Response(
        payload,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={study_code}_export.csv"},
    )
