from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.core.exceptions import ValidationError
from app.core.route_helpers import flash_form_errors, handle_service_errors
from app.engines import permission_engine
from app.modules.appointments import services
from app.modules.appointments.forms import (
    AppointmentForm,
    AppointmentSearchForm,
    ArchiveAppointmentForm,
    CancelAppointmentForm,
    RescheduleForm,
)
from app.modules.appointments.booking_capacity.forms import (
    BookingCapacitySettingsForm,
    BookingHolidayForm,
)
from app.modules.appointments.booking_capacity import services as capacity_services
from app.modules.appointments.booking_capacity.models import BookingHoliday
from app.modules.patients import services as patient_services

bp = Blueprint("appointments", __name__, url_prefix="/appointments")


@bp.route("/")
@login_required
@handle_service_errors
def list_appointments():
    search_form = AppointmentSearchForm(request.args)
    date_from = search_form.date_from.data
    date_to = search_form.date_to.data
    status = request.args.get("status") or None

    appointments = services.search_appointments(
        current_user, date_from=date_from, date_to=date_to, status=status
    )
    return render_template(
        "appointments/list.html", appointments=appointments, search_form=search_form
    )


@bp.route("/capacity-settings", methods=["GET", "POST"])
@login_required
@handle_service_errors
def capacity_settings():
    permission_engine.require(current_user, "appointment:capacity_manage")
    settings = capacity_services.get_capacity_settings()
    settings_form = BookingCapacitySettingsForm()
    holiday_form = BookingHolidayForm()
    holidays = (
        BookingHoliday.query.filter_by(is_archived=False)
        .order_by(BookingHoliday.holiday_date.asc())
        .all()
    )

    if request.method == "GET":
        settings_form.upper_gi_daily_cap.data = settings.upper_gi_daily_cap
        settings_form.colonoscopy_daily_cap.data = settings.colonoscopy_daily_cap
        settings_form.peg_daily_cap.data = settings.peg_daily_cap
        settings_form.scheduler_sub_quota_percent.data = settings.scheduler_sub_quota_percent
        settings_form.time_lock_hours.data = settings.time_lock_hours
        settings_form.sunday_blocked.data = settings.sunday_blocked
        settings_form.ercp_weekdays_only.data = settings.ercp_weekdays_only

    if settings_form.submit.data and settings_form.validate_on_submit():
        try:
            capacity_services.update_capacity_settings(
                current_user,
                upper_gi_daily_cap=settings_form.upper_gi_daily_cap.data,
                colonoscopy_daily_cap=settings_form.colonoscopy_daily_cap.data,
                peg_daily_cap=settings_form.peg_daily_cap.data,
                scheduler_sub_quota_percent=settings_form.scheduler_sub_quota_percent.data,
                time_lock_hours=settings_form.time_lock_hours.data,
                sunday_blocked=settings_form.sunday_blocked.data,
                ercp_weekdays_only=settings_form.ercp_weekdays_only.data,
            )
        except ValidationError as e:
            flash(str(e), "danger")
        else:
            flash("Booking capacity settings saved.", "success")
            return redirect(url_for("appointments.capacity_settings"))

    if holiday_form.submit.data and holiday_form.validate_on_submit():
        try:
            capacity_services.add_holiday(
                current_user,
                holiday_form.holiday_date.data,
                label=holiday_form.label.data,
            )
        except ValidationError as e:
            flash(str(e), "danger")
        else:
            flash("Holiday added.", "success")
            return redirect(url_for("appointments.capacity_settings"))

    return render_template(
        "appointments/capacity_settings.html",
        settings_form=settings_form,
        holiday_form=holiday_form,
        holidays=holidays,
    )


@bp.route("/capacity-settings/holidays/<int:holiday_id>/remove", methods=["POST"])
@login_required
@handle_service_errors
def remove_booking_holiday(holiday_id):
    try:
        capacity_services.remove_holiday(current_user, holiday_id)
    except ValidationError as e:
        flash(str(e), "danger")
    else:
        flash("Holiday removed.", "success")
    return redirect(url_for("appointments.capacity_settings"))


@bp.route("/new", methods=["GET", "POST"])
@login_required
@handle_service_errors
def new_appointment():
    patient_id = request.args.get("patient_id", type=int)
    if not patient_id:
        flash("Choose a patient first, then book an appointment from their record.", "danger")
        return redirect(url_for("patients.list_patients"))

    patient = patient_services.get_patient(current_user, patient_id)

    form = AppointmentForm()
    if form.validate_on_submit():
        try:
            appointment = services.create_appointment(
                acting_user=current_user,
                patient_id=patient.id,
                scheduled_at=form.scheduled_at.data,
                provider_id=int(form.provider_id.data) if form.provider_id.data else None,
                duration_minutes=form.duration_minutes.data,
                reason=form.reason.data,
                notes=form.notes.data,
            )
        except ValidationError as e:
            flash(str(e), "danger")
            return render_template("appointments/form.html", form=form, mode="create", patient=patient)

        flash("Appointment booked.", "success")
        return redirect(url_for("appointments.view_appointment", appointment_id=appointment.id))

    if request.method == "POST":
        flash_form_errors(form)

    return render_template("appointments/form.html", form=form, mode="create", patient=patient)


@bp.route("/<int:appointment_id>")
@login_required
@handle_service_errors
def view_appointment(appointment_id):
    appointment = services.get_appointment(current_user, appointment_id)
    from app.modules.procedures.models import Procedure

    linked_procedures = (
        Procedure.query.filter_by(appointment_id=appointment.id, is_archived=False)
        .order_by(Procedure.created_at.desc())
        .all()
    )
    return render_template(
        "appointments/detail.html",
        appointment=appointment,
        linked_procedures=linked_procedures,
    )


@bp.route("/<int:appointment_id>/reschedule", methods=["GET", "POST"])
@login_required
@handle_service_errors
def reschedule_appointment(appointment_id):
    target = services.get_appointment(current_user, appointment_id)
    form = RescheduleForm()
    if form.validate_on_submit():
        try:
            services.reschedule_appointment(
                current_user,
                target,
                form.new_scheduled_at.data,
                reason=form.reason.data,
                is_capacity_override=form.is_capacity_override.data,
            )
        except ValidationError as e:
            flash(str(e), "danger")
            return render_template("appointments/reschedule.html", form=form, target=target)

        flash("Appointment rescheduled.", "success")
        return redirect(url_for("appointments.view_appointment", appointment_id=target.id))

    if request.method == "POST":
        flash_form_errors(form)

    return render_template("appointments/reschedule.html", form=form, target=target)


@bp.route("/<int:appointment_id>/check-in", methods=["POST"])
@login_required
@handle_service_errors
def check_in_appointment(appointment_id):
    target = services.get_appointment(current_user, appointment_id)
    try:
        services.check_in_appointment(current_user, target)
        flash("Patient checked in.", "success")
    except ValidationError as e:
        flash(str(e), "danger")
    return redirect(url_for("appointments.view_appointment", appointment_id=target.id))


@bp.route("/<int:appointment_id>/start", methods=["POST"])
@login_required
@handle_service_errors
def start_appointment(appointment_id):
    target = services.get_appointment(current_user, appointment_id)
    try:
        services.start_appointment(current_user, target)
        flash("Appointment marked in progress.", "success")
    except ValidationError as e:
        flash(str(e), "danger")
    return redirect(url_for("appointments.view_appointment", appointment_id=target.id))


@bp.route("/<int:appointment_id>/complete", methods=["POST"])
@login_required
@handle_service_errors
def complete_appointment(appointment_id):
    target = services.get_appointment(current_user, appointment_id)
    try:
        services.complete_appointment(current_user, target)
        flash("Appointment marked completed.", "success")
    except ValidationError as e:
        flash(str(e), "danger")
    return redirect(url_for("appointments.view_appointment", appointment_id=target.id))


@bp.route("/<int:appointment_id>/no-show", methods=["POST"])
@login_required
@handle_service_errors
def no_show_appointment(appointment_id):
    target = services.get_appointment(current_user, appointment_id)
    try:
        services.mark_no_show(current_user, target)
        flash("Appointment marked as no-show.", "success")
    except ValidationError as e:
        flash(str(e), "danger")
    return redirect(url_for("appointments.view_appointment", appointment_id=target.id))


@bp.route("/<int:appointment_id>/cancel", methods=["GET", "POST"])
@login_required
@handle_service_errors
def cancel_appointment(appointment_id):
    target = services.get_appointment(current_user, appointment_id)
    form = CancelAppointmentForm()
    if form.validate_on_submit():
        try:
            services.cancel_appointment(current_user, target, reason=form.reason.data)
        except ValidationError as e:
            flash(str(e), "danger")
            return render_template("appointments/cancel.html", form=form, target=target)

        flash("Appointment cancelled.", "success")
        return redirect(url_for("appointments.view_appointment", appointment_id=target.id))

    return render_template("appointments/cancel.html", form=form, target=target)


@bp.route("/<int:appointment_id>/archive", methods=["GET", "POST"])
@login_required
@handle_service_errors
def archive_appointment(appointment_id):
    target = services.get_appointment(current_user, appointment_id)
    form = ArchiveAppointmentForm()
    if form.validate_on_submit():
        services.archive_appointment(current_user, target, reason=form.reason.data)
        flash("Appointment archived.", "success")
        return redirect(url_for("appointments.view_appointment", appointment_id=target.id))

    return render_template("appointments/archive.html", form=form, target=target)


@bp.route("/<int:appointment_id>/restore", methods=["POST"])
@login_required
@handle_service_errors
def restore_appointment(appointment_id):
    target = services.get_appointment(current_user, appointment_id)
    services.restore_appointment(current_user, target)
    flash("Appointment restored.", "success")
    return redirect(url_for("appointments.view_appointment", appointment_id=target.id))
