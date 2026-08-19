"""Workforce & Training Platform routes — Sprint 7A."""

from datetime import date

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.core.route_helpers import handle_service_errors
from app.modules.workforce import dashboard_services, services

bp = Blueprint("workforce", __name__, url_prefix="/workforce")


@bp.route("/")
@login_required
@handle_service_errors
def home():
    page = dashboard_services.get_role_homepage(current_user)
    return render_template(page["template"], **page["data"])


@bp.route("/portfolio")
@login_required
@handle_service_errors
def portfolio():
    user_id = request.args.get("user_id", type=int)
    services.sync_user_portfolio(current_user, user_id)
    entries = services.list_portfolio(current_user, user_id)
    totals = services.get_performance(current_user, user_id or current_user.id)
    return render_template(
        "workforce/portfolio.html",
        entries=entries,
        totals=totals,
        target_user_id=user_id or current_user.id,
    )


@bp.route("/portfolio/<int:entry_id>/verify", methods=["POST"])
@login_required
@handle_service_errors
def verify_entry(entry_id):
    action = request.form.get("action", "supervisor")
    if action == "department":
        services.verify_department(current_user, entry_id)
        flash("Entry department-verified.", "success")
    elif action == "lock":
        services.lock_entry(current_user, entry_id)
        flash("Entry locked.", "success")
    else:
        services.verify_supervisor(current_user, entry_id)
        flash("Entry supervisor-verified.", "success")
    return redirect(request.referrer or url_for("workforce.portfolio"))


@bp.route("/attendance/adjust", methods=["POST"])
@login_required
@handle_service_errors
def adjust_attendance():
    adj_date = request.form.get("adjustment_date")
    services.create_attendance_adjustment(
        current_user,
        user_id=request.form.get("user_id", type=int),
        adjustment_date=date.fromisoformat(adj_date) if adj_date else date.today(),
        adjustment_type=request.form.get("adjustment_type"),
        hours=float(request.form.get("hours") or 8),
        notes=request.form.get("notes") or None,
    )
    flash("Attendance adjustment recorded.", "success")
    return redirect(request.referrer or url_for("workforce.home"))


@bp.route("/department")
@login_required
@handle_service_errors
def department_overview():
    data = dashboard_services.get_hod_dashboard(current_user)
    trainees = services.list_department_trainees(current_user)
    return render_template("workforce/hod_dashboard.html", **data, trainees=trainees)


@bp.route("/sync", methods=["POST"])
@login_required
@handle_service_errors
def sync_portfolio():
    services.sync_user_portfolio(current_user)
    flash("Portfolio synced from clinical activity.", "success")
    return redirect(request.referrer or url_for("workforce.portfolio"))
