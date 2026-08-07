"""Clinical AI routes — HTML UI + JSON infrastructure endpoints."""

from __future__ import annotations

import json

from flask import flash, jsonify, redirect, render_template, request, session, url_for

from gi_platform import ai_service, history_service
from gi_platform.catalogue_runtime import compute_differential_for_session
from gi_platform.clinical_ai.constants import ALL_PROMPT_TYPES, PROMPT_CLINICAL_REASONING
from gi_platform.clinical_ai.permissions import PermissionDeniedError

AI_ROLES = (
    'admin', 'specialist', 'pg_trainee', 'consultant', 'hod', 'registrar',
    'house_officer', 'general_endoscopy',
)


def register_ai_routes(app, *, get_db, login_required, roles_required):
    def _role():
        return session.get('role')

    def _user_id():
        return session.get('user_id')

    @app.route('/clinical-ai/patient/<int:ward_patient_id>')
    @login_required
    @roles_required(*AI_ROLES)
    def gi_ai_patient(ward_patient_id):
        db = get_db()
        sessions = ai_service.list_sessions(db, ward_patient_id)
        return render_template(
            'gi/ai_patient.html', ward_patient_id=ward_patient_id, sessions=sessions,
            back_url=url_for('ward_patient_view', ward_patient_id=ward_patient_id),
        )

    @app.route('/clinical-ai/patient/<int:ward_patient_id>/session', methods=['POST'])
    @login_required
    @roles_required(*AI_ROLES)
    def gi_ai_new_session(ward_patient_id):
        db = get_db()
        sid = ai_service.create_session(
            db, ward_patient_id=ward_patient_id, created_by=_user_id(),
        )
        return redirect(url_for('gi_ai_session', session_id=sid))

    @app.route('/clinical-ai/session/<int:session_id>', methods=['GET', 'POST'])
    @login_required
    @roles_required(*AI_ROLES)
    def gi_ai_session(session_id):
        db = get_db()
        sess = ai_service.get_session(db, session_id)
        if not sess:
            flash('AI session not found.', 'error')
            return redirect(url_for('ward_dashboard'))

        cds_hint = None
        hist = db.execute(
            """
            SELECT id, complaint_code FROM gi_history_session
            WHERE ward_patient_id = ? ORDER BY updated_at DESC LIMIT 1
            """,
            (sess['ward_patient_id'],),
        ).fetchone()
        if hist and hist['complaint_code']:
            cds_hint = compute_differential_for_session(db, hist['complaint_code'], hist['id'])

        svc = ai_service.get_clinical_ai_service(db, app.config)
        config_data = svc.get_configuration(role=_role())
        last_parsed = None

        if request.method == 'POST':
            prompt = (request.form.get('prompt') or '').strip()
            prompt_type = (request.form.get('prompt_type') or PROMPT_CLINICAL_REASONING).strip()
            if prompt:
                try:
                    result = svc.ask_session(
                        role=_role(), user_id=_user_id(), session_id=session_id,
                        prompt=prompt, prompt_type=prompt_type,
                    )
                    last_parsed = result.get('parsed_response')
                    if cds_hint and cds_hint.differentials and not last_parsed.get('narrative'):
                        top = ', '.join(d['title'] for d in cds_hint.differentials[:5])
                        last_parsed['cds_differential'] = top
                    flash('Clinical AI response generated.', 'success')
                except PermissionDeniedError:
                    flash('You do not have permission to use Clinical AI.', 'error')
                except Exception as exc:
                    flash(f'Clinical AI error: {exc}', 'error')

        logs = ai_service.list_logs(db, session_id)
        parsed_logs = []
        for log in logs:
            parsed = None
            if log['parsed_response_json'] if 'parsed_response_json' in log.keys() else None:
                try:
                    parsed = json.loads(log['parsed_response_json'])
                except json.JSONDecodeError:
                    parsed = None
            parsed_logs.append({'log': log, 'parsed': parsed})

        back_url = (
            url_for('ward_patient_view', ward_patient_id=sess['ward_patient_id'])
            if sess['ward_patient_id'] else url_for('ward_dashboard')
        )
        return render_template(
            'gi/ai_session.html',
            sess=sess,
            logs=logs,
            parsed_logs=parsed_logs,
            cds_hint=cds_hint,
            back_url=back_url,
            prompt_types=ALL_PROMPT_TYPES,
            active_provider=config_data.get('active_provider'),
            context_sources=config_data.get('available_context_sources', []),
            last_parsed=last_parsed,
        )

    @app.route('/clinical-ai/status')
    @login_required
    @roles_required(*AI_ROLES)
    def gi_ai_status():
        db = get_db()
        try:
            data = ai_service.get_clinical_ai_service(db, app.config).get_configuration(role=_role())
            return jsonify({'status': 'ok', **data})
        except PermissionDeniedError as exc:
            return jsonify({'status': 'error', 'message': str(exc)}), 403

    @app.route('/clinical-ai/config', methods=['GET'])
    @login_required
    @roles_required(*AI_ROLES)
    def gi_ai_config():
        db = get_db()
        try:
            return jsonify(ai_service.get_clinical_ai_service(db, app.config).get_configuration(role=_role()))
        except PermissionDeniedError as exc:
            return jsonify({'status': 'error', 'message': str(exc)}), 403

    @app.route('/clinical-ai/config/preview', methods=['POST'])
    @login_required
    @roles_required(*AI_ROLES)
    def gi_ai_config_preview():
        db = get_db()
        payload = request.get_json(silent=True) or {}
        try:
            data = ai_service.get_clinical_ai_service(db, app.config).update_configuration_preview(
                role=_role(), overrides=payload,
            )
            return jsonify(data)
        except PermissionDeniedError as exc:
            return jsonify({'status': 'error', 'message': str(exc)}), 403

    @app.route('/clinical-ai/sessions/run', methods=['POST'])
    @login_required
    @roles_required(*AI_ROLES)
    def gi_ai_run_session():
        db = get_db()
        payload = request.get_json(silent=True) or {}
        try:
            result = ai_service.get_clinical_ai_service(db, app.config).execute_infrastructure_request(
                role=_role(),
                user_id=_user_id(),
                prompt_type=payload.get('prompt_type', PROMPT_CLINICAL_REASONING),
                ward_patient_id=payload.get('ward_patient_id') or payload.get('patient_id'),
                history_session_id=payload.get('history_session_id') or payload.get('encounter_id'),
                context_sources=payload.get('context_sources'),
                topic_keys=payload.get('topic_keys'),
                object_types=payload.get('object_types'),
                provider_key=payload.get('provider_key'),
                user_question=payload.get('user_question'),
            )
            return jsonify(result)
        except PermissionDeniedError as exc:
            return jsonify({'status': 'error', 'message': str(exc)}), 403
        except Exception as exc:
            return jsonify({'status': 'error', 'message': str(exc)}), 500
