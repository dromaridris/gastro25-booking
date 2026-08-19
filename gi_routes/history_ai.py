"""Clinical History AI routes — JSON API + guided UI."""

from __future__ import annotations

from flask import flash, jsonify, redirect, render_template, request, session, url_for

from gi_platform import history_service
from gi_platform.clinical_ai.permissions import PermissionDeniedError
from gi_platform.clinical_history_ai import service as gh_service

HISTORY_AI_ROLES = (
    'admin', 'hod', 'consultant', 'specialist', 'registrar', 'general_endoscopy',
    'house_officer', 'pg_trainee', 'nurse_manager', 'staff_nurse',
)


def register_history_ai_routes(app, *, get_db, login_required, roles_required):
    def _role():
        return session.get('role')

    def _user_id():
        return session.get('user_id')

    @app.route('/clinical-history-ai/patient/<int:ward_patient_id>')
    @login_required
    @roles_required(*HISTORY_AI_ROLES)
    def gi_guided_history_ui(ward_patient_id):
        db = get_db()
        wp = db.execute('SELECT * FROM ward_patient WHERE id = ?', (ward_patient_id,)).fetchone()
        if not wp:
            flash('Patient not found.', 'error')
            return redirect(url_for('ward_dashboard'))

        hist_row = db.execute(
            """
            SELECT id FROM gi_history_session
            WHERE ward_patient_id = ? ORDER BY updated_at DESC LIMIT 1
            """,
            (ward_patient_id,),
        ).fetchone()
        if not hist_row:
            hist_id_val = history_service.create_session(
                db, ward_patient_id=ward_patient_id, mrn=wp['mrn'] or '',
                created_by=_user_id(),
            )
        else:
            hist_id_val = hist_row['id']

        gh_sess = gh_service.get_session_for_history(db, role=_role(), history_session_id=hist_id_val)
        questions, draft = [], None
        if gh_sess:
            questions = gh_service.get_next_questions(
                db, role=_role(), user_id=_user_id(), session_id=gh_sess['id'], limit=5,
            )
            latest = db.execute(
                """
                SELECT * FROM gi_guided_history_draft
                WHERE session_id = ? ORDER BY created_at DESC LIMIT 1
                """,
                (gh_sess['id'],),
            ).fetchone()
            if latest:
                draft = gh_service.draft_to_dict(latest)

        hist = history_service.get_session(db, hist_id_val)
        return render_template(
            'gi/guided_history.html',
            patient=wp,
            history_session_id=hist_id_val,
            hist=hist,
            gh_session=gh_sess,
            questions=questions,
            draft=draft,
            back_url=url_for('gi_clinical_workflow', ward_patient_id=ward_patient_id),
        )

    @app.route('/clinical-history-ai/patient/<int:ward_patient_id>/start', methods=['POST'])
    @login_required
    @roles_required(*HISTORY_AI_ROLES)
    def gi_guided_history_start(ward_patient_id):
        db = get_db()
        history_session_id = int(request.form.get('history_session_id') or 0)
        complaint_code = (request.form.get('complaint_code') or '').strip()
        if complaint_code:
            history_service.set_complaint(db, history_session_id, complaint_code, complaint_code)
        if not history_session_id:
            flash('History session required.', 'error')
            return redirect(url_for('gi_guided_history_ui', ward_patient_id=ward_patient_id))
        try:
            gh_service.start_guided_session(
                db, role=_role(), user_id=_user_id(),
                history_session_id=history_session_id, ward_patient_id=ward_patient_id,
            )
            flash('Guided history session started.', 'success')
        except PermissionDeniedError:
            flash('Permission denied.', 'error')
        return redirect(url_for('gi_guided_history_ui', ward_patient_id=ward_patient_id))

    @app.route('/clinical-history-ai/sessions/<int:session_id>/answer', methods=['POST'])
    @login_required
    @roles_required(*HISTORY_AI_ROLES)
    def gi_guided_history_answer(session_id):
        db = get_db()
        gh_sess = gh_service.get_session(db, role=_role(), session_id=session_id)
        answers = {}
        for key in request.form:
            if key.startswith('answer_'):
                answers[key.replace('answer_', '')] = request.form.get(key, '')
        if answers:
            gh_service.save_answers(db, role=_role(), user_id=_user_id(), session_id=session_id, answers=answers)
            flash('Answers saved.', 'success')
        return redirect(url_for('gi_guided_history_ui', ward_patient_id=gh_sess['ward_patient_id']))

    @app.route('/clinical-history-ai/sessions/<int:session_id>/generate', methods=['POST'])
    @login_required
    @roles_required(*HISTORY_AI_ROLES)
    def gi_guided_history_generate(session_id):
        db = get_db()
        gh_sess = gh_service.get_session(db, role=_role(), session_id=session_id)
        try:
            gh_service.generate_history_draft(db, role=_role(), user_id=_user_id(), session_id=session_id)
            flash('History draft generated.', 'success')
        except gh_service.ValidationError as exc:
            flash(str(exc), 'error')
        except PermissionDeniedError:
            flash('Permission denied.', 'error')
        return redirect(url_for('gi_guided_history_ui', ward_patient_id=gh_sess['ward_patient_id']))

    @app.route('/clinical-history-ai/drafts/<int:draft_id>/approve', methods=['POST'])
    @login_required
    @roles_required(*HISTORY_AI_ROLES)
    def gi_guided_history_approve(draft_id):
        db = get_db()
        draft = gh_service.approve_draft(db, role=_role(), user_id=_user_id(), draft_id=draft_id)
        row = gh_service.get_session(db, role=_role(), session_id=draft['session_id'])
        flash('Draft approved and synced to clinical summary.', 'success')
        return redirect(url_for('gi_clinical_workflow', ward_patient_id=row['ward_patient_id']) + '#summary')

    # JSON API (GI parity)
    @app.route('/clinical-history-ai/api/history/<int:history_session_id>/start', methods=['POST'])
    @login_required
    @roles_required(*HISTORY_AI_ROLES)
    def gi_guided_history_api_start(history_session_id):
        db = get_db()
        try:
            sess = gh_service.start_guided_session(
                db, role=_role(), user_id=_user_id(), history_session_id=history_session_id,
            )
            return jsonify({'session': gh_service.session_to_dict(db, sess)}), 201
        except PermissionDeniedError as exc:
            return jsonify({'error': str(exc)}), 403

    @app.route('/clinical-history-ai/api/sessions/<int:session_id>', methods=['GET'])
    @login_required
    @roles_required(*HISTORY_AI_ROLES)
    def gi_guided_history_api_get(session_id):
        db = get_db()
        try:
            sess = gh_service.get_session(db, role=_role(), session_id=session_id)
            return jsonify({'session': gh_service.session_to_dict(db, sess)})
        except gh_service.NotFoundError as exc:
            return jsonify({'error': str(exc)}), 404

    @app.route('/clinical-history-ai/api/sessions/<int:session_id>/questions', methods=['GET'])
    @login_required
    @roles_required(*HISTORY_AI_ROLES)
    def gi_guided_history_api_questions(session_id):
        db = get_db()
        limit = min(int(request.args.get('limit', 5)), 20)
        questions = gh_service.get_next_questions(
            db, role=_role(), user_id=_user_id(), session_id=session_id, limit=limit,
        )
        return jsonify({'questions': questions})

    @app.route('/clinical-history-ai/api/sessions/<int:session_id>/answers', methods=['POST'])
    @login_required
    @roles_required(*HISTORY_AI_ROLES)
    def gi_guided_history_api_answers(session_id):
        db = get_db()
        payload = request.get_json(silent=True) or {}
        sess = gh_service.save_answers(
            db, role=_role(), user_id=_user_id(),
            session_id=session_id, answers=payload.get('answers') or {},
        )
        return jsonify({'session': gh_service.session_to_dict(db, sess)})

    @app.route('/clinical-history-ai/api/sessions/<int:session_id>/generate', methods=['POST'])
    @login_required
    @roles_required(*HISTORY_AI_ROLES)
    def gi_guided_history_api_generate(session_id):
        db = get_db()
        try:
            draft = gh_service.generate_history_draft(
                db, role=_role(), user_id=_user_id(), session_id=session_id,
            )
            return jsonify({'draft': draft}), 201
        except gh_service.ValidationError as exc:
            return jsonify({'error': str(exc)}), 400

    @app.route('/clinical-history-ai/api/drafts/<int:draft_id>/approve', methods=['POST'])
    @login_required
    @roles_required(*HISTORY_AI_ROLES)
    def gi_guided_history_api_approve(draft_id):
        db = get_db()
        draft = gh_service.approve_draft(db, role=_role(), user_id=_user_id(), draft_id=draft_id)
        return jsonify({'draft': draft})
