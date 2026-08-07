"""Analytics JSON routes — Gastro25."""

from __future__ import annotations

from flask import jsonify, session

from gi_platform.analytics import service as analytics_service
from gi_platform.clinical_ai.permissions import PermissionDeniedError

ANALYTICS_ROLES = ('admin', 'hod', 'consultant', 'specialist')


def register_analytics_routes(app, *, get_db, login_required, roles_required):
    def _role():
        return session.get('role')

    def _user_id():
        return session.get('user_id')

    @app.route('/analytics/status')
    @login_required
    @roles_required(*ANALYTICS_ROLES)
    def gi_analytics_status():
        return jsonify({'status': 'ok', 'version': 'g25.1'})

    @app.route('/analytics/metrics')
    @login_required
    @roles_required(*ANALYTICS_ROLES)
    def gi_analytics_metrics():
        db = get_db()
        try:
            return jsonify({'metrics': analytics_service.list_metrics(db, role=_role())})
        except PermissionDeniedError as exc:
            return jsonify({'error': str(exc)}), 403

    @app.route('/analytics/run/<metric_id>')
    @login_required
    @roles_required(*ANALYTICS_ROLES)
    def gi_analytics_run(metric_id):
        db = get_db()
        try:
            return jsonify(analytics_service.run_metric(
                db, role=_role(), user_id=_user_id(), metric_id=metric_id,
            ))
        except ValueError as exc:
            return jsonify({'error': str(exc)}), 400
        except PermissionDeniedError as exc:
            return jsonify({'error': str(exc)}), 403
