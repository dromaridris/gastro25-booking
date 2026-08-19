from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.core.exceptions import ValidationError
from app.core.route_helpers import handle_service_errors
from app.modules.encounters import services
from app.modules.encounters.forms import EncounterForm
from app.modules.investigations.models import InvestigationOrder
from app.modules.patients import services as patient_services

bp = Blueprint("encounters", __name__, url_prefix="/encounters")


@bp.route("/")
@login_required
@handle_service_errors
def list_encounters():
    encounters = services.list_open_encounters(current_user)
    return render_template("encounters/list.html", encounters=encounters)


@bp.route("/new", methods=["GET", "POST"])
@login_required
@handle_service_errors
def new_encounter():
    patient_id = request.args.get("patient_id", type=int)
    if not patient_id:
        flash("Patient is required to start an encounter.", "danger")
        return redirect(url_for("patients.list_patients"))

    patient = patient_services.get_patient(current_user, patient_id)
    form = EncounterForm()
    if form.validate_on_submit():
        try:
            encounter = services.create_encounter(
                current_user,
                patient_id=patient.id,
                encounter_type=form.encounter_type.data or "opd",
                summary=form.summary.data,
            )
        except ValidationError as e:
            flash(str(e), "danger")
            return render_template("encounters/form.html", form=form, patient=patient)
        flash("Encounter started.", "success")
        return redirect(url_for("encounters.view_encounter", encounter_id=encounter.id))
    return render_template("encounters/form.html", form=form, patient=patient)


@bp.route("/<int:encounter_id>")
@login_required
@handle_service_errors
def view_encounter(encounter_id):
    encounter = services.get_encounter(current_user, encounter_id)
    orders = InvestigationOrder.query.filter_by(encounter_id=encounter.id, is_archived=False).all()
    return render_template("encounters/detail.html", encounter=encounter, orders=orders)


@bp.route("/<int:encounter_id>/close", methods=["POST"])
@login_required
@handle_service_errors
def close_encounter(encounter_id):
    encounter = services.get_encounter(current_user, encounter_id)
    try:
        services.close_encounter(current_user, encounter)
    except ValidationError as e:
        flash(str(e), "danger")
    else:
        flash("Encounter closed.", "success")
    return redirect(url_for("encounters.view_encounter", encounter_id=encounter.id))
