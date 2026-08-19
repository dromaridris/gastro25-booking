from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.core.route_helpers import handle_service_errors
from app.modules.notifications import services

bp = Blueprint("notifications", __name__, url_prefix="/notifications")


@bp.route("/")
@login_required
@handle_service_errors
def inbox():
    unread_only = request.args.get("unread") == "1"
    notes = services.list_for_user(current_user, unread_only=unread_only)
    return render_template("notifications/inbox.html", notifications=notes, unread_only=unread_only)


@bp.route("/<int:notification_id>/read", methods=["POST"])
@login_required
@handle_service_errors
def mark_read(notification_id):
    note = services.mark_read(current_user, notification_id)
    if note.link_url:
        return redirect(note.link_url)
    return redirect(url_for("notifications.inbox"))


@bp.route("/read-all", methods=["POST"])
@login_required
@handle_service_errors
def mark_all_read():
    count = services.mark_all_read(current_user)
    flash(f"{count} notification(s) marked read.", "success")
    return redirect(url_for("notifications.inbox"))
