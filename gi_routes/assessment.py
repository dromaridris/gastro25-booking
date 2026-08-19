"""Clinical Assessment JSON API routes — Gastro25."""

from __future__ import annotations

from flask import jsonify, request, session

from gi_platform.clinical_ai.permissions import PermissionDeniedError
from gi_platform.clinical_assessment import service as assessment_service

ASSESSMENT_ROLES = (
    'admin', 'hod', 'consultant', 'specialist', 'registrar', 'general_endoscopy',
    'house_officer', 'pg_trainee',
)


def register_assessment_routes(app, *, get_db, login_required, roles_required):
    def _role():
        return session.get('role')

    def _user_id():
        return session.get('user_id')

    @app.route('/clinical-assessment/status')
    @login_required
    @roles_required(*ASSESSMENT_ROLES)
    def gi_assessment_status():
        return jsonify({'status': 'ok', 'version': 'g25.1'})

    @app.route('/clinical-assessment/history/<int:history_session_id>/generate', methods=['POST'])
    @login_required
    @roles_required(*ASSESSMENT_ROLES)
    def gi_assessment_generate(history_session_id):
        db = get_db()
        try:
            run = assessment_service.generate_assessment(
                db, role=_role(), user_id=_user_id(), history_session_id=history_session_id,
            )
            suggestions = assessment_service.list_suggestions(db, role=_role(), run_id=run['id'])
            return jsonify({'run': run, 'suggestions': suggestions}), 201
        except assessment_service.ValidationError as exc:
            return jsonify({'error': str(exc)}), 400
        except assessment_service.NotFoundError as exc:
            return jsonify({'error': str(exc)}), 404
        except PermissionDeniedError as exc:
            return jsonify({'error': str(exc)}), 403

    @app.route('/clinical-assessment/history/<int:history_session_id>')
    @login_required
    @roles_required(*ASSESSMENT_ROLES)
    def gi_assessment_get(history_session_id):
        db = get_db()
        try:
            return jsonify(assessment_service.get_final_assessment(
                db, role=_role(), history_session_id=history_session_id,
            ))
        except PermissionDeniedError as exc:
            return jsonify({'error': str(exc)}), 403

    @app.route('/clinical-assessment/runs/<int:run_id>/suggestions')
    @login_required
    @roles_required(*ASSESSMENT_ROLES)
    def gi_assessment_suggestions(run_id):
        db = get_db()
        try:
            suggestions = assessment_service.list_suggestions(db, role=_role(), run_id=run_id)
            return jsonify({'suggestions': suggestions})
        except assessment_service.NotFoundError as exc:
            return jsonify({'error': str(exc)}), 404
        except PermissionDeniedError as exc:
            return jsonify({'error': str(exc)}), 403

    @app.route('/clinical-assessment/suggestions/<int:suggestion_id>/accept', methods=['POST'])
    @login_required
    @roles_required(*ASSESSMENT_ROLES)
    def gi_assessment_accept(suggestion_id):
        db = get_db()
        payload = request.get_json(silent=True) or {}
        try:
            decision = assessment_service.accept_suggestion(
                db, role=_role(), user_id=_user_id(), suggestion_id=suggestion_id,
                notes=payload.get('notes'),
            )
            return jsonify({'decision': decision})
        except assessment_service.NotFoundError as exc:
            return jsonify({'error': str(exc)}), 404
        except PermissionDeniedError as exc:
            return jsonify({'error': str(exc)}), 403

    @app.route('/clinical-assessment/suggestions/<int:suggestion_id>/reject', methods=['POST'])
    @login_required
    @roles_required(*ASSESSMENT_ROLES)
    def gi_assessment_reject(suggestion_id):
        db = get_db()
        payload = request.get_json(silent=True) or {}
        try:
            decision = assessment_service.reject_suggestion(
                db, role=_role(), user_id=_user_id(), suggestion_id=suggestion_id,
                notes=payload.get('notes'),
            )
            return jsonify({'decision': decision})
        except assessment_service.NotFoundError as exc:
            return jsonify({'error': str(exc)}), 404
        except PermissionDeniedError as exc:
            return jsonify({'error': str(exc)}), 403

    @app.route('/clinical-assessment/suggestions/<int:suggestion_id>/confirm', methods=['POST'])
    @login_required
    @roles_required(*ASSESSMENT_ROLES)
    def gi_assessment_confirm(suggestion_id):
        db = get_db()
        payload = request.get_json(silent=True) or {}
        try:
            decision = assessment_service.confirm_diagnosis(
                db, role=_role(), user_id=_user_id(), suggestion_id=suggestion_id,
                notes=payload.get('notes'),
            )
            return jsonify({'decision': decision})
        except assessment_service.NotFoundError as exc:
            return jsonify({'error': str(exc)}), 404
        except PermissionDeniedError as exc:
            return jsonify({'error': str(exc)}), 403

    @app.route('/clinical-assessment/history/<int:history_session_id>/manual', methods=['POST'])
    @login_required
    @roles_required(*ASSESSMENT_ROLES)
    def gi_assessment_manual(history_session_id):
        db = get_db()
        payload = request.get_json(silent=True) or {}
        try:
            decision = assessment_service.add_manual_diagnosis(
                db, role=_role(), user_id=_user_id(), history_session_id=history_session_id,
                diagnosis_name=payload.get('diagnosis_name', ''),
                notes=payload.get('notes'),
            )
            return jsonify({'decision': decision}), 201
        except assessment_service.NotFoundError as exc:
            return jsonify({'error': str(exc)}), 404
        except PermissionDeniedError as exc:
            return jsonify({'error': str(exc)}), 403
