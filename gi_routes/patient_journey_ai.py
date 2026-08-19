"""Patient Journey AI JSON routes — Gastro25."""

from __future__ import annotations

from flask import jsonify, request, session

from gi_platform.clinical_ai.permissions import PermissionDeniedError
from gi_platform.patient_journey import service as journey_ai_service

JOURNEY_AI_ROLES = (
    'admin', 'hod', 'consultant', 'specialist', 'registrar', 'general_endoscopy',
    'house_officer', 'pg_trainee', 'nurse_manager',
)


def register_patient_journey_ai_routes(app, *, get_db, login_required, roles_required):
    def _role():
        return session.get('role')

    def _user_id():
        return session.get('user_id')

    @app.route('/patient-journey-ai/status')
    @login_required
    @roles_required(*JOURNEY_AI_ROLES)
    def gi_journey_ai_status():
        return jsonify({'status': 'ok', 'version': 'g25.1'})

    @app.route('/patient-journey-ai/patient/<int:ward_patient_id>')
    @login_required
    @roles_required(*JOURNEY_AI_ROLES)
    def gi_journey_ai_view(ward_patient_id):
        db = get_db()
        history_session_id = request.args.get('history_session_id', type=int)
        try:
            return jsonify(journey_ai_service.get_journey_view(
                db, role=_role(), ward_patient_id=ward_patient_id,
                history_session_id=history_session_id,
            ))
        except PermissionDeniedError as exc:
            return jsonify({'error': str(exc)}), 403

    @app.route('/patient-journey-ai/history/<int:history_session_id>/follow-up', methods=['POST'])
    @login_required
    @roles_required(*JOURNEY_AI_ROLES)
    def gi_journey_ai_follow_up(history_session_id):
        db = get_db()
        payload = request.get_json(silent=True) or {}
        try:
            plan = journey_ai_service.create_follow_up_plan(
                db, role=_role(), user_id=_user_id(), history_session_id=history_session_id,
                related_condition=payload.get('related_condition'),
                recommended_interval_days=payload.get('recommended_interval_days'),
                recommended_interval_text=payload.get('recommended_interval_text'),
                reason=payload.get('reason'),
            )
            return jsonify({'follow_up_plan': plan}), 201
        except journey_ai_service.ValidationError as exc:
            return jsonify({'error': str(exc)}), 400
        except journey_ai_service.NotFoundError as exc:
            return jsonify({'error': str(exc)}), 404

    @app.route('/patient-journey-ai/history/<int:history_session_id>/summary/generate', methods=['POST'])
    @login_required
    @roles_required(*JOURNEY_AI_ROLES)
    def gi_journey_ai_summary(history_session_id):
        db = get_db()
        try:
            draft = journey_ai_service.generate_summary_draft(
                db, role=_role(), user_id=_user_id(), history_session_id=history_session_id,
            )
            return jsonify({'summary': draft}), 201
        except journey_ai_service.NotFoundError as exc:
            return jsonify({'error': str(exc)}), 404

    @app.route('/patient-journey-ai/summaries/<int:draft_id>/approve', methods=['POST'])
    @login_required
    @roles_required(*JOURNEY_AI_ROLES)
    def gi_journey_ai_approve_summary(draft_id):
        db = get_db()
        payload = request.get_json(silent=True) or {}
        try:
            draft = journey_ai_service.approve_summary(
                db, role=_role(), user_id=_user_id(), draft_id=draft_id,
                approved_text=payload.get('approved_text'),
            )
            return jsonify({'summary': draft})
        except journey_ai_service.NotFoundError as exc:
            return jsonify({'error': str(exc)}), 404
