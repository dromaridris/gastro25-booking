"""Documentation AI JSON API routes — Gastro25."""

from __future__ import annotations

from flask import jsonify, request, session

from gi_platform.clinical_ai.permissions import PermissionDeniedError
from gi_platform.documentation_ai import service as doc_service

DOC_ROLES = (
    'admin', 'hod', 'consultant', 'specialist', 'registrar', 'general_endoscopy',
    'house_officer', 'pg_trainee',
)


def register_documentation_ai_routes(app, *, get_db, login_required, roles_required):
    def _role():
        return session.get('role')

    def _user_id():
        return session.get('user_id')

    @app.route('/documentation-ai/status')
    @login_required
    @roles_required(*DOC_ROLES)
    def gi_documentation_status():
        return jsonify({'status': 'ok', 'version': 'g25.1'})

    @app.route('/documentation-ai/templates')
    @login_required
    @roles_required(*DOC_ROLES)
    def gi_documentation_templates():
        db = get_db()
        try:
            return jsonify({'templates': doc_service.list_templates(db, role=_role())})
        except PermissionDeniedError as exc:
            return jsonify({'error': str(exc)}), 403

    @app.route('/documentation-ai/history/<int:history_session_id>/generate', methods=['POST'])
    @login_required
    @roles_required(*DOC_ROLES)
    def gi_documentation_generate(history_session_id):
        db = get_db()
        payload = request.get_json(silent=True) or {}
        template_key = payload.get('template_key', 'doc.admission.gi')
        try:
            doc = doc_service.generate_document(
                db, role=_role(), user_id=_user_id(), history_session_id=history_session_id,
                template_key=template_key,
            )
            view = doc_service.get_document_view(db, role=_role(), document_id=doc['id'])
            return jsonify(view), 201
        except doc_service.ValidationError as exc:
            return jsonify({'error': str(exc)}), 400
        except doc_service.NotFoundError as exc:
            return jsonify({'error': str(exc)}), 404
        except PermissionDeniedError as exc:
            return jsonify({'error': str(exc)}), 403

    @app.route('/documentation-ai/documents/<int:document_id>')
    @login_required
    @roles_required(*DOC_ROLES)
    def gi_documentation_get(document_id):
        db = get_db()
        try:
            return jsonify(doc_service.get_document_view(db, role=_role(), document_id=document_id))
        except doc_service.NotFoundError as exc:
            return jsonify({'error': str(exc)}), 404

    @app.route('/documentation-ai/sections/<int:section_id>/edit', methods=['POST'])
    @login_required
    @roles_required(*DOC_ROLES)
    def gi_documentation_edit_section(section_id):
        db = get_db()
        payload = request.get_json(silent=True) or {}
        try:
            section = doc_service.edit_section(
                db, role=_role(), user_id=_user_id(), section_id=section_id,
                content=payload.get('content', ''), notes=payload.get('notes'),
            )
            return jsonify({'section': section})
        except doc_service.NotFoundError as exc:
            return jsonify({'error': str(exc)}), 404

    @app.route('/documentation-ai/documents/<int:document_id>/approve', methods=['POST'])
    @login_required
    @roles_required(*DOC_ROLES)
    def gi_documentation_approve(document_id):
        db = get_db()
        payload = request.get_json(silent=True) or {}
        try:
            doc = doc_service.approve_document(
                db, role=_role(), user_id=_user_id(), document_id=document_id,
                notes=payload.get('notes'),
            )
            return jsonify({'document': doc})
        except doc_service.ValidationError as exc:
            return jsonify({'error': str(exc)}), 400
        except doc_service.NotFoundError as exc:
            return jsonify({'error': str(exc)}), 404

    @app.route('/documentation-ai/documents/<int:document_id>/sign', methods=['POST'])
    @login_required
    @roles_required(*DOC_ROLES)
    def gi_documentation_sign(document_id):
        db = get_db()
        try:
            signed = doc_service.sign_document(
                db, role=_role(), user_id=_user_id(), document_id=document_id,
            )
            return jsonify({'signed_document': signed})
        except doc_service.ValidationError as exc:
            return jsonify({'error': str(exc)}), 400
        except PermissionDeniedError as exc:
            return jsonify({'error': str(exc)}), 403
