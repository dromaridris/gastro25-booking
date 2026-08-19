"""Workforce Identity & Duty Management routes — Phase 7E."""

from datetime import date

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.core.route_helpers import handle_service_errors
from app.modules.workforce_identity import (
    dashboard_services,
    duty_services,
    invitation_services,
    lifecycle_services,
    swap_services,
)
from app.modules.workforce_identity.forms import InvitationForm, RegisterForm, SwapRequestForm

bp = Blueprint("workforce_identity", __name__, url_prefix="/workforce-identity")


@bp.route("/register/<token>", methods=["GET", "POST"])
@handle_service_errors
def register(token):
    if request.method == "POST":
        invitation_services.validate_invitation_token(token)
    else:
        invitation_services.get_invitation_by_token(token)
    invitation = invitation_services.get_invitation_by_token(token)
    form = RegisterForm()
    if invitation.email:
        form.email.data = invitation.email
    if form.validate_on_submit():
        if form.password.data != form.confirm_password.data:
            flash("Passwords do not match.", "danger")
            return render_template("workforce_identity/register.html", form=form, invitation=invitation)
        user = invitation_services.accept_invitation(
            token,
            full_name=form.full_name.data,
            email=form.email.data,
            password=form.password.data,
        )
        flash(f"Welcome, {user.full_name}. Your training account is active.", "success")
        return redirect(url_for("auth.login"))
    return render_template(
        "workforce_identity/register.html",
        form=form,
        invitation=invitation,
    )


@bp.route("/my-duties")
@login_required
@handle_service_errors
def my_duties():
    duties = duty_services.get_my_next_duties(current_user)
    return render_template("workforce_identity/my_duties.html", duties=duties)


@bp.route("/today-team")
@login_required
@handle_service_errors
def today_team():
    team = duty_services.get_today_on_call_team(current_user)
    return render_template("workforce_identity/today_team.html", **team)


@bp.route("/invitations")
@login_required
@handle_service_errors
def list_invitations():
    invitations = invitation_services.list_invitations(current_user)
    return render_template("workforce_identity/invitations.html", invitations=invitations)


@bp.route("/invitations/new", methods=["GET", "POST"])
@login_required
@handle_service_errors
def create_invitation():
    form = InvitationForm()
    if form.validate_on_submit():
        invitation = invitation_services.create_invitation(
            current_user,
            role_code=form.role_code.data,
            start_date=form.start_date.data,
            expiry_date=form.expiry_date.data,
            rotation_label=form.rotation_label.data or None,
            email=form.email.data or None,
            maximum_validity_days=form.maximum_validity_days.data or 14,
        )
        flash(f"Invitation created. Registration link: {invitation_services.registration_url(invitation, external=True)}", "success")
        return redirect(url_for("workforce_identity.list_invitations"))
    return render_template("workforce_identity/invitation_form.html", form=form)


@bp.route("/invitations/<int:invitation_id>/revoke", methods=["POST"])
@login_required
@handle_service_errors
def revoke_invitation(invitation_id):
    invitation_services.revoke_invitation(current_user, invitation_id)
    flash("Invitation revoked.", "success")
    return redirect(url_for("workforce_identity.list_invitations"))


@bp.route("/swaps")
@login_required
@handle_service_errors
def list_swaps():
    swaps = swap_services.list_user_swaps(current_user)
    pending = []
    from app.engines import permission_engine

    if permission_engine.check(current_user, "workforce_identity:duty_coordinate"):
        pending = swap_services.list_pending_swaps(current_user)
    return render_template("workforce_identity/swaps.html", swaps=swaps, pending=pending)


@bp.route("/swaps/new", methods=["GET", "POST"])
@login_required
@handle_service_errors
def request_swap():
    form = SwapRequestForm()
    if form.validate_on_submit():
        swap_services.create_swap_request(
            current_user,
            replacement_user_id=form.replacement_user_id.data,
            original_roster_entry_id=form.original_roster_entry_id.data,
            requested_roster_entry_id=form.requested_roster_entry_id.data or None,
            reason=form.reason.data,
        )
        flash("Swap request submitted for coordinator approval.", "success")
        return redirect(url_for("workforce_identity.list_swaps"))
    return render_template("workforce_identity/swap_form.html", form=form)


@bp.route("/swaps/<int:request_id>/approve", methods=["POST"])
@login_required
@handle_service_errors
def approve_swap(request_id):
    swap_services.approve_swap(current_user, request_id, notes=request.form.get("notes"))
    flash("Swap approved and roster updated.", "success")
    return redirect(url_for("workforce_identity.list_swaps"))


@bp.route("/swaps/<int:request_id>/reject", methods=["POST"])
@login_required
@handle_service_errors
def reject_swap(request_id):
    swap_services.reject_swap(current_user, request_id, notes=request.form.get("notes"))
    flash("Swap request rejected.", "info")
    return redirect(url_for("workforce_identity.list_swaps"))


@bp.route("/accounts/<int:user_id>/extend", methods=["POST"])
@login_required
@handle_service_errors
def extend_account(user_id):
    new_expiry = date.fromisoformat(request.form["new_expiry_date"])
    lifecycle_services.extend_account(current_user, user_id, new_expiry_date=new_expiry)
    flash("Account extended.", "success")
    return redirect(url_for("workforce_identity.hod_dashboard"))


@bp.route("/accounts/<int:user_id>/period", methods=["POST"])
@login_required
@handle_service_errors
def set_account_period(user_id):
    from app.modules.workforce_identity import account_admin_services

    start = date.fromisoformat(request.form["start_date"])
    expiry = date.fromisoformat(request.form["expiry_date"])
    rotation = request.form.get("rotation_label") or None
    account_admin_services.set_account_period(
        current_user,
        user_id,
        start_date=start,
        expiry_date=expiry,
        rotation_label=rotation,
    )
    flash("Account period saved.", "success")
    return redirect(url_for("workforce_identity.hod_dashboard"))


@bp.route("/accounts/<int:user_id>/supervisor", methods=["POST"])
@login_required
@handle_service_errors
def assign_supervisor(user_id):
    from app.modules.workforce_identity import account_admin_services

    raw = request.form.get("supervisor_user_id", "").strip()
    supervisor_id = int(raw) if raw else None
    account_admin_services.assign_clinical_supervisor(
        current_user,
        user_id,
        supervisor_user_id=supervisor_id,
    )
    flash("Clinical supervisor updated.", "success")
    return redirect(url_for("workforce_identity.hod_dashboard"))


@bp.route("/hod-dashboard")
@login_required
@handle_service_errors
def hod_dashboard():
    from app.modules.workforce_identity import account_admin_services

    data = dashboard_services.get_hod_workforce_dashboard(current_user)
    dept_id = getattr(current_user, "department_id", 1) or 1
    data["supervisors"] = account_admin_services.list_eligible_supervisors(department_id=dept_id)
    return render_template("workforce_identity/hod_dashboard.html", **data)
