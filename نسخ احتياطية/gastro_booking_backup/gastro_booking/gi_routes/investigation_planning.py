"""Investigation Planning JSON API routes — Gastro25."""

from __future__ import annotations

from flask import jsonify, request, session

from gi_platform.clinical_ai.permissions import PermissionDeniedError
from gi_platform.investigation_planning import service as planning_service

PLANNING_ROLES = (
    'admin', 'hod', 'consultant', 'specialist', 'registrar', 'general_endoscopy',
    'house_officer', 'pg_trainee',
)


def register_investigation_planning_routes(app, *, get_db, login_required, roles_required):
    def _role():
        return session.get('role')

    def _user_id():
        return session.get('user_id')

    @app.route('/investigation-planning/status')
    @login_required
    @roles_required(*PLANNING_ROLES)
    def gi_investigation_planning_status():
        return jsonify({'status': 'ok', 'version': 'g25.1'})

    @app.route('/investigation-planning/history/<int:history_session_id>/generate', methods=['POST'])
    @login_required
    @roles_required(*PLANNING_ROLES)
    def gi_investigation_plan_generate(history_session_id):
        db = get_db()
        try:
            plan = planning_service.generate_plan(
                db, role=_role(), user_id=_user_id(), history_session_id=history_session_id,
            )
            suggestions = planning_service.list_suggestions(db, role=_role(), plan_id=plan['id'])
            return jsonify({'plan': plan, 'suggestions': suggestions}), 201
        except planning_service.ValidationError as exc:
            return jsonify({'error': str(exc)}), 400
        except planning_service.NotFoundError as exc:
            return jsonify({'error': str(exc)}), 404
        except PermissionDeniedError as exc:
            return jsonify({'error': str(exc)}), 403

    @app.route('/investigation-planning/history/<int:history_session_id>')
    @login_required
    @roles_required(*PLANNING_ROLES)
    def gi_investigation_plan_get(history_session_id):
        db = get_db()
        try:
            return jsonify(planning_service.get_plan_view(
                db, role=_role(), history_session_id=history_session_id,
            ))
        except PermissionDeniedError as exc:
            return jsonify({'error': str(exc)}), 403

    @app.route('/investigation-planning/plans/<int:plan_id>/review', methods=['POST'])
    @login_required
    @roles_required(*PLANNING_ROLES)
    def gi_investigation_plan_review(plan_id):
        db = get_db()
        try:
            return jsonify({'plan': planning_service.review_plan(db, role=_role(), plan_id=plan_id)})
        except planning_service.NotFoundError as exc:
            return jsonify({'error': str(exc)}), 404

    @app.route('/investigation-planning/plans/<int:plan_id>/approve', methods=['POST'])
    @login_required
    @roles_required(*PLANNING_ROLES)
    def gi_investigation_plan_approve(plan_id):
        db = get_db()
        try:
            return jsonify({'plan': planning_service.approve_plan(
                db, role=_role(), user_id=_user_id(), plan_id=plan_id,
            )})
        except planning_service.NotFoundError as exc:
            return jsonify({'error': str(exc)}), 404

    @app.route('/investigation-planning/suggestions/<int:suggestion_id>/accept', methods=['POST'])
    @login_required
    @roles_required(*PLANNING_ROLES)
    def gi_investigation_suggestion_accept(suggestion_id):
        db = get_db()
        payload = request.get_json(silent=True) or {}
        try:
            decision = planning_service.accept_suggestion(
                db, role=_role(), user_id=_user_id(), suggestion_id=suggestion_id,
                reason=payload.get('reason'),
            )
            return jsonify({'decision': decision})
        except planning_service.NotFoundError as exc:
            return jsonify({'error': str(exc)}), 404

    @app.route('/investigation-planning/suggestions/<int:suggestion_id>/reject', methods=['POST'])
    @login_required
    @roles_required(*PLANNING_ROLES)
    def gi_investigation_suggestion_reject(suggestion_id):
        db = get_db()
        payload = request.get_json(silent=True) or {}
        try:
            decision = planning_service.reject_suggestion(
                db, role=_role(), user_id=_user_id(), suggestion_id=suggestion_id,
                reason=payload.get('reason'),
            )
            return jsonify({'decision': decision})
        except planning_service.NotFoundError as exc:
            return jsonify({'error': str(exc)}), 404

    @app.route('/investigation-planning/history/<int:history_session_id>/manual', methods=['POST'])
    @login_required
    @roles_required(*PLANNING_ROLES)
    def gi_investigation_manual(history_session_id):
        db = get_db()
        payload = request.get_json(silent=True) or {}
        try:
            decision = planning_service.add_manual_investigation(
                db, role=_role(), user_id=_user_id(), history_session_id=history_session_id,
                investigation_name=payload.get('investigation_name', ''),
                category=payload.get('category'), priority=payload.get('priority'),
                reason=payload.get('reason'),
            )
            return jsonify({'decision': decision}), 201
        except planning_service.NotFoundError as exc:
            return jsonify({'error': str(exc)}), 404
