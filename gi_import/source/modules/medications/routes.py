from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.core.exceptions import ValidationError
from app.core.route_helpers import handle_service_errors
from app.modules.encounters import services as encounter_services
from app.modules.medications import services
from app.modules.medications.forms import MedicationEntryForm

bp = Blueprint("medications", __name__, url_prefix="/medications")


@bp.route("/encounters/<int:encounter_id>")
@login_required
@handle_service_errors
def list_encounter_medications(encounter_id):
    encounter = encounter_services.get_encounter(current_user, encounter_id)
    entries = services.list_entries_for_encounter(current_user, encounter_id)
    return render_template(
        "medications/encounter_list.html",
        encounter=encounter,
        entries=entries,
    )


@bp.route("/encounters/<int:encounter_id>/new", methods=["GET", "POST"])
@login_required
@handle_service_errors
def new_medication_entry(encounter_id):
    encounter = encounter_services.get_encounter(current_user, encounter_id)
    services.ensure_catalogue_seeded()
    form = MedicationEntryForm()
    form.catalogue_item_id.choices = [(0, "-- Select --")] + [
        (m.id, m.name) for m in services.list_catalogue(current_user)
    ]

    if form.validate_on_submit():
        if form.catalogue_item_id.data == 0:
            flash("Select a medication.", "danger")
        else:
            try:
                mark_active = "save_as_draft" not in request.form
                services.create_medication_entry(
                    current_user,
                    encounter,
                    catalogue_item_id=form.catalogue_item_id.data,
                    entry_type=form.entry_type.data,
                    dose_text=form.dose_text.data,
                    route=form.route.data,
                    frequency_text=form.frequency_text.data,
                    indication=form.indication.data,
                    started_on=form.started_on.data,
                    notes=form.notes.data,
                    mark_active=mark_active,
                )
            except ValidationError as e:
                flash(str(e), "danger")
            else:
                flash("Medication entry saved.", "success")
                return redirect(url_for("medications.list_encounter_medications", encounter_id=encounter.id))

    return render_template("medications/form.html", form=form, encounter=encounter)


@bp.route("/entries/<int:entry_id>")
@login_required
@handle_service_errors
def view_entry(entry_id):
    entry = services.get_entry(current_user, entry_id)
    return render_template("medications/detail.html", entry=entry)


@bp.route("/entries/<int:entry_id>/stop", methods=["POST"])
@login_required
@handle_service_errors
def stop_entry(entry_id):
    entry = services.get_entry(current_user, entry_id)
    try:
        services.stop_entry(current_user, entry)
        flash("Medication marked stopped.", "success")
    except ValidationError as e:
        flash(str(e), "danger")
    return redirect(url_for("medications.view_entry", entry_id=entry.id))


@bp.route("/entries/<int:entry_id>/review", methods=["POST"])
@login_required
@handle_service_errors
def review_entry(entry_id):
    entry = services.get_entry(current_user, entry_id)
    try:
        services.review_entry(current_user, entry)
        flash("Medication entry reviewed.", "success")
    except ValidationError as e:
        flash(str(e), "danger")
    return redirect(url_for("medications.view_entry", entry_id=entry.id))
