from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.core.route_helpers import handle_service_errors
from app.modules.data_exchange import services

bp = Blueprint("data_exchange", __name__, url_prefix="/data-exchange")


@bp.route("/")
@login_required
@handle_service_errors
def index():
    jobs = services.list_jobs(current_user)
    return render_template("data_exchange/index.html", jobs=jobs)


@bp.route("/export/patients", methods=["POST"])
@login_required
@handle_service_errors
def export_patients():
    fmt = request.form.get("format", "csv")
    job = services.export_patients(current_user, fmt=fmt)
    flash(f"Export completed — {job.record_count or 0} records.", "success")
    return redirect(url_for("data_exchange.index"))
