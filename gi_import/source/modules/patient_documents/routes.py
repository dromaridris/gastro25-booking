from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.core.exceptions import ValidationError
from app.core.route_helpers import handle_service_errors
from app.modules.patient_documents import services

bp = Blueprint("patient_documents", __name__, url_prefix="/patient-documents")


@bp.route("/patients/<int:patient_id>")
@login_required
@handle_service_errors
def list_documents(patient_id):
    from app.modules.patients import services as patient_services
    patient = patient_services.get_patient(current_user, patient_id)
    docs = services.list_for_patient(current_user, patient_id)
    return render_template("patient_documents/list.html", patient=patient, documents=docs)


@bp.route("/patients/<int:patient_id>/upload", methods=["POST"])
@login_required
@handle_service_errors
def upload(patient_id):
    upload_file = request.files.get("file")
    try:
        services.upload(
            current_user,
            patient_id=patient_id,
            title=request.form.get("title", ""),
            file_obj=upload_file.stream if upload_file else None,
            filename=upload_file.filename if upload_file else "",
            content_type=upload_file.content_type if upload_file else None,
            category=request.form.get("category", "general"),
            encounter_id=request.form.get("encounter_id", type=int) or None,
            notes=request.form.get("notes"),
        )
        flash("Document uploaded.", "success")
    except ValidationError as e:
        flash(str(e), "danger")
    return redirect(request.referrer or url_for("patients.view_patient", patient_id=patient_id))
