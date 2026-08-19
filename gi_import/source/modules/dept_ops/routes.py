"""Department Operations routes — Sprint 7C."""

from datetime import date, datetime, time

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.core.route_helpers import handle_service_errors
from app.engines import permission_engine
from app.modules.auth.models import User
from app.modules.dept_ops import (
    alert_services,
    announcement_services,
    calendar_services,
    consumable_services,
    dashboard_services,
    messaging_services,
    reprocessing_services,
    room_services,
    roster_services,
    scope_services,
    waiting_list_services,
)
from app.modules.dept_ops.constants import ALL_CONSUMABLE_CATEGORIES, STOCK_RECEIPT, STOCK_USAGE
from app.modules.procedures.models import Procedure

bp = Blueprint("dept_ops", __name__, url_prefix="/dept-ops")


@bp.route("/")
@login_required
@handle_service_errors
def home():
    page = dashboard_services.get_role_homepage(current_user)
    return render_template(page["template"], **page["data"])


@bp.route("/alerts")
@login_required
@handle_service_errors
def alerts():
    items = alert_services.collect_alerts(current_user)
    return render_template("dept_ops/alerts.html", alerts=items)


# --- Rooms ---
@bp.route("/rooms")
@login_required
@handle_service_errors
def rooms():
    board = room_services.list_room_states(current_user)
    calendar = calendar_services.room_schedule_calendar(current_user)
    return render_template("dept_ops/rooms.html", board=board, calendar=calendar)


@bp.route("/rooms/schedule", methods=["POST"])
@login_required
@handle_service_errors
def book_room_slot():
    room_services.book_room_slot(
        current_user,
        request.form.get("room_id", type=int),
        datetime.fromisoformat(request.form.get("start_at")),
        datetime.fromisoformat(request.form.get("end_at")),
        procedure_id=request.form.get("procedure_id", type=int),
        title=request.form.get("title"),
    )
    flash("Room slot booked.", "success")
    return redirect(url_for("dept_ops.rooms"))


@bp.route("/rooms/<int:room_id>/status", methods=["POST"])
@login_required
@handle_service_errors
def update_room_status(room_id):
    room_services.update_room_status(current_user, room_id, request.form.get("status"), notes=request.form.get("notes"))
    flash("Room status updated.", "success")
    return redirect(url_for("dept_ops.rooms"))


# --- Scopes ---
@bp.route("/scopes")
@login_required
@handle_service_errors
def scopes():
    items = scope_services.list_scopes(current_user)
    queue = reprocessing_services.cleaning_queue(current_user)
    return render_template("dept_ops/scopes.html", scopes=items, cleaning_queue=queue)


@bp.route("/scopes/new", methods=["GET", "POST"])
@login_required
@handle_service_errors
def create_scope():
    if request.method == "POST":
        scope_services.create_scope(
            current_user,
            scope_code=request.form.get("scope_code"),
            scope_type=request.form.get("scope_type"),
            serial_number=request.form.get("serial_number") or None,
            model=request.form.get("model") or None,
            manufacturer=request.form.get("manufacturer") or None,
        )
        flash("Endoscope registered.", "success")
        return redirect(url_for("dept_ops.scopes"))
    return render_template("dept_ops/scope_form.html")


@bp.route("/scopes/<int:scope_id>")
@login_required
@handle_service_errors
def scope_detail(scope_id):
    detail = scope_services.get_scope_detail(current_user, scope_id)
    detail["active_cycle"] = reprocessing_services.get_active_cycle(scope_id)
    return render_template("dept_ops/scope_detail.html", **detail)


@bp.route("/scopes/<int:scope_id>/maintenance", methods=["POST"])
@login_required
@handle_service_errors
def record_scope_maintenance(scope_id):
    scope = scope_services.get_scope(current_user, scope_id)
    next_due = request.form.get("next_due_at")
    scope_services.record_maintenance(
        current_user,
        scope,
        request.form.get("record_type", "service"),
        notes=request.form.get("notes"),
        next_due_at=datetime.fromisoformat(next_due) if next_due else None,
    )
    flash("Maintenance recorded.", "success")
    return redirect(url_for("dept_ops.scope_detail", scope_id=scope_id))


@bp.route("/scopes/<int:scope_id>/reprocess/start", methods=["POST"])
@login_required
@handle_service_errors
def start_reprocessing(scope_id):
    scope = scope_services.get_scope(current_user, scope_id)
    reprocessing_services.start_reprocessing(current_user, scope)
    flash("Reprocessing started.", "success")
    return redirect(url_for("dept_ops.scope_detail", scope_id=scope_id))


@bp.route("/scopes/<int:scope_id>/reprocess/advance", methods=["POST"])
@login_required
@handle_service_errors
def advance_reprocessing(scope_id):
    cycle = reprocessing_services.get_active_cycle(scope_id)
    if cycle:
        if cycle.current_step == "storage":
            reprocessing_services.complete_reprocessing(current_user, cycle)
            flash("Reprocessing complete — scope available.", "success")
        else:
            reprocessing_services.advance_reprocessing_step(current_user, cycle)
            flash("Reprocessing step advanced.", "success")
    return redirect(request.referrer or url_for("dept_ops.scope_detail", scope_id=scope_id))


@bp.route("/reprocessing")
@login_required
@handle_service_errors
def reprocessing_board():
    queue = reprocessing_services.cleaning_queue(current_user)
    return render_template("dept_ops/reprocessing.html", cleaning_queue=queue)


# --- Consumables ---
@bp.route("/consumables")
@login_required
@handle_service_errors
def consumables():
    items = consumable_services.list_consumables(current_user)
    low = consumable_services.low_stock_items(current_user)
    procedures = Procedure.query.filter_by(is_archived=False).order_by(Procedure.id.desc()).limit(50).all()
    return render_template(
        "dept_ops/consumables.html",
        items=items,
        low_stock=low,
        categories=ALL_CONSUMABLE_CATEGORIES,
        procedures=procedures,
    )


@bp.route("/consumables/new", methods=["POST"])
@login_required
@handle_service_errors
def create_consumable():
    consumable_services.create_consumable(
        current_user,
        name=request.form.get("name"),
        category=request.form.get("category"),
        current_stock=request.form.get("current_stock", type=int) or 0,
        minimum_stock=request.form.get("minimum_stock", type=int) or 0,
        unit=request.form.get("unit") or "each",
    )
    flash("Consumable created.", "success")
    return redirect(url_for("dept_ops.consumables"))


@bp.route("/consumables/<int:item_id>/movement", methods=["POST"])
@login_required
@handle_service_errors
def consumable_movement(item_id):
    from app.modules.dept_ops.models import ConsumableItem

    item = ConsumableItem.query.get(item_id)
    consumable_services.record_stock_movement(
        current_user,
        item,
        request.form.get("movement_type"),
        request.form.get("quantity", type=int),
        procedure_id=request.form.get("procedure_id", type=int),
        notes=request.form.get("notes"),
    )
    flash("Stock updated.", "success")
    return redirect(url_for("dept_ops.consumables"))


@bp.route("/consumables/plan", methods=["POST"])
@login_required
@handle_service_errors
def plan_consumable():
    consumable_services.plan_procedure_consumable(
        current_user,
        request.form.get("procedure_id", type=int),
        request.form.get("consumable_id", type=int),
        request.form.get("quantity", type=int) or 1,
    )
    flash("Consumable planned for procedure — will auto-deduct on completion.", "success")
    return redirect(url_for("dept_ops.consumables"))


# --- Waiting list ---
@bp.route("/waiting-list")
@login_required
@handle_service_errors
def waiting_list():
    permission_engine.require(current_user, "dept_ops:waiting_list")
    summary = waiting_list_services.waiting_list_summary(current_user)
    calendar = calendar_services.waiting_list_schedule(current_user)
    from app.modules.patients.models import Patient
    from app.modules.procedures.models import ProcedureType

    return render_template(
        "dept_ops/waiting_list.html",
        **summary,
        calendar=calendar,
        patients=Patient.query.filter_by(is_archived=False).limit(100).all(),
        procedure_types=ProcedureType.query.filter_by(is_archived=False).all(),
    )


@bp.route("/waiting-list/add", methods=["POST"])
@login_required
@handle_service_errors
def add_waiting_list():
    sched = request.form.get("scheduled_date")
    waiting_list_services.add_to_waiting_list(
        current_user,
        patient_id=request.form.get("patient_id", type=int),
        procedure_type_id=request.form.get("procedure_type_id", type=int),
        priority=request.form.get("priority", "routine"),
        consultant_id=request.form.get("consultant_id", type=int),
        scheduled_date=date.fromisoformat(sched) if sched else None,
    )
    flash("Patient added to waiting list.", "success")
    return redirect(url_for("dept_ops.waiting_list"))


@bp.route("/waiting-list/<int:entry_id>/schedule", methods=["POST"])
@login_required
@handle_service_errors
def schedule_waiting_list(entry_id):
    from app.modules.dept_ops.models import WaitingListEntry

    entry = WaitingListEntry.query.get(entry_id)
    waiting_list_services.schedule_waiting_list_entry(
        current_user,
        entry,
        date.fromisoformat(request.form.get("scheduled_date")),
        procedure_id=request.form.get("procedure_id", type=int),
    )
    flash("Waiting list entry scheduled.", "success")
    return redirect(url_for("dept_ops.waiting_list"))


# --- Roster ---
@bp.route("/roster")
@login_required
@handle_service_errors
def roster():
    permission_engine.require(current_user, "dept_ops:roster_manage")
    roster_date = request.args.get("date")
    target = date.fromisoformat(roster_date) if roster_date else date.today()
    entries = roster_services.list_roster(current_user, roster_date=target)
    calendar = calendar_services.weekly_roster_calendar(current_user, target)
    users = User.query.filter_by(is_archived=False).order_by(User.email.asc()).all()
    return render_template("dept_ops/roster.html", entries=entries, roster_date=target, calendar=calendar, users=users)


@bp.route("/roster/add", methods=["POST"])
@login_required
@handle_service_errors
def add_roster_entry():
    roster_services.create_roster_entry(
        current_user,
        user_id=request.form.get("user_id", type=int),
        roster_date=date.fromisoformat(request.form.get("roster_date")),
        shift_type=request.form.get("shift_type"),
        is_on_call=bool(request.form.get("is_on_call")),
        is_leave=bool(request.form.get("is_leave")),
        notes=request.form.get("notes"),
    )
    flash("Roster entry added.", "success")
    return redirect(url_for("dept_ops.roster", date=request.form.get("roster_date")))


# --- Announcements & messages ---
@bp.route("/announcements")
@login_required
@handle_service_errors
def announcements():
    items = announcement_services.list_announcements(current_user)
    return render_template("dept_ops/announcements.html", announcements=items)


@bp.route("/announcements/new", methods=["POST"])
@login_required
@handle_service_errors
def publish_announcement():
    expires = request.form.get("expires_at")
    announcement_services.publish_announcement(
        current_user,
        title=request.form.get("title"),
        body=request.form.get("body"),
        category=request.form.get("category", "notice"),
        priority=request.form.get("priority", "normal"),
        expires_at=datetime.fromisoformat(expires) if expires else None,
    )
    flash("Announcement published.", "success")
    return redirect(url_for("dept_ops.announcements"))


@bp.route("/messages")
@login_required
@handle_service_errors
def messages():
    items = messaging_services.inbox(current_user)
    users = User.query.filter_by(is_archived=False).order_by(User.email.asc()).all()
    return render_template("dept_ops/messages.html", messages=items, users=users)


@bp.route("/messages/send", methods=["POST"])
@login_required
@handle_service_errors
def send_message():
    messaging_services.send_message(
        current_user,
        subject=request.form.get("subject"),
        body=request.form.get("body"),
        message_scope=request.form.get("message_scope", "direct"),
        recipient_id=request.form.get("recipient_id", type=int),
    )
    flash("Message sent.", "success")
    return redirect(url_for("dept_ops.messages"))
