from datetime import date

from flask import Blueprint, render_template, request
from flask_login import current_user, login_required

from app.core.route_helpers import handle_service_errors
from app.modules.calendar_hub import services

bp = Blueprint("calendar_hub", __name__, url_prefix="/calendar")


@bp.route("/")
@login_required
@handle_service_errors
def week_view():
    week_date = request.args.get("date")
    on_date = date.fromisoformat(week_date) if week_date else None
    calendar = services.aggregate_week(current_user, on_date=on_date)
    return render_template("calendar_hub/week.html", calendar=calendar)
