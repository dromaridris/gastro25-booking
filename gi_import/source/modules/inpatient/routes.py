from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.core.exceptions import ValidationError
from app.core.route_helpers import handle_service_errors
from app.modules.inpatient import services
from app.modules.inpatient.models import BED_AVAILABLE, BED_CLEANING, BED_ISOLATION

bp = Blueprint("inpatient", __name__, url_prefix="/inpatient")


@bp.route("/")
@login_required
@handle_service_errors
def board():
    ward_id = request.args.get("ward_id", type=int)
    board_data = services.list_board(current_user, ward_id=ward_id)
    return render_template("inpatient/board.html", board=board_data, ward_id=ward_id)


@bp.route("/beds/<int:bed_id>/admit", methods=["POST"])
@login_required
@handle_service_errors
def admit_patient(bed_id):
    patient_id = request.form.get("patient_id", type=int)
    try:
        services.admit(current_user, bed_id=bed_id, patient_id=patient_id, notes=request.form.get("notes"))
        flash("Patient admitted.", "success")
    except ValidationError as e:
        flash(str(e), "danger")
    return redirect(url_for("inpatient.board"))


@bp.route("/beds/<int:bed_id>/discharge", methods=["POST"])
@login_required
@handle_service_errors
def discharge_patient(bed_id):
    try:
        services.discharge(current_user, bed_id=bed_id, notes=request.form.get("notes"))
        flash("Patient discharged.", "success")
    except ValidationError as e:
        flash(str(e), "danger")
    return redirect(url_for("inpatient.board"))


@bp.route("/beds/<int:from_bed_id>/transfer/<int:to_bed_id>", methods=["POST"])
@login_required
@handle_service_errors
def transfer_patient(from_bed_id, to_bed_id):
    try:
        services.transfer(current_user, from_bed_id=from_bed_id, to_bed_id=to_bed_id, notes=request.form.get("notes"))
        flash("Patient transferred.", "success")
    except ValidationError as e:
        flash(str(e), "danger")
    return redirect(url_for("inpatient.board"))


@bp.route("/beds/<int:bed_id>/status", methods=["POST"])
@login_required
@handle_service_errors
def set_status(bed_id):
    status = request.form.get("status", BED_AVAILABLE)
    try:
        services.set_bed_status(current_user, bed_id, status)
        flash(f"Bed marked {status}.", "success")
    except ValidationError as e:
        flash(str(e), "danger")
    return redirect(url_for("inpatient.board"))
