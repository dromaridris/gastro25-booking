"""Clinical Interpretation JSON API routes — Gastro25."""

from __future__ import annotations

from flask import jsonify, request, session

from gi_platform.clinical_ai.permissions import PermissionDeniedError
from gi_platform.clinical_interpretation import service as interpretation_service

INTERPRETATION_ROLES = (
    'admin', 'hod', 'consultant', 'specialist', 'registrar', 'general_endoscopy',
    'house_officer', 'pg_trainee',
)


def register_interpretation_routes(app, *, get_db, login_required, roles_required):
    def _role():
        return session.get('role')

    def _user_id():
        return session.get('user_id')

    @app.route('/clinical-interpretation/status')
    @login_required
    @roles_required(*INTERPRETATION_ROLES)
    def gi_interpretation_status():
        return jsonify({'status': 'ok', 'version': 'g25.1'})

    @app.route('/clinical-interpretation/history/<int:history_session_id>/generate', methods=['POST'])
    @login_required
    @roles_required(*INTERPRETATION_ROLES)
    def gi_interpretation_generate(history_session_id):
        db = get_db()
        try:
            run = interpretation_service.generate_interpretation(
                db, role=_role(), user_id=_user_id(), history_session_id=history_session_id,
            )
            view = interpretation_service.get_interpretation_view(
                db, role=_role(), history_session_id=history_session_id,
            )
            return jsonify(view), 201
        except interpretation_service.ValidationError as exc:
            return jsonify({'error': str(exc)}), 400
        except interpretation_service.NotFoundError as exc:
            return jsonify({'error': str(exc)}), 404
        except PermissionDeniedError as exc:
            return jsonify({'error': str(exc)}), 403

    @app.route('/clinical-interpretation/history/<int:history_session_id>')
    @login_required
    @roles_required(*INTERPRETATION_ROLES)
    def gi_interpretation_get(history_session_id):
        db = get_db()
        try:
            return jsonify(interpretation_service.get_interpretation_view(
                db, role=_role(), history_session_id=history_session_id,
            ))
        except PermissionDeniedError as exc:
            return jsonify({'error': str(exc)}), 403

    @app.route('/clinical-interpretation/findings/<int:finding_id>/accept', methods=['POST'])
    @login_required
    @roles_required(*INTERPRETATION_ROLES)
    def gi_interpretation_accept(finding_id):
        db = get_db()
        payload = request.get_json(silent=True) or {}
        try:
            decision = interpretation_service.accept_finding(
                db, role=_role(), user_id=_user_id(), finding_id=finding_id,
                notes=payload.get('notes'),
            )
            return jsonify({'decision': decision})
        except interpretation_service.NotFoundError as exc:
            return jsonify({'error': str(exc)}), 404
        except PermissionDeniedError as exc:
            return jsonify({'error': str(exc)}), 403

    @app.route('/clinical-interpretation/findings/<int:finding_id>/reject', methods=['POST'])
    @login_required
    @roles_required(*INTERPRETATION_ROLES)
    def gi_interpretation_reject(finding_id):
        db = get_db()
        payload = request.get_json(silent=True) or {}
        try:
            decision = interpretation_service.reject_finding(
                db, role=_role(), user_id=_user_id(), finding_id=finding_id,
                notes=payload.get('notes'),
            )
            return jsonify({'decision': decision})
        except interpretation_service.NotFoundError as exc:
            return jsonify({'error': str(exc)}), 404
        except PermissionDeniedError as exc:
            return jsonify({'error': str(exc)}), 403
