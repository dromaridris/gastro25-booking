from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.core.exceptions import ValidationError
from app.core.route_helpers import handle_service_errors
from app.engines import permission_engine
from app.modules.appointments import services as appointment_services
from app.modules.encounters import services as encounter_services
from app.modules.investigations import services as investigation_services
from app.modules.medications import services as medication_services
from app.modules.clinical_history import services as history_services
from app.modules.patients import services
from app.modules.patients.forms import ArchivePatientForm, PatientForm, PatientSearchForm

bp = Blueprint("patients", __name__, url_prefix="/patients")


@bp.route("/")
@login_required
@handle_service_errors
def list_patients():
    search_form = PatientSearchForm(request.args)
    query = request.args.get("q", "").strip() or None
    patients = services.search_patients(current_user, query=query)
    return render_template("patients/list.html", patients=patients, search_form=search_form, query=query)


@bp.route("/new", methods=["GET", "POST"])
@login_required
@handle_service_errors
def create_patient():
    form = PatientForm()
    if form.validate_on_submit():
        try:
            patient = services.create_patient(
                acting_user=current_user,
                first_name=form.first_name.data,
                last_name=form.last_name.data,
                date_of_birth=form.date_of_birth.data,
                sex=form.sex.data,
                phone=form.phone.data,
                email=form.email.data,
                address=form.address.data,
                national_id=form.national_id.data,
                emergency_contact_name=form.emergency_contact_name.data,
                emergency_contact_phone=form.emergency_contact_phone.data,
            )
        except ValidationError as e:
            flash(str(e), "danger")
            return render_template("patients/form.html", form=form, mode="create")

        flash(f"Patient created (MRN {patient.mrn}).", "success")
        return redirect(url_for("patients.view_patient", patient_id=patient.id))

    return render_template("patients/form.html", form=form, mode="create")


@bp.route("/<int:patient_id>")
@login_required
@handle_service_errors
def view_patient(patient_id):
    patient = services.get_patient(current_user, patient_id)

    appointments = []
    if permission_engine.check(current_user, "appointment:view"):
        appointments = appointment_services.search_appointments(
            current_user, patient_id=patient.id
        )

    encounters = []
    if permission_engine.check(current_user, "encounter:view"):
        encounters = encounter_services.list_encounters_for_patient(current_user, patient.id)

    timeline = []
    if permission_engine.check(current_user, "investigation:view"):
        timeline = investigation_services.patient_timeline(current_user, patient.id)

    active_medications = []
    medication_timeline = []
    if permission_engine.check(current_user, "medication:view"):
        active_medications = medication_services.active_medications_for_patient(current_user, patient.id)
        medication_timeline = medication_services.patient_medication_timeline(current_user, patient.id)

    history_timeline = []
    follow_ups = []
    if permission_engine.check(current_user, "history:view"):
        history_timeline = history_services.patient_history_timeline(current_user, patient.id)
        follow_ups = history_services.list_follow_ups_for_patient(current_user, patient.id)

    documents = []
    if permission_engine.check(current_user, "patient_document:view"):
        from app.modules.patient_documents import services as doc_services
        documents = doc_services.list_for_patient(current_user, patient.id)

    return render_template(
        "patients/detail.html",
        patient=patient,
        appointments=appointments,
        encounters=encounters,
        timeline=timeline,
        active_medications=active_medications,
        medication_timeline=medication_timeline,
        history_timeline=history_timeline,
        follow_ups=follow_ups,
        documents=documents,
    )


@bp.route("/<int:patient_id>/edit", methods=["GET", "POST"])
@login_required
@handle_service_errors
def edit_patient(patient_id):
    target = services.get_patient(current_user, patient_id)
    form = PatientForm(obj=target)
    if form.validate_on_submit():
        try:
            services.update_patient(
                acting_user=current_user,
                target_patient=target,
                first_name=form.first_name.data,
                last_name=form.last_name.data,
                date_of_birth=form.date_of_birth.data,
                sex=form.sex.data,
                phone=form.phone.data,
                email=form.email.data,
                address=form.address.data,
                national_id=form.national_id.data,
                emergency_contact_name=form.emergency_contact_name.data,
                emergency_contact_phone=form.emergency_contact_phone.data,
            )
        except ValidationError as e:
            flash(str(e), "danger")
            return render_template("patients/form.html", form=form, mode="edit", target=target)

        flash("Patient updated.", "success")
        return redirect(url_for("patients.view_patient", patient_id=target.id))

    return render_template("patients/form.html", form=form, mode="edit", target=target)


@bp.route("/<int:patient_id>/archive", methods=["GET", "POST"])
@login_required
@handle_service_errors
def archive_patient(patient_id):
    target = services.get_patient(current_user, patient_id)
    form = ArchivePatientForm()
    if form.validate_on_submit():
        services.archive_patient(current_user, target, reason=form.reason.data)
        flash("Patient archived.", "success")
        return redirect(url_for("patients.view_patient", patient_id=target.id))

    return render_template("patients/archive.html", form=form, target=target)


@bp.route("/<int:patient_id>/restore", methods=["POST"])
@login_required
@handle_service_errors
def restore_patient(patient_id):
    target = services.get_patient(current_user, patient_id)
    services.restore_patient(current_user, target)
    flash("Patient restored.", "success")
    return redirect(url_for("patients.view_patient", patient_id=target.id))
