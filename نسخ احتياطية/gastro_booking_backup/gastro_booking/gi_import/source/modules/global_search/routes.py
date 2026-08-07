from flask import Blueprint, jsonify, render_template, request
from flask_login import current_user, login_required

from app.core.route_helpers import handle_service_errors
from app.modules.global_search import services

bp = Blueprint("global_search", __name__)


@bp.route("/search/")
@login_required
@handle_service_errors
def search_page():
    q = request.args.get("q", "").strip()
    results = services.search(current_user, q) if q else {"patients": [], "appointments": [], "procedures": []}
    if request.accept_mimetypes.best == "application/json":
        return jsonify(results)
    return render_template("ui/search_results.html", q=q, results=results)
