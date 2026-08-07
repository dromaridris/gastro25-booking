from flask import Blueprint, current_app, jsonify, request, send_from_directory
from flask_login import current_user, login_required

bp = Blueprint("core", __name__)


@bp.route("/")
@login_required
def dashboard():
    """Role-based homepage — delegates to Workforce & Training Platform (Sprint 7A)."""
    from flask import redirect, url_for

    from app.engines import permission_engine

    if permission_engine.check(current_user, "workforce:view_own"):
        return redirect(url_for("workforce.home"))
    from flask import render_template

    return render_template("dashboard.html")


@bp.route("/files/<path:key>")
@login_required
def serve_file(key):
    """
    Serves files stored via LocalStorageBackend. This route is the ONLY
    place that touches STORAGE_LOCAL_ROOT directly for reads — everything
    else goes through the StorageBackend interface. When a cloud backend
    is added later, this route becomes unnecessary for cloud-stored files
    (their url_for() will return a signed URL instead), so callers that
    used backend.url_for(key) never need to change.
    """
    root = current_app.config["STORAGE_LOCAL_ROOT"]
    return send_from_directory(root, key)


@bp.route("/qr/<entity>/<int:entity_id>")
@login_required
def qr_code(entity, entity_id):
    from flask import Response
    from app.platform.qr_service import generate_qr_png

    try:
        png = generate_qr_png(entity, entity_id)
    except ValueError:
        from flask import abort
        abort(404)
    return Response(png, mimetype="image/png")


@bp.route("/api/productivity/sync", methods=["POST"])
@login_required
def productivity_sync():
    from app.platform.productivity_service import prefs_to_dict, sync_prefs

    payload = request.get_json(silent=True) or {}
    prefs = sync_prefs(
        current_user.id,
        favorites=payload.get("favorites"),
        recent_pages=payload.get("recent_pages"),
    )
    return jsonify(prefs)


@bp.route("/api/productivity", methods=["GET"])
@login_required
def productivity_get():
    from app.platform.productivity_service import get_prefs, prefs_to_dict

    return jsonify(prefs_to_dict(get_prefs(current_user.id)))
