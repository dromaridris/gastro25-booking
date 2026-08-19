from datetime import date

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.core.exceptions import ValidationError
from app.core.route_helpers import handle_service_errors
from app.modules.education import services

bp = Blueprint("education", __name__, url_prefix="/education")


@bp.route("/")
@login_required
@handle_service_errors
def list_activities():
    activities = services.list_activities(current_user)
    return render_template("education/list.html", activities=activities)


@bp.route("/<int:activity_id>")
@login_required
@handle_service_errors
def detail(activity_id):
    activity = services.get_activity(current_user, activity_id)
    return render_template("education/detail.html", activity=activity)


@bp.route("/new", methods=["GET", "POST"])
@login_required
@handle_service_errors
def create():
    if request.method == "POST":
        try:
            act = services.create(
                current_user,
                title=request.form.get("title", ""),
                activity_type=request.form.get("activity_type", "teaching"),
                activity_date=date.fromisoformat(request.form.get("activity_date")),
                description=request.form.get("description"),
                duration_minutes=request.form.get("duration_minutes", type=int),
                location=request.form.get("location"),
            )
            flash("Education activity recorded.", "success")
            return redirect(url_for("education.detail", activity_id=act.id))
        except (ValidationError, ValueError) as e:
            flash(str(e), "danger")
    return render_template("education/form.html", mode="create")


@bp.route("/<int:activity_id>/edit", methods=["GET", "POST"])
@login_required
@handle_service_errors
def edit(activity_id):
    activity = services.get_activity(current_user, activity_id)
    if request.method == "POST":
        try:
            services.update(
                current_user,
                activity_id,
                title=request.form.get("title"),
                activity_type=request.form.get("activity_type"),
                activity_date=date.fromisoformat(request.form.get("activity_date")),
                description=request.form.get("description"),
                duration_minutes=request.form.get("duration_minutes", type=int),
                location=request.form.get("location"),
            )
            flash("Activity updated.", "success")
            return redirect(url_for("education.detail", activity_id=activity_id))
        except (ValidationError, ValueError) as e:
            flash(str(e), "danger")
    return render_template("education/form.html", mode="edit", activity=activity)
