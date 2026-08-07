"""CDS JSON API routes — decision_support orchestrator."""

from __future__ import annotations

from flask import jsonify, request

from gi_platform.decision_support.adapters import (
    build_context_from_session,
    interview_step_to_legacy,
    to_legacy_result,
)
from gi_platform.decision_support.interview_driver import ClinicalInterviewDriver
from gi_platform.decision_support.service import get_decision_support_service

CDS_ROLES = (
    'admin', 'specialist', 'pg_trainee', 'consultant', 'hod', 'registrar',
    'house_officer', 'general_endoscopy',
)


def register_cds_routes(app, *, get_db, login_required, roles_required):
    @app.route('/clinical-cds/status')
    @login_required
    @roles_required(*CDS_ROLES)
    def gi_cds_status():
        db = get_db()
        complaint = (request.args.get('complaint_code') or '').strip()
        driver = ClinicalInterviewDriver(db)
        return jsonify({
            'status': 'ok',
            'provider_key': 'sqlite_knowledge',
            'kl_drives_complaint': driver.kl_drives_complaint(complaint) if complaint else None,
        })

    @app.route('/clinical-cds/assess', methods=['POST'])
    @login_required
    @roles_required(*CDS_ROLES)
    def gi_cds_assess():
        db = get_db()
        payload = request.get_json(silent=True) or {}
        ctx = build_context_from_session(
            db,
            session_id=payload.get('session_id'),
            complaint_code=payload.get('complaint_code', ''),
            ward_patient_id=payload.get('ward_patient_id'),
            teaching_mode=bool(payload.get('teaching_mode')),
        )
        if payload.get('answers'):
            ctx.answers.update({str(k): str(v) for k, v in payload['answers'].items()})
            ctx.answered_question_codes.update(ctx.answers.keys())
        svc = get_decision_support_service(db)
        if payload.get('report_safe'):
            result = svc.assess_for_report(ctx)
        else:
            result = svc.assess(ctx)
        return jsonify(to_legacy_result(result).__dict__)

    @app.route('/clinical-cds/interview/advance', methods=['POST'])
    @login_required
    @roles_required(*CDS_ROLES)
    def gi_cds_interview_advance():
        db = get_db()
        payload = request.get_json(silent=True) or {}
        ctx = build_context_from_session(
            db,
            session_id=payload.get('session_id'),
            complaint_code=payload.get('complaint_code', ''),
            ward_patient_id=payload.get('ward_patient_id'),
            teaching_mode=bool(payload.get('teaching_mode')),
        )
        if payload.get('answers'):
            ctx.answers.update({str(k): str(v) for k, v in payload['answers'].items()})
        driver = ClinicalInterviewDriver(db)
        step = driver.advance(ctx)
        data = interview_step_to_legacy(step).__dict__
        data['interview_complete'] = step.interview_complete
        data['active_branches'] = step.active_branches
        data['questions_answered'] = step.questions_answered
        if step.next_question:
            data['next_question'] = {
                'question_code': step.next_question.question_code,
                'prompt': step.next_question.prompt,
                'diagnostic_value': step.next_question.diagnostic_value,
                'purpose': step.next_question.purpose,
                'rationale': step.next_question.rationale,
            }
        return jsonify(data)

    @app.route('/clinical-cds/interview/answer', methods=['POST'])
    @login_required
    @roles_required(*CDS_ROLES)
    def gi_cds_interview_answer():
        db = get_db()
        payload = request.get_json(silent=True) or {}
        qcode = payload.get('question_code', '')
        answer = payload.get('answer', '')
        ctx = build_context_from_session(
            db,
            session_id=payload.get('session_id'),
            complaint_code=payload.get('complaint_code', ''),
            ward_patient_id=payload.get('ward_patient_id'),
            teaching_mode=bool(payload.get('teaching_mode')),
        )
        if payload.get('answers'):
            ctx.answers.update({str(k): str(v) for k, v in payload['answers'].items()})
        driver = ClinicalInterviewDriver(db)
        step = driver.on_answer(ctx, qcode, answer)
        data = interview_step_to_legacy(step).__dict__
        data['interview_complete'] = step.interview_complete
        if step.next_question:
            data['next_question'] = {
                'question_code': step.next_question.question_code,
                'prompt': step.next_question.prompt,
                'diagnostic_value': step.next_question.diagnostic_value,
            }
        return jsonify(data)
