"""History Templates admin — configurable History Designer (legacy, write-frozen)."""

from flask import flash, redirect, render_template, request, session, url_for

from gi_platform import history_template_service
from gi_platform.legacy_history_freeze import (
    FREEZE_MESSAGE,
    legacy_history_writes_frozen,
)

TEMPLATE_ROLES = ('admin', 'hod', 'consultant', 'specialist')


def _block_write_if_frozen():
    if legacy_history_writes_frozen():
        flash(FREEZE_MESSAGE, 'error')
        return True
    return False


def register_history_template_routes(app, *, get_db, login_required, roles_required):
    @app.route('/admin/history-templates')
    @login_required
    @roles_required(*TEMPLATE_ROLES)
    def gi_history_templates():
        db = get_db()
        templates = history_template_service.list_templates(db, q=(request.args.get('q') or ''))
        return render_template(
            'gi/history_templates.html',
            templates=templates,
            writes_frozen=legacy_history_writes_frozen(),
        )

    @app.route('/admin/history-templates/new', methods=['GET', 'POST'])
    @login_required
    @roles_required(*TEMPLATE_ROLES)
    def gi_history_template_new():
        if request.method == 'POST':
            if _block_write_if_frozen():
                return redirect(url_for('gi_history_templates'))
            db = get_db()
            tid = history_template_service.create_template(
                db,
                disease_code=(request.form.get('disease_code') or '').strip(),
                disease_name=(request.form.get('disease_name') or '').strip(),
                created_by=session.get('user_id'),
            )
            flash('Template created.', 'success')
            return redirect(url_for('gi_history_template_edit', template_id=tid))
        return render_template(
            'gi/history_template_edit.html',
            template=None,
            questions=[],
            writes_frozen=legacy_history_writes_frozen(),
        )

    @app.route('/admin/history-templates/<int:template_id>', methods=['GET', 'POST'])
    @login_required
    @roles_required(*TEMPLATE_ROLES)
    def gi_history_template_edit(template_id):
        db = get_db()
        template = history_template_service.get_template(db, template_id)
        if not template:
            flash('Template not found.', 'error')
            return redirect(url_for('gi_history_templates'))

        if request.method == 'POST':
            if _block_write_if_frozen():
                return redirect(url_for('gi_history_template_edit', template_id=template_id))
            action = (request.form.get('action') or 'save').strip()
            if action == 'save':
                history_template_service.update_template(
                    db, template_id,
                    disease_code=(request.form.get('disease_code') or '').strip(),
                    disease_name=(request.form.get('disease_name') or '').strip(),
                    symptoms=[s.strip() for s in (request.form.get('symptoms') or '').split('\n') if s.strip()],
                    red_flags=[s.strip() for s in (request.form.get('red_flags') or '').split('\n') if s.strip()],
                    risk_factors=[s.strip() for s in (request.form.get('risk_factors') or '').split('\n') if s.strip()],
                    positive_findings=[s.strip() for s in (request.form.get('positive_findings') or '').split('\n') if s.strip()],
                    negative_findings=[s.strip() for s in (request.form.get('negative_findings') or '').split('\n') if s.strip()],
                    exclusions=[s.strip() for s in (request.form.get('exclusions') or '').split('\n') if s.strip()],
                )
                flash('Template saved.', 'success')
            elif action == 'add_question':
                history_template_service.add_question(
                    db, template_id=template_id,
                    question_key=(request.form.get('question_key') or '').strip(),
                    prompt=(request.form.get('prompt') or '').strip(),
                    answer_type=(request.form.get('answer_type') or 'text').strip(),
                    choices=[c.strip() for c in (request.form.get('choices') or '').split(',') if c.strip()],
                    sort_order=request.form.get('sort_order', type=int) or 0,
                    is_red_flag=bool(request.form.get('is_red_flag')),
                    is_exclusion=bool(request.form.get('is_exclusion')),
                )
                flash('Question added.', 'success')
            elif action == 'delete_question':
                qid = request.form.get('question_id', type=int)
                if qid:
                    history_template_service.delete_question(db, qid)
                    flash('Question removed.', 'success')
            return redirect(url_for('gi_history_template_edit', template_id=template_id))

        import json
        questions = history_template_service.list_questions(db, template_id)

        def _lines(field):
            try:
                return '\n'.join(json.loads(template[field] or '[]'))
            except Exception:
                return ''

        return render_template(
            'gi/history_template_edit.html',
            template=template,
            questions=questions,
            symptoms_text=_lines('symptoms_json'),
            red_flags_text=_lines('red_flags_json'),
            risk_factors_text=_lines('risk_factors_json'),
            positive_text=_lines('positive_findings_json'),
            negative_text=_lines('negative_findings_json'),
            exclusions_text=_lines('exclusions_json'),
            writes_frozen=legacy_history_writes_frozen(),
        )

    @app.route('/admin/history-templates/<int:template_id>/delete', methods=['POST'])
    @login_required
    @roles_required('admin', 'hod')
    def gi_history_template_delete(template_id):
        if _block_write_if_frozen():
            return redirect(url_for('gi_history_templates'))
        history_template_service.delete_template(get_db(), template_id)
        flash('Template deleted.', 'success')
        return redirect(url_for('gi_history_templates'))
