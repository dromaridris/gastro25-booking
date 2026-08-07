"""Management Plan AI JSON API routes — Gastro25."""

from __future__ import annotations

from flask import jsonify, request, session

from gi_platform.clinical_ai.permissions import PermissionDeniedError
from gi_platform.management_plan_ai import service as mgmt_service

MGMT_ROLES = (
    'admin', 'hod', 'consultant', 'specialist', 'registrar', 'general_endoscopy',
    'house_officer', 'pg_trainee',
)


def register_management_plan_routes(app, *, get_db, login_required, roles_required):
    def _role():
        return session.get('role')

    def _user_id():
        return session.get('user_id')

    @app.route('/management-plan/status')
    @login_required
    @roles_required(*MGMT_ROLES)
    def gi_management_plan_status():
        return jsonify({'status': 'ok', 'version': 'g25.1'})

    @app.route('/management-plan/history/<int:history_session_id>/generate', methods=['POST'])
    @login_required
    @roles_required(*MGMT_ROLES)
    def gi_management_plan_generate(history_session_id):
        db = get_db()
        try:
            plan = mgmt_service.generate_plan(
                db, role=_role(), user_id=_user_id(), history_session_id=history_session_id,
            )
            suggestions = mgmt_service.list_suggestions(db, role=_role(), plan_id=plan['id'])
            return jsonify({'plan': plan, 'suggestions': suggestions}), 201
        except mgmt_service.ValidationError as exc:
            return jsonify({'error': str(exc)}), 400
        except mgmt_service.NotFoundError as exc:
            return jsonify({'error': str(exc)}), 404
        except PermissionDeniedError as exc:
            return jsonify({'error': str(exc)}), 403

    @app.route('/management-plan/history/<int:history_session_id>')
    @login_required
    @roles_required(*MGMT_ROLES)
    def gi_management_plan_get(history_session_id):
        db = get_db()
        try:
            return jsonify(mgmt_service.get_plan_view(
                db, role=_role(), history_session_id=history_session_id,
            ))
        except PermissionDeniedError as exc:
            return jsonify({'error': str(exc)}), 403

    @app.route('/management-plan/plans/<int:plan_id>/review', methods=['POST'])
    @login_required
    @roles_required(*MGMT_ROLES)
    def gi_management_plan_review(plan_id):
        db = get_db()
        try:
            return jsonify({'plan': mgmt_service.review_plan(db, role=_role(), plan_id=plan_id)})
        except mgmt_service.NotFoundError as exc:
            return jsonify({'error': str(exc)}), 404

    @app.route('/management-plan/plans/<int:plan_id>/approve', methods=['POST'])
    @login_required
    @roles_required(*MGMT_ROLES)
    def gi_management_plan_approve(plan_id):
        db = get_db()
        try:
            return jsonify({'plan': mgmt_service.approve_plan(
                db, role=_role(), user_id=_user_id(), plan_id=plan_id,
            )})
        except mgmt_service.NotFoundError as exc:
            return jsonify({'error': str(exc)}), 404

    @app.route('/management-plan/suggestions/<int:suggestion_id>/accept', methods=['POST'])
    @login_required
    @roles_required(*MGMT_ROLES)
    def gi_management_suggestion_accept(suggestion_id):
        db = get_db()
        payload = request.get_json(silent=True) or {}
        try:
            decision = mgmt_service.accept_suggestion(
                db, role=_role(), user_id=_user_id(), suggestion_id=suggestion_id,
                notes=payload.get('notes'),
            )
            return jsonify({'decision': decision})
        except mgmt_service.NotFoundError as exc:
            return jsonify({'error': str(exc)}), 404

    @app.route('/management-plan/suggestions/<int:suggestion_id>/reject', methods=['POST'])
    @login_required
    @roles_required(*MGMT_ROLES)
    def gi_management_suggestion_reject(suggestion_id):
        db = get_db()
        payload = request.get_json(silent=True) or {}
        try:
            decision = mgmt_service.reject_suggestion(
                db, role=_role(), user_id=_user_id(), suggestion_id=suggestion_id,
                notes=payload.get('notes'),
            )
            return jsonify({'decision': decision})
        except mgmt_service.NotFoundError as exc:
            return jsonify({'error': str(exc)}), 404

    @app.route('/management-plan/history/<int:history_session_id>/manual', methods=['POST'])
    @login_required
    @roles_required(*MGMT_ROLES)
    def gi_management_manual(history_session_id):
        db = get_db()
        payload = request.get_json(silent=True) or {}
        try:
            decision = mgmt_service.add_manual_plan_item(
                db, role=_role(), user_id=_user_id(), history_session_id=history_session_id,
                description=payload.get('description', ''),
                category=payload.get('category'), notes=payload.get('notes'),
            )
            return jsonify({'decision': decision}), 201
        except mgmt_service.NotFoundError as exc:
            return jsonify({'error': str(exc)}), 404
