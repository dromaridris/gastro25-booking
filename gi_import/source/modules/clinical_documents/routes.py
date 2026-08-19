from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.core.route_helpers import handle_service_errors
from app.modules.clinical_documents import services

bp = Blueprint("clinical_documents", __name__, url_prefix="/clinical-documents")


@bp.route("/consents/patient/<int:patient_id>")
@login_required
@handle_service_errors
def consent_list(patient_id):
    templates = services.list_templates(current_user)
    records = services.list_consents_for_patient(current_user, patient_id)
    return render_template(
        "clinical_documents/consent_list.html",
        patient_id=patient_id,
        templates=templates,
        records=records,
    )


@bp.route("/consents/new", methods=["POST"])
@login_required
@handle_service_errors
def consent_create():
    rec = services.create_consent(
        current_user,
        template_id=request.form.get("template_id", type=int),
        patient_id=request.form.get("patient_id", type=int),
        encounter_id=request.form.get("encounter_id", type=int) or None,
        procedure_id=request.form.get("procedure_id", type=int) or None,
    )
    return redirect(url_for("clinical_documents.consent_sign", record_id=rec.id))


@bp.route("/consents/<int:record_id>")
@login_required
@handle_service_errors
def consent_sign(record_id):
    rec = services.get_consent(current_user, record_id)
    return render_template("clinical_documents/consent_sign.html", record=rec)


@bp.route("/consents/<int:record_id>/sign", methods=["POST"])
@login_required
@handle_service_errors
def consent_do_sign(record_id):
    services.sign_consent(current_user, record_id, witness_name=request.form.get("witness_name"))
    flash("Consent signed.", "success")
    return redirect(url_for("clinical_documents.consent_print", record_id=record_id))


@bp.route("/consents/<int:record_id>/print")
@login_required
@handle_service_errors
def consent_print(record_id):
    rec = services.get_consent(current_user, record_id)
    return render_template("clinical_documents/consent_print.html", record=rec)


@bp.route("/discharge-summary/<int:encounter_id>")
@login_required
@handle_service_errors
def discharge_summary(encounter_id):
    from app.modules.encounters import services as encounter_services
    encounter = encounter_services.get_encounter(current_user, encounter_id)
    return render_template(
        "clinical_documents/discharge_summary.html",
        encounter=encounter,
        doc_ai_url=url_for("documentation_ai.list_templates"),
    )


@bp.route("/certificate/<int:patient_id>")
@login_required
@handle_service_errors
def certificate_print(patient_id):
    from app.modules.patients import services as patient_services
    patient = patient_services.get_patient(current_user, patient_id)
    return render_template("clinical_documents/certificate_print.html", patient=patient)


@bp.route("/letter/<int:patient_id>")
@login_required
@handle_service_errors
def letter_print(patient_id):
    from app.modules.patients import services as patient_services
    patient = patient_services.get_patient(current_user, patient_id)
    return render_template("clinical_documents/letter_print.html", patient=patient)
