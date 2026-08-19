from datetime import date

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.core.exceptions import ValidationError
from app.core.route_helpers import flash_form_errors, handle_service_errors
from app.modules.appointments import services as appointment_services
from app.modules.procedures import services
from app.modules.procedures.forms import (
    ArchiveProcedureForm,
    ArchiveProcedureTypeForm,
    ArchiveRoomForm,
    AssignEndoscopistForm,
    AssignRoomForm,
    CancelProcedureForm,
    ChangeProcedureTypeForm,
    DailyListFilterForm,
    PriorityForm,
    ProcedureForm,
    ProcedureTypeForm,
    RoomForm,
    WaitlistForm,
)

bp = Blueprint("procedures", __name__, url_prefix="/procedures")


# --- Procedure Catalogue (administrator-managed) ---


@bp.route("/types")
@login_required
@handle_service_errors
def list_procedure_types():
    procedure_types = services.list_procedure_types(current_user)
    return render_template("procedures/type_list.html", procedure_types=procedure_types)


@bp.route("/types/new", methods=["GET", "POST"])
@login_required
@handle_service_errors
def create_procedure_type():
    form = ProcedureTypeForm()
    if form.validate_on_submit():
        try:
            services.create_procedure_type(
                current_user,
                name=form.name.data,
                requires_special_authorization=form.requires_special_authorization.data,
                report_template_key=form.report_template_key.data,
                description=form.description.data,
            )
        except ValidationError as e:
            flash(str(e), "danger")
            return render_template("procedures/type_form.html", form=form, mode="create")

        flash("Procedure type created.", "success")
        return redirect(url_for("procedures.list_procedure_types"))

    return render_template("procedures/type_form.html", form=form, mode="create")


@bp.route("/types/<int:procedure_type_id>/edit", methods=["GET", "POST"])
@login_required
@handle_service_errors
def edit_procedure_type(procedure_type_id):
    target = services.get_procedure_type(current_user, procedure_type_id)
    form = ProcedureTypeForm(
        obj=target,
        report_template_key=target.report_template_key or "",
    )
    if form.validate_on_submit():
        try:
            services.update_procedure_type(
                current_user,
                target,
                name=form.name.data,
                requires_special_authorization=form.requires_special_authorization.data,
                report_template_key=form.report_template_key.data,
                description=form.description.data,
            )
        except ValidationError as e:
            flash(str(e), "danger")
            return render_template("procedures/type_form.html", form=form, mode="edit", target=target)

        flash("Procedure type updated.", "success")
        return redirect(url_for("procedures.list_procedure_types"))

    return render_template("procedures/type_form.html", form=form, mode="edit", target=target)


@bp.route("/types/<int:procedure_type_id>/archive", methods=["GET", "POST"])
@login_required
@handle_service_errors
def archive_procedure_type(procedure_type_id):
    target = services.get_procedure_type(current_user, procedure_type_id)
    form = ArchiveProcedureTypeForm()
    if form.validate_on_submit():
        services.archive_procedure_type(current_user, target, reason=form.reason.data)
        flash("Procedure type archived.", "success")
        return redirect(url_for("procedures.list_procedure_types"))

    return render_template("procedures/type_archive.html", form=form, target=target)


@bp.route("/types/<int:procedure_type_id>/restore", methods=["POST"])
@login_required
@handle_service_errors
def restore_procedure_type(procedure_type_id):
    target = services.get_procedure_type(current_user, procedure_type_id)
    services.restore_procedure_type(current_user, target)
    flash("Procedure type restored.", "success")
    return redirect(url_for("procedures.list_procedure_types"))


# --- Endoscopy Rooms (administrator-managed) ---


@bp.route("/rooms")
@login_required
@handle_service_errors
def list_rooms():
    rooms = services.list_rooms(current_user)
    return render_template("procedures/room_list.html", rooms=rooms)


@bp.route("/rooms/new", methods=["GET", "POST"])
@login_required
@handle_service_errors
def create_room():
    form = RoomForm()
    if form.validate_on_submit():
        try:
            services.create_room(current_user, name=form.name.data, description=form.description.data)
        except ValidationError as e:
            flash(str(e), "danger")
            return render_template("procedures/room_form.html", form=form, mode="create")

        flash("Room created.", "success")
        return redirect(url_for("procedures.list_rooms"))

    return render_template("procedures/room_form.html", form=form, mode="create")


@bp.route("/rooms/<int:room_id>/edit", methods=["GET", "POST"])
@login_required
@handle_service_errors
def edit_room(room_id):
    target = services.get_room(current_user, room_id)
    form = RoomForm(obj=target)
    if form.validate_on_submit():
        try:
            services.update_room(current_user, target, name=form.name.data, description=form.description.data)
        except ValidationError as e:
            flash(str(e), "danger")
            return render_template("procedures/room_form.html", form=form, mode="edit", target=target)

        flash("Room updated.", "success")
        return redirect(url_for("procedures.list_rooms"))

    return render_template("procedures/room_form.html", form=form, mode="edit", target=target)


@bp.route("/rooms/<int:room_id>/archive", methods=["GET", "POST"])
@login_required
@handle_service_errors
def archive_room(room_id):
    target = services.get_room(current_user, room_id)
    form = ArchiveRoomForm()
    if form.validate_on_submit():
        services.archive_room(current_user, target, reason=form.reason.data)
        flash("Room archived.", "success")
        return redirect(url_for("procedures.list_rooms"))

    return render_template("procedures/room_archive.html", form=form, target=target)


@bp.route("/rooms/<int:room_id>/restore", methods=["POST"])
@login_required
@handle_service_errors
def restore_room(room_id):
    target = services.get_room(current_user, room_id)
    services.restore_room(current_user, target)
    flash("Room restored.", "success")
    return redirect(url_for("procedures.list_rooms"))


# --- Procedure booking & workflow ---


@bp.route("/")
@login_required
@handle_service_errors
def list_procedures():
    procedures = services.search_procedures(current_user)
    return render_template("procedures/list.html", procedures=procedures)


@bp.route("/daily-list")
@login_required
@handle_service_errors
def daily_endoscopy_list():
    filter_form = DailyListFilterForm(request.args)
    on_date = filter_form.date.data or date.today()

    def _int_or_none(value):
        return int(value) if value else None

    procedures = services.daily_list(
        current_user,
        on_date,
        room_id=_int_or_none(request.args.get("room_id")),
        procedure_type_id=_int_or_none(request.args.get("procedure_type_id")),
        endoscopist_id=_int_or_none(request.args.get("endoscopist_id")),
        status=request.args.get("status") or None,
        priority=request.args.get("priority") or None,
    )
    return render_template(
        "procedures/daily_list.html", procedures=procedures, filter_form=filter_form, on_date=on_date
    )


@bp.route("/waiting-list")
@login_required
@handle_service_errors
def waiting_list_view():
    procedures = services.waiting_list(current_user)
    return render_template("procedures/waiting_list.html", procedures=procedures)


@bp.route("/new", methods=["GET", "POST"])
@login_required
@handle_service_errors
def new_procedure():
    appointment_id = request.args.get("appointment_id", type=int)
    if not appointment_id:
        flash("Choose an appointment first, then book a procedure from it.", "danger")
        return redirect(url_for("appointments.list_appointments"))

    appointment = appointment_services.get_appointment(current_user, appointment_id)

    form = ProcedureForm(acting_user=current_user)
    from app.modules.procedures.models import ProcedureType
    from app.modules.auth.models import User

    catalogue_ready = ProcedureType.query.filter_by(is_archived=False).count() > 0
    endoscopists_available = User.query.filter_by(
        is_archived=False, is_active_account=True, is_provider=True
    ).count() > 0
    if form.validate_on_submit():
        if not catalogue_ready:
            flash(
                "No procedure types are configured yet. Add at least one procedure type before booking.",
                "danger",
            )
        else:
            try:
                procedure = services.create_procedure(
                    acting_user=current_user,
                    appointment_id=appointment.id,
                    procedure_type_id=int(form.procedure_type_id.data),
                    room_id=int(form.room_id.data) if form.room_id.data else None,
                    endoscopist_id=int(form.endoscopist_id.data) if form.endoscopist_id.data else None,
                    priority=form.priority.data,
                    notes=form.notes.data,
                    is_capacity_override=form.is_capacity_override.data,
                )
            except ValidationError as e:
                flash(str(e), "danger")
                return render_template(
                    "procedures/form.html",
                    form=form,
                    mode="create",
                    appointment=appointment,
                    catalogue_ready=catalogue_ready,
                    endoscopists_available=endoscopists_available,
                )

            flash("Procedure booked.", "success")
            return redirect(url_for("procedures.view_procedure", procedure_id=procedure.id))

    if request.method == "POST":
        flash_form_errors(form)

    return render_template(
        "procedures/form.html",
        form=form,
        mode="create",
        appointment=appointment,
        catalogue_ready=catalogue_ready,
        endoscopists_available=endoscopists_available,
    )


@bp.route("/<int:procedure_id>")
@login_required
@handle_service_errors
def view_procedure(procedure_id):
    procedure = services.get_procedure(current_user, procedure_id)
    return render_template("procedures/detail.html", procedure=procedure)


@bp.route("/<int:procedure_id>/assign-endoscopist", methods=["GET", "POST"])
@login_required
@handle_service_errors
def assign_endoscopist(procedure_id):
    target = services.get_procedure(current_user, procedure_id)
    form = AssignEndoscopistForm(endoscopist_id=str(target.endoscopist_id) if target.endoscopist_id else "")
    if form.validate_on_submit():
        try:
            services.assign_endoscopist(
                current_user, target, int(form.endoscopist_id.data) if form.endoscopist_id.data else None
            )
        except ValidationError as e:
            flash(str(e), "danger")
            return render_template("procedures/assign_endoscopist.html", form=form, target=target)

        flash("Endoscopist assignment updated.", "success")
        return redirect(url_for("procedures.view_procedure", procedure_id=target.id))

    return render_template("procedures/assign_endoscopist.html", form=form, target=target)


@bp.route("/<int:procedure_id>/assign-room", methods=["GET", "POST"])
@login_required
@handle_service_errors
def assign_room(procedure_id):
    target = services.get_procedure(current_user, procedure_id)
    form = AssignRoomForm(room_id=str(target.room_id) if target.room_id else "")
    if form.validate_on_submit():
        try:
            services.assign_room(current_user, target, int(form.room_id.data) if form.room_id.data else None)
        except ValidationError as e:
            flash(str(e), "danger")
            return render_template("procedures/assign_room.html", form=form, target=target)

        flash("Room assignment updated.", "success")
        return redirect(url_for("procedures.view_procedure", procedure_id=target.id))

    return render_template("procedures/assign_room.html", form=form, target=target)


@bp.route("/<int:procedure_id>/change-type", methods=["GET", "POST"])
@login_required
@handle_service_errors
def change_procedure_type(procedure_id):
    target = services.get_procedure(current_user, procedure_id)
    form = ChangeProcedureTypeForm(procedure_type_id=str(target.procedure_type_id), acting_user=current_user)
    if form.validate_on_submit():
        try:
            services.change_procedure_type(current_user, target, int(form.procedure_type_id.data))
        except ValidationError as e:
            flash(str(e), "danger")
            return render_template("procedures/change_type.html", form=form, target=target)

        flash("Procedure type updated.", "success")
        return redirect(url_for("procedures.view_procedure", procedure_id=target.id))

    return render_template("procedures/change_type.html", form=form, target=target)


@bp.route("/<int:procedure_id>/priority", methods=["GET", "POST"])
@login_required
@handle_service_errors
def set_priority(procedure_id):
    target = services.get_procedure(current_user, procedure_id)
    form = PriorityForm(priority=target.priority)
    if form.validate_on_submit():
        try:
            services.set_priority(current_user, target, form.priority.data)
        except ValidationError as e:
            flash(str(e), "danger")
            return render_template("procedures/priority.html", form=form, target=target)

        flash("Priority updated.", "success")
        return redirect(url_for("procedures.view_procedure", procedure_id=target.id))

    return render_template("procedures/priority.html", form=form, target=target)


@bp.route("/<int:procedure_id>/waitlist", methods=["GET", "POST"])
@login_required
@handle_service_errors
def move_to_waiting_list(procedure_id):
    target = services.get_procedure(current_user, procedure_id)
    form = WaitlistForm()
    if form.validate_on_submit():
        try:
            services.move_to_waiting_list(current_user, target, reason=form.reason.data)
        except ValidationError as e:
            flash(str(e), "danger")
            return render_template("procedures/waitlist.html", form=form, target=target)

        flash("Procedure moved to the waiting list.", "success")
        return redirect(url_for("procedures.view_procedure", procedure_id=target.id))

    return render_template("procedures/waitlist.html", form=form, target=target)


@bp.route("/<int:procedure_id>/ready", methods=["POST"])
@login_required
@handle_service_errors
def mark_ready(procedure_id):
    target = services.get_procedure(current_user, procedure_id)
    try:
        services.mark_ready(current_user, target)
        flash("Procedure marked ready.", "success")
    except ValidationError as e:
        flash(str(e), "danger")
    return redirect(url_for("procedures.view_procedure", procedure_id=target.id))


@bp.route("/<int:procedure_id>/in-room", methods=["POST"])
@login_required
@handle_service_errors
def mark_in_room(procedure_id):
    target = services.get_procedure(current_user, procedure_id)
    try:
        services.mark_in_room(current_user, target)
        flash("Procedure marked in room.", "success")
    except ValidationError as e:
        flash(str(e), "danger")
    return redirect(url_for("procedures.view_procedure", procedure_id=target.id))


@bp.route("/<int:procedure_id>/finished", methods=["POST"])
@login_required
@handle_service_errors
def mark_finished(procedure_id):
    target = services.get_procedure(current_user, procedure_id)
    try:
        services.mark_finished(current_user, target)
        flash("Procedure marked finished.", "success")
    except ValidationError as e:
        flash(str(e), "danger")
    return redirect(url_for("procedures.view_procedure", procedure_id=target.id))


@bp.route("/<int:procedure_id>/cancel", methods=["GET", "POST"])
@login_required
@handle_service_errors
def cancel_procedure(procedure_id):
    target = services.get_procedure(current_user, procedure_id)
    form = CancelProcedureForm()
    if form.validate_on_submit():
        try:
            services.cancel_procedure(current_user, target, reason=form.reason.data)
        except ValidationError as e:
            flash(str(e), "danger")
            return render_template("procedures/cancel.html", form=form, target=target)

        flash("Procedure cancelled.", "success")
        return redirect(url_for("procedures.view_procedure", procedure_id=target.id))

    return render_template("procedures/cancel.html", form=form, target=target)


@bp.route("/<int:procedure_id>/archive", methods=["GET", "POST"])
@login_required
@handle_service_errors
def archive_procedure(procedure_id):
    target = services.get_procedure(current_user, procedure_id)
    form = ArchiveProcedureForm()
    if form.validate_on_submit():
        try:
            services.archive_procedure(current_user, target, reason=form.reason.data)
        except ValidationError as e:
            flash(str(e), "danger")
            return render_template("procedures/archive.html", form=form, target=target)

        flash("Procedure archived.", "success")
        return redirect(url_for("procedures.view_procedure", procedure_id=target.id))

    return render_template("procedures/archive.html", form=form, target=target)


@bp.route("/<int:procedure_id>/restore", methods=["POST"])
@login_required
@handle_service_errors
def restore_procedure(procedure_id):
    target = services.get_procedure(current_user, procedure_id)
    try:
        services.restore_procedure(current_user, target)
        flash("Procedure restored.", "success")
    except ValidationError as e:
        flash(str(e), "danger")
    return redirect(url_for("procedures.view_procedure", procedure_id=target.id))
