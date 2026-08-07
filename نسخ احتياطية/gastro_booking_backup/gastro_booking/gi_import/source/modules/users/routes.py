from flask import Blueprint, current_app, flash, redirect, render_template, url_for
from flask_login import current_user, login_required

from app.core.exceptions import ValidationError
from app.core.route_helpers import handle_service_errors
from app.modules.department.services import list_active_departments
from app.modules.users import services
from app.modules.users.forms import (
    AppointmentLimitForm,
    ChangeRoleForm,
    DeactivateForm,
    ProviderFlagForm,
    UserCreateForm,
    UserEditForm,
)

bp = Blueprint("users", __name__, url_prefix="/users")


@bp.route("/")
@login_required
@handle_service_errors
def list_users():
    users = services.list_users(current_user)
    return render_template("users/list.html", users=users)


@bp.route("/new", methods=["GET", "POST"])
@login_required
@handle_service_errors
def create_user():
    form = UserCreateForm()
    form_departments = list_active_departments()
    if form.validate_on_submit():
        try:
            services.create_user(
                acting_user=current_user,
                full_name=form.full_name.data,
                email=form.email.data,
                password=form.password.data,
                role=form.role.data,
                department_id=form_departments[0].id
                if form_departments
                else current_app.config["DEFAULT_DEPARTMENT_ID"],
            )
        except ValidationError as e:
            flash(str(e), "danger")
            return render_template("users/form.html", form=form, mode="create")

        flash("User created.", "success")
        return redirect(url_for("users.list_users"))

    return render_template("users/form.html", form=form, mode="create")


@bp.route("/<int:user_id>")
@login_required
@handle_service_errors
def view_user(user_id):
    user = services.get_user(current_user, user_id)
    return render_template("users/detail.html", user=user)


@bp.route("/<int:user_id>/edit", methods=["GET", "POST"])
@login_required
@handle_service_errors
def edit_user(user_id):
    target = services.get_user(current_user, user_id)
    form = UserEditForm(obj=target)
    if form.validate_on_submit():
        try:
            services.update_user(current_user, target, form.full_name.data, form.email.data)
        except ValidationError as e:
            flash(str(e), "danger")
            return render_template("users/form.html", form=form, mode="edit", target=target)

        flash("User updated.", "success")
        return redirect(url_for("users.view_user", user_id=target.id))

    return render_template("users/form.html", form=form, mode="edit", target=target)


@bp.route("/<int:user_id>/role", methods=["GET", "POST"])
@login_required
@handle_service_errors
def change_role(user_id):
    from app.modules.rbac import services as rbac_services

    rbac_services.ensure_role_catalog()
    target = services.get_user(current_user, user_id)
    form = ChangeRoleForm(role=target.role.code if target.role else None)
    if form.validate_on_submit():
        try:
            services.change_role(current_user, target, form.role.data)
        except ValidationError as e:
            flash(str(e), "danger")
            return render_template("users/change_role.html", form=form, target=target)

        flash("Role updated.", "success")
        return redirect(url_for("users.view_user", user_id=target.id))

    return render_template("users/change_role.html", form=form, target=target)


@bp.route("/<int:user_id>/deactivate", methods=["GET", "POST"])
@login_required
@handle_service_errors
def deactivate_user(user_id):
    target = services.get_user(current_user, user_id)
    form = DeactivateForm()
    if form.validate_on_submit():
        services.deactivate_user(current_user, target, reason=form.reason.data)
        flash("User deactivated.", "success")
        return redirect(url_for("users.view_user", user_id=target.id))

    return render_template("users/deactivate.html", form=form, target=target)


@bp.route("/<int:user_id>/appointment-limit", methods=["GET", "POST"])
@login_required
@handle_service_errors
def set_appointment_limit(user_id):
    target = services.get_user(current_user, user_id)
    form = AppointmentLimitForm(daily_appointment_limit=target.daily_appointment_limit)
    if form.validate_on_submit():
        try:
            services.set_daily_appointment_limit(
                current_user, target, form.daily_appointment_limit.data
            )
        except ValidationError as e:
            flash(str(e), "danger")
            return render_template("users/appointment_limit.html", form=form, target=target)

        flash("Daily appointment limit updated.", "success")
        return redirect(url_for("users.view_user", user_id=target.id))

    return render_template("users/appointment_limit.html", form=form, target=target)


@bp.route("/<int:user_id>/provider-flag", methods=["GET", "POST"])
@login_required
@handle_service_errors
def set_provider_flag(user_id):
    target = services.get_user(current_user, user_id)
    form = ProviderFlagForm(is_provider=target.is_provider)
    if form.validate_on_submit():
        services.set_provider_flag(current_user, target, form.is_provider.data)
        flash("Provider eligibility updated.", "success")
        return redirect(url_for("users.view_user", user_id=target.id))

    return render_template("users/provider_flag.html", form=form, target=target)


@bp.route("/<int:user_id>/reactivate", methods=["POST"])
@login_required
@handle_service_errors
def reactivate_user(user_id):
    target = services.get_user(current_user, user_id)
    services.reactivate_user(current_user, target)
    flash("User reactivated.", "success")
    return redirect(url_for("users.view_user", user_id=target.id))
