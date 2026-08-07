from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.core.exceptions import ValidationError
from app.core.route_helpers import handle_service_errors
from app.modules.consult_requests import services

bp = Blueprint("consult_requests", __name__, url_prefix="/consult-requests")


@bp.route("/")
@login_required
@handle_service_errors
def list_requests():
    status = request.args.get("status")
    requests_list = services.list_requests(current_user, status=status)
    return render_template("consult_requests/list.html", requests=requests_list, status=status)


@bp.route("/<int:request_id>")
@login_required
@handle_service_errors
def detail(request_id):
    req = services.get_request(current_user, request_id)
    return render_template("consult_requests/detail.html", req=req)


@bp.route("/new", methods=["GET", "POST"])
@login_required
@handle_service_errors
def create_request():
    if request.method == "POST":
        try:
            req = services.create(
                current_user,
                patient_id=request.form.get("patient_id", type=int),
                specialty=request.form.get("specialty", ""),
                clinical_question=request.form.get("clinical_question", ""),
                urgency=request.form.get("urgency", "routine"),
                encounter_id=request.form.get("encounter_id", type=int) or None,
            )
            flash("Consult request submitted.", "success")
            return redirect(url_for("consult_requests.detail", request_id=req.id))
        except ValidationError as e:
            flash(str(e), "danger")
    return render_template("consult_requests/form.html")


@bp.route("/<int:request_id>/accept", methods=["POST"])
@login_required
@handle_service_errors
def accept(request_id):
    services.accept(current_user, request_id)
    flash("Consult accepted.", "success")
    return redirect(url_for("consult_requests.detail", request_id=request_id))


@bp.route("/<int:request_id>/complete", methods=["POST"])
@login_required
@handle_service_errors
def complete(request_id):
    services.complete(current_user, request_id, response_notes=request.form.get("response_notes", ""))
    flash("Consult completed.", "success")
    return redirect(url_for("consult_requests.detail", request_id=request_id))


@bp.route("/<int:request_id>/reject", methods=["POST"])
@login_required
@handle_service_errors
def reject(request_id):
    services.reject(current_user, request_id, reason=request.form.get("reason", ""))
    flash("Consult rejected.", "success")
    return redirect(url_for("consult_requests.detail", request_id=request_id))


@bp.route("/<int:request_id>/cancel", methods=["POST"])
@login_required
@handle_service_errors
def cancel(request_id):
    services.cancel(current_user, request_id)
    flash("Consult cancelled.", "success")
    return redirect(url_for("consult_requests.list_requests"))
