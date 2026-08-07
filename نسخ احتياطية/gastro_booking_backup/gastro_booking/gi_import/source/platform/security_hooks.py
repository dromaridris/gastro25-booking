"""Production security hooks — presentation-layer guards without modifying frozen modules."""

from flask import abort, request
from flask_login import current_user


def register_security_hooks(app):
    """Enforce RBAC on routes that lack explicit GET-time permission checks."""

    @app.before_request
    def _track_ui_navigation():
        from app.ui.navigation_history import track_navigation_visit

        track_navigation_visit()

    @app.before_request
    def _guard_admin_routes():
        endpoint = request.endpoint or ""
        if endpoint == "branding.settings" and request.method in ("GET", "POST"):
            if not getattr(current_user, "is_authenticated", False):
                return None
            from app.engines import permission_engine

            if not permission_engine.check(current_user, "branding:manage"):
                abort(403)
