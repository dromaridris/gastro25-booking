"""History AI training admin routes — HOD, admin, specialist (legacy, write-frozen)."""

from __future__ import annotations

import json

from flask import flash, redirect, render_template, request, url_for

from gi_platform.catalogue_runtime import list_complaints
from gi_platform.history_ai_training.service import (
    TRAINING_ROLES, CATEGORIES, QUESTION_TYPES,
    add_complaint_rule, create_question, delete_question, delete_rule,
    list_questions, list_rules_for_complaint, update_question,
)
from gi_platform.legacy_history_freeze import (
    FREEZE_MESSAGE,
    legacy_history_writes_frozen,
)


def _block_write_if_frozen():
    if legacy_history_writes_frozen():
        flash(FREEZE_MESSAGE, 'error')
        return True
    return False


def register_history_ai_training_routes(app, *, get_db, login_required, roles_required):
    @app.route('/admin/history-ai-training')
    @login_required
    @roles_required(*TRAINING_ROLES)
    def gi_history_ai_training():
        db = get_db()
        from gi_platform.complaints_extra_seed import seed_extra_complaints_if_missing, seed_symptom_training_questions
        # Idempotent catalogue seeds only (not admin template edits)
        seed_extra_complaints_if_missing(db)
        seed_symptom_training_questions(db)
        questions = list_questions(db, q=(request.args.get('q') or ''))
        complaints = list_complaints(db)
        complaint_code = request.args.get('complaint') or (complaints[0]['code'] if complaints else '')
        rules = list_rules_for_complaint(db, complaint_code) if complaint_code else []
        return render_template(
            'gi/history_ai_training.html',
            questions=questions, complaints=complaints, rules=rules,
            complaint_code=complaint_code,
            categories=CATEGORIES, question_types=QUESTION_TYPES,
            writes_frozen=legacy_history_writes_frozen(),
        )

    @app.route('/admin/history-ai-training/question', methods=['POST'])
    @login_required
    @roles_required(*TRAINING_ROLES)
    def gi_history_ai_training_add_question():
        if _block_write_if_frozen():
            return redirect(url_for('gi_history_ai_training'))
        db = get_db()
        qid = (request.form.get('question_id') or '').strip()
        if not qid:
            flash('Question ID required.', 'error')
            return redirect(url_for('gi_history_ai_training'))
        opts = [o.strip() for o in (request.form.get('answer_options') or '').split(',') if o.strip()]
        cond_raw = (request.form.get('conditional_rules_json') or '').strip()
        cond = json.loads(cond_raw) if cond_raw else {}
        create_question(
            db,
            question_id=qid,
            question_text=(request.form.get('question_text') or '').strip(),
            category=(request.form.get('category') or 'history_of_present_illness').strip(),
            question_type=(request.form.get('question_type') or 'boolean').strip(),
            answer_options=opts,
            is_required=bool(request.form.get('is_required')),
            priority=request.form.get('priority', type=int) or 100,
            conditional_rules=cond,
            clinical_purpose=(request.form.get('clinical_purpose') or '').strip(),
        )
        flash(f'Question {qid} created.', 'success')
        return redirect(url_for('gi_history_ai_training'))

    @app.route('/admin/history-ai-training/question/<question_id>', methods=['POST'])
    @login_required
    @roles_required(*TRAINING_ROLES)
    def gi_history_ai_training_update_question(question_id):
        if _block_write_if_frozen():
            return redirect(url_for('gi_history_ai_training', q=question_id))
        db = get_db()
        action = request.form.get('action', 'save')
        if action == 'delete':
            delete_question(db, question_id)
            flash('Question deleted.', 'success')
            return redirect(url_for('gi_history_ai_training'))
        opts = [o.strip() for o in (request.form.get('answer_options') or '').split(',') if o.strip()]
        cond_raw = (request.form.get('conditional_rules_json') or '').strip()
        cond = json.loads(cond_raw) if cond_raw else {}
        update_question(
            db, question_id,
            question_text=(request.form.get('question_text') or '').strip(),
            category=(request.form.get('category') or '').strip(),
            question_type=(request.form.get('question_type') or '').strip(),
            answer_options=opts,
            is_required=bool(request.form.get('is_required')),
            priority=request.form.get('priority', type=int) or 100,
            conditional_rules=cond,
            clinical_purpose=(request.form.get('clinical_purpose') or '').strip(),
        )
        flash('Question updated.', 'success')
        return redirect(url_for('gi_history_ai_training', q=question_id))

    @app.route('/admin/history-ai-training/rule', methods=['POST'])
    @login_required
    @roles_required(*TRAINING_ROLES)
    def gi_history_ai_training_add_rule():
        if _block_write_if_frozen():
            code = (request.form.get('complaint_code') or '').strip()
            return redirect(url_for('gi_history_ai_training', complaint=code))
        db = get_db()
        code = (request.form.get('complaint_code') or '').strip()
        qid = (request.form.get('question_id') or '').strip()
        act_raw = (request.form.get('activation_rules_json') or '').strip()
        act = json.loads(act_raw) if act_raw else {}
        add_complaint_rule(
            db, complaint_code=code, question_id=qid,
            sort_order=request.form.get('sort_order', type=int) or 100,
            activation_rules=act,
        )
        flash('Rule linked.', 'success')
        return redirect(url_for('gi_history_ai_training', complaint=code))

    @app.route('/admin/history-ai-training/rule/<int:rule_id>/delete', methods=['POST'])
    @login_required
    @roles_required(*TRAINING_ROLES)
    def gi_history_ai_training_delete_rule(rule_id):
        if _block_write_if_frozen():
            code = (request.form.get('complaint_code') or '').strip()
            return redirect(url_for('gi_history_ai_training', complaint=code))
        db = get_db()
        code = (request.form.get('complaint_code') or '').strip()
        delete_rule(db, rule_id)
        flash('Rule removed.', 'success')
        return redirect(url_for('gi_history_ai_training', complaint=code))
