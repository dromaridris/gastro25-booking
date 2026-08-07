from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.core.route_helpers import handle_service_errors
from app.modules.archive_storage import services

bp = Blueprint("archive_storage", __name__, url_prefix="/archive")


@bp.route("/")
@login_required
@handle_service_errors
def index():
    q = request.args.get("q", "").strip()
    resource_type = request.args.get("type")
    if q:
        assets = services.search_assets(current_user, q)
    else:
        assets = services.list_assets(current_user, resource_type=resource_type or None)
    policies = services.list_policies(current_user)
    return render_template("archive_storage/index.html", assets=assets, policies=policies, q=q, resource_type=resource_type)


@bp.route("/<int:asset_id>/restore", methods=["POST"])
@login_required
@handle_service_errors
def restore(asset_id):
    services.restore_asset(current_user, asset_id)
    flash("Asset restored.", "success")
    return redirect(url_for("archive_storage.index"))
