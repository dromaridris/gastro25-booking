from flask import Blueprint, abort, render_template
from flask_login import current_user, login_required

from app.core.exceptions import PermissionDeniedError
from app.engines import audit_engine, permission_engine

bp = Blueprint("audit", __name__, url_prefix="/audit")


@bp.route("/")
@login_required
def list_logs():
    try:
        permission_engine.require(
            current_user, "audit_log:view", audit_context={"target_type": "AuditLog"}
        )
    except PermissionDeniedError:
        abort(403)

    entries = audit_engine.list_recent(limit=200)
    return render_template("audit/list.html", entries=entries)
