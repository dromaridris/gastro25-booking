"""Clinical history, CDS, medications routes."""

import json

from flask import flash, redirect, render_template, request, session, url_for

from gi_platform import cds_service, history_service, workforce_service
from gi_platform.catalogue_runtime import (
    build_narrative, compute_differential_for_session, get_next_questions,
    get_next_questions_for_session, session_interview_complete, list_complaints,
)
from gi_platform import symptom_service
from gi_platform.cds_service import AssessmentContext
from gi_platform.investigation_catalog import ORDER_TYPES
from gi_platform.narrative_engine import (
    generate_history_note, sections_to_history_text, SECTION_LABELS,
)

CLINICAL_ROLES = (
    'admin', 'hod', 'consultant', 'specialist', 'registrar', 'general_endoscopy',
    'house_officer', 'pg_trainee', 'nurse_manager', 'staff_nurse',
)


def _patient_back_url(sess) -> str:
    if sess and sess['ward_patient_id']:
        return url_for('ward_patient_view', ward_patient_id=sess['ward_patient_id'])
    return url_for('ward_dashboard')


def _run_cds(db, sess, session_id, *, persist: bool = False):
    if not sess['complaint_code']:
        return None
    ctx = AssessmentContext(
        chief_complaint=sess['chief_complaint'] or '',
        complaint_code=sess['complaint_code'] or '',
        session_id=session_id,
        ward_patient_id=sess['ward_patient_id'],
    )
    result = cds_service.assess(db, ctx)
    if persist:
        cds_service.persist_assessment(db, ctx, result, created_by=session.get('user_id'))
    return result


def _workflow_or_session_url(sess, session_id) -> str:
    if sess and sess['ward_patient_id']:
        return url_for('gi_clinical_workflow', ward_patient_id=sess['ward_patient_id'])
    return url_for('gi_clinical_session', session_id=session_id)


def _session_redirect(sess, session_id, anchor: str = ''):
    if sess and sess['ward_patient_id']:
        target = url_for('gi_clinical_workflow', ward_patient_id=sess['ward_patient_id'])
        return redirect(target + anchor)
    return redirect(url_for('gi_clinical_session', session_id=session_id))


def _log_clinical(db, sess, session_id, *, activity_type, title, source_type, source_id=None, details=None):
    """Log department logbook + patient journey."""
    from gi_platform import logbook_service, patient_journey_service
    uid = session.get('user_id')
    wp = sess['ward_patient_id'] if sess else None
    logbook_service.log_activity(
        db, user_id=uid, activity_type=activity_type, title=title,
        ward_patient_id=wp, session_id=session_id,
        source_module='clinical', source_type=source_type, source_id=source_id,
        details=details,
    )
    if wp:
        patient_journey_service.add_event(
            db, event_type=activity_type, title=title,
            ward_patient_id=wp,
            created_by=uid, source_module='clinical', source_id=source_id,
            details=details,
        )


def _ensure_suggestions(db, session_id, complaint_code):
    """Idempotent CDS investigation suggestions for a session."""
    existing = db.execute(
        "SELECT name FROM gi_investigation_suggestion WHERE session_id = ?", (session_id,)
    ).fetchall()
    if existing:
        return
    diff = compute_differential_for_session(db, complaint_code, session_id)
    for inv in diff.investigations:
        db.execute(
            """
            INSERT INTO gi_investigation_suggestion (session_id, name, rationale, priority)
            VALUES (?, ?, ?, ?)
            """,
            (session_id, inv['name'], inv.get('rationale', ''), inv.get('priority', 'routine')),
        )
    db.commit()


def register_clinical_routes(app, *, get_db, login_required, roles_required):
    @app.route('/clinical-history/patient/<int:ward_patient_id>')
    @login_required
    @roles_required(*CLINICAL_ROLES)
    def gi_clinical_patient(ward_patient_id):
        db = get_db()
        sessions = history_service.list_sessions_for_patient(db, ward_patient_id)
        complaints = list_complaints(db)
        return render_template(
            'gi/clinical_patient.html',
            ward_patient_id=ward_patient_id, sessions=sessions, complaints=complaints,
            back_url=url_for('ward_patient_view', ward_patient_id=ward_patient_id),
        )

    @app.route('/clinical-history/patient/<int:ward_patient_id>/session', methods=['POST'])
    @login_required
    @roles_required(*CLINICAL_ROLES)
    def gi_clinical_new_session(ward_patient_id):
        db = get_db()
        complaint_code = (request.form.get('complaint_code') or '').strip()
        selected = [c for c in list_complaints(db) if c['code'] == complaint_code]
        complaint_name = selected[0]['name'] if selected else complaint_code
        sid = history_service.create_session(
            db, ward_patient_id=ward_patient_id,
            chief_complaint=complaint_name,
            complaint_code=complaint_code,
            mrn=(request.form.get('mrn') or '').strip(),
            created_by=session.get('user_id'),
        )
        flash('History session started.', 'success')
        return redirect(url_for('gi_clinical_workflow', ward_patient_id=ward_patient_id))

    @app.route('/ward/patient/<int:ward_patient_id>/clinical', methods=['GET', 'POST'])
    @login_required
    @roles_required(*CLINICAL_ROLES)
    def gi_clinical_workflow(ward_patient_id):
        """Unified inpatient clinical page: history → exam → investigations → summary → plan."""
        db = get_db()
        from gi_platform import patient_identity_service
        wp = db.execute('SELECT * FROM ward_patient WHERE id = ?', (ward_patient_id,)).fetchone()
        if not wp:
            flash('Patient not found.', 'error')
            return redirect(url_for('ward_dashboard'))

        sid = patient_identity_service.get_latest_history_session(db, ward_patient_id)
        if not sid:
            sid = history_service.create_session(
                db, ward_patient_id=ward_patient_id, mrn=wp['mrn'] or '',
                created_by=session.get('user_id'),
            )
            patient_identity_service.sync_ward_patient_mrn(db, ward_patient_id)

        sess = history_service.get_session(db, sid)
        session_id = sid

        if request.method == 'POST':
            action = request.form.get('action')
            # Unified encounter staged workflow actions
            if action and action.startswith('ue_'):
                from gi_platform import unified_encounter as ue
                ue_action = action[3:]  # strip ue_
                state, msg = ue.handle_action(db, session_id, ue_action, request.form)
                if msg:
                    low = msg.lower()
                    err = any(t in low for t in ('required', 'select at least', 'choose an', 'not found'))
                    flash(msg, 'error' if err else 'success')
                stage = (state or {}).get('stage') or 'mode_select'
                anchor = {
                    'mode_select': '#encounter',
                    'complaints': '#history',
                    'known_diseases': '#history',
                    'current_problem': '#history',
                    'characterization': '#history',
                    'initial_reasoning': '#history',
                    'discriminating': '#history',
                    'history_summary': '#summary',
                    'examination': '#examination',
                    'investigations': '#investigations',
                    'plan': '#plan',
                }.get(stage, '#history')
                return redirect(url_for('gi_clinical_workflow', ward_patient_id=ward_patient_id) + anchor)

            if action == 'submit_plan':
                plan_text = (request.form.get('plan_text') or '').strip()
                final_dx = (sess['final_diagnosis'] if 'final_diagnosis' in sess.keys() else '') or ''
                if plan_text and not final_dx.strip():
                    flash('Save final diagnosis in Summary section before submitting plan.', 'error')
                    return redirect(url_for('gi_clinical_workflow', ward_patient_id=ward_patient_id) + '#plan')
                if plan_text:
                    db.execute(
                        """
                        INSERT INTO gi_management_plan
                        (session_id, ward_patient_id, plan_text, created_by, approval_status)
                        VALUES (?, ?, ?, ?, 'pending_registrar')
                        """,
                        (session_id, ward_patient_id, plan_text, session.get('user_id')),
                    )
                    db.commit()
                    workforce_service.create_task(
                        db, ward_patient_id=ward_patient_id, task_type='registry',
                        title='Approve management plan',
                        assigned_role='registrar',
                        notes=f'Session #{session_id}',
                        created_by=session.get('user_id'),
                    )
                    from gi_platform import audit_service
                    audit_service.log_event(
                        db, action='plan_submitted', entity_type='gi_management_plan',
                        entity_id=db.execute('SELECT last_insert_rowid() AS id').fetchone()['id'],
                        user_id=session.get('user_id'),
                    )
                    _log_clinical(db, sess, session_id, activity_type='management_plan',
                                  title='Management plan submitted', source_type='plan')
                    flash('Management plan submitted for registrar approval.', 'success')
                return redirect(url_for('gi_clinical_workflow', ward_patient_id=ward_patient_id) + '#plan')

            if action == 'save_summary':
                sections = {}
                for key in request.form:
                    if key.startswith('section_'):
                        sections[key.replace('section_', '')] = request.form.get(key, '').strip()
                final_dx = (request.form.get('final_diagnosis') or '').strip()
                db.execute(
                    'UPDATE gi_history_session SET final_diagnosis = ?, updated_at = datetime("now") WHERE id = ?',
                    (final_dx, session_id),
                )
                patient_name, mrn = wp['patient_name'], wp['mrn'] or ''
                from gi_platform.narrative_engine import sections_to_history_text
                full_text = sections_to_history_text(sections, patient_name=patient_name, mrn=mrn)
                if final_dx:
                    sections['final_diagnosis'] = final_dx
                    full_text += f"\n\nFinal diagnosis: {final_dx}"
                history_service.save_narrative(db, session_id, full_text, sections)
                flash('History summary saved.', 'success')
                return redirect(url_for('gi_clinical_workflow', ward_patient_id=ward_patient_id) + '#summary')

            if action == 'save_diagnosis':
                final_dx = (request.form.get('final_diagnosis') or '').strip()
                db.execute(
                    'UPDATE gi_history_session SET final_diagnosis = ?, updated_at = datetime("now") WHERE id = ?',
                    (final_dx, session_id),
                )
                db.commit()
                flash('Final diagnosis saved.', 'success')
                return redirect(url_for('gi_clinical_workflow', ward_patient_id=ward_patient_id) + '#summary')

        questions, differential, complete = [], None, False
        symptoms = []
        from gi_platform.complaints_extra_seed import seed_extra_complaints_if_missing, seed_symptom_training_questions
        from gi_platform.catalogue_runtime import ensure_structured_common_questions
        seed_extra_complaints_if_missing(db)
        seed_symptom_training_questions(db)
        ensure_structured_common_questions(db)
        symptom_service.sync_legacy_complaint(db, session_id)
        symptoms = symptom_service.list_session_symptoms(db, session_id)
        if sess['complaint_code'] or symptoms:
            questions, complete = get_next_questions_for_session(db, session_id, batch_size=5)
            differential = symptom_service.compute_combined_differential(db, session_id)
            if sess['complaint_code']:
                _ensure_suggestions(db, session_id, sess['complaint_code'])

        answers = history_service.list_answers(db, session_id)
        narrative = history_service.get_narrative(db, session_id)
        narrative_sections = json.loads(narrative['sections_json']) if narrative and narrative['sections_json'] else {}
        exam_text = (sess['examination_text'] if 'examination_text' in sess.keys() else '') or ''
        suggestions = db.execute(
            "SELECT * FROM gi_investigation_suggestion WHERE session_id = ? ORDER BY id",
            (session_id,),
        ).fetchall()
        orders = db.execute(
            "SELECT * FROM gi_investigation_order WHERE session_id = ? ORDER BY id DESC",
            (session_id,),
        ).fetchall()
        plans = db.execute(
            "SELECT * FROM gi_management_plan WHERE session_id = ? ORDER BY id DESC",
            (session_id,),
        ).fetchall()
        from gi_platform import lab_propagation
        lab_results = lab_propagation.list_labs_for_patient(db, ward_patient_id=ward_patient_id, limit=30)
        cds_result = _run_cds(db, sess, session_id, persist=False) if sess['complaint_code'] else None
        user_row = db.execute('SELECT role FROM user WHERE id = ?', (session.get('user_id'),)).fetchone()
        role = user_row['role'] if user_row else ''

        final_diagnosis = (sess['final_diagnosis'] if 'final_diagnosis' in sess.keys() else '') or ''
        symptom_map = {s['complaint_code']: s for s in symptoms}

        from gi_platform import unified_encounter as ue
        ue_view = ue.build_workflow_view(db, session_id)
        # Prefer enriched differential from unified encounter (never empty after characterization)
        if ue_view.get('ue_differential') and (ue_view['ue_differential'].get('diagnoses') or []):
            differential = ue_view['ue_differential']

        return render_template(
            'gi/clinical_workflow.html',
            patient=wp, sess=sess, session_id=session_id,
            questions=questions, answers=answers, complaints=list_complaints(db),
            symptoms=symptoms, symptom_map=symptom_map, interview_complete=complete, examination_text=exam_text,
            narrative=narrative, narrative_sections=narrative_sections,
            section_labels=SECTION_LABELS, differential=differential,
            cds_result=cds_result, suggestions=suggestions, orders=orders,
            order_types=ORDER_TYPES, plans=plans, role=role,
            final_diagnosis=final_diagnosis,
            lab_results=lab_results,
            back_url=url_for('ward_patient_view', ward_patient_id=ward_patient_id),
            **ue_view,
        )

    @app.route('/clinical-history/session/<int:session_id>')
    @login_required
    @roles_required(*CLINICAL_ROLES)
    def gi_clinical_session(session_id):
        db = get_db()
        sess = history_service.get_session(db, session_id)
        if not sess:
            flash('Session not found.', 'error')
            return redirect(url_for('ward_dashboard'))
        questions = []
        differential = None
        complete = False
        if sess['complaint_code']:
            questions = get_next_questions(db, sess['complaint_code'], session_id)
            differential = compute_differential_for_session(db, sess['complaint_code'], session_id)
            complete = interview_complete(db, sess['complaint_code'], session_id)
        answers = history_service.list_answers(db, session_id)
        narrative = history_service.get_narrative(db, session_id)
        narrative_sections = {}
        if narrative and narrative['sections_json']:
            import json
            narrative_sections = json.loads(narrative['sections_json'])
        meds = history_service.list_medications(db, session_id=session_id)
        complaints = list_complaints(db)
        exam_text = (sess['examination_text'] if 'examination_text' in sess.keys() else '') or ''
        return render_template(
            'gi/clinical_session.html',
            sess=sess, questions=questions, answers=answers, narrative=narrative,
            narrative_sections=narrative_sections, section_labels=SECTION_LABELS,
            medications=meds, differential=differential, complaints=complaints,
            interview_complete=complete, examination_text=exam_text,
            back_url=_patient_back_url(sess),
        )

    @app.route('/clinical-history/session/<int:session_id>/answer', methods=['POST'])
    @login_required
    @roles_required(*CLINICAL_ROLES)
    def gi_clinical_save_answer(session_id):
        db = get_db()
        sess = history_service.get_session(db, session_id)
        symptom_id = request.form.get('symptom_id', type=int)
        history_service.save_answer(
            db, session_id,
            question_key=(request.form.get('question_key') or '').strip(),
            answer_text=(request.form.get('answer_text') or '').strip(),
            symptom_id=symptom_id,
        )
        flash('Answer saved.', 'success')
        _log_clinical(db, sess, session_id, activity_type='history_taking',
                      title='History answer recorded', source_type='answer')
        return _session_redirect(sess, session_id, '#history')

    @app.route('/clinical-history/session/<int:session_id>/symptoms', methods=['POST'])
    @login_required
    @roles_required(*CLINICAL_ROLES)
    def gi_clinical_set_symptoms(session_id):
        db = get_db()
        sess = history_service.get_session(db, session_id)
        codes = request.form.getlist('complaint_codes')
        primary = request.form.get('primary_complaint')
        items = []
        for idx, code in enumerate(codes):
            code = (code or '').strip()
            if not code:
                continue
            onset = (request.form.get(f'onset_{code}') or '').strip()
            items.append({
                'complaint_code': code,
                'onset_text': onset,
                'is_primary': code == primary or (not primary and idx == 0),
            })
        if not items:
            flash('Select at least one symptom.', 'error')
            return _session_redirect(sess, session_id, '#history')
        symptom_service.set_session_symptoms(db, session_id, symptoms=items)
        flash(f'History started for {len(items)} symptom(s).', 'success')
        return _session_redirect(sess, session_id, '#history')

    @app.route('/clinical-history/session/<int:session_id>/complaint', methods=['POST'])
    @login_required
    @roles_required(*CLINICAL_ROLES)
    def gi_clinical_set_complaint(session_id):
        db = get_db()
        sess = history_service.get_session(db, session_id)
        code = (request.form.get('complaint_code') or '').strip()
        selected = [c for c in list_complaints(db) if c['code'] == code]
        onset = (request.form.get('onset_text') or '').strip()
        symptom_service.set_session_symptoms(db, session_id, symptoms=[{
            'complaint_code': code,
            'onset_text': onset,
            'is_primary': True,
        }])
        if selected:
            history_service.set_complaint(db, session_id, code, selected[0]['name'])
        return _session_redirect(sess, session_id, '#history')

    @app.route('/clinical-history/session/<int:session_id>/examination', methods=['POST'])
    @login_required
    @roles_required(*CLINICAL_ROLES)
    def gi_clinical_save_examination(session_id):
        db = get_db()
        sess = history_service.get_session(db, session_id)
        history_service.save_examination(
            db, session_id, (request.form.get('examination_text') or '').strip(),
        )
        flash('Examination notes saved.', 'success')
        _log_clinical(db, sess, session_id, activity_type='examination',
                      title='Physical examination documented', source_type='examination')
        return _session_redirect(sess, session_id, '#examination')

    @app.route('/clinical-history/session/<int:session_id>/generate-note', methods=['POST'])
    @login_required
    @roles_required(*CLINICAL_ROLES)
    def gi_clinical_generate_note(session_id):
        db = get_db()
        sess = history_service.get_session(db, session_id)
        if not sess:
            flash('Session not found.', 'error')
            return redirect(url_for('ward_dashboard'))

        exam = (sess['examination_text'] if 'examination_text' in sess.keys() else '') or ''
        sections = generate_history_note(db, session_id, examination_text=exam)
        patient_name, mrn = '', sess['mrn'] or ''
        if sess['ward_patient_id']:
            wp = db.execute(
                'SELECT patient_name, mrn FROM ward_patient WHERE id = ?', (sess['ward_patient_id'],)
            ).fetchone()
            if wp:
                patient_name, mrn = wp['patient_name'], mrn or wp['mrn'] or ''
        full_text = sections_to_history_text(sections, patient_name=patient_name, mrn=mrn)
        history_service.save_narrative(db, session_id, full_text, sections)
        if sess['ward_patient_id']:
            from gi_platform import patient_identity_service, audit_service
            patient_identity_service.sync_ward_patient_mrn(db, sess['ward_patient_id'])
            audit_service.log_event(
                db, action='history_generated', entity_type='gi_history_session',
                entity_id=session_id, user_id=session.get('user_id'),
            )
        flash('History narrative generated and saved.', 'success')
        _log_clinical(db, sess, session_id, activity_type='history_generated',
                      title='Clinical summary generated', source_type='narrative')
        return _session_redirect(sess, session_id, '#summary')

    @app.route('/clinical-history/session/<int:session_id>/print')
    @login_required
    @roles_required(*CLINICAL_ROLES)
    def gi_clinical_print(session_id):
        db = get_db()
        sess = history_service.get_session(db, session_id)
        if not sess:
            flash('Session not found.', 'error')
            return redirect(url_for('ward_dashboard'))
        narrative = history_service.get_narrative(db, session_id)
        sections = {}
        if narrative and narrative['sections_json']:
            import json
            sections = json.loads(narrative['sections_json'])
        patient_name, mrn = '', sess['mrn'] or ''
        if sess['ward_patient_id']:
            wp = db.execute(
                'SELECT patient_name, mrn FROM ward_patient WHERE id = ?', (sess['ward_patient_id'],)
            ).fetchone()
            if wp:
                patient_name, mrn = wp['patient_name'], mrn or wp['mrn'] or ''
        return render_template(
            'gi/history_print.html',
            sess=sess, narrative=narrative, sections=sections,
            section_labels=SECTION_LABELS, patient_name=patient_name, mrn=mrn,
            back_url=_workflow_or_session_url(sess, session_id),
        )

    @app.route('/clinical-history/session/<int:session_id>/cds')
    @login_required
    @roles_required(*CLINICAL_ROLES)
    def gi_clinical_cds(session_id):
        db = get_db()
        sess = history_service.get_session(db, session_id)
        if not sess:
            flash('Session not found.', 'error')
            return redirect(url_for('ward_dashboard'))
        result = _run_cds(db, sess, session_id, persist=False) if sess['complaint_code'] else None
        return render_template(
            'gi/cds.html', sess=sess, result=result,
            back_url=_workflow_or_session_url(sess, session_id),
        )

    @app.route('/clinical-history/session/<int:session_id>/medications', methods=['POST'])
    @login_required
    @roles_required(*CLINICAL_ROLES)
    def gi_clinical_add_medication(session_id):
        db = get_db()
        sess = history_service.get_session(db, session_id)
        history_service.add_medication(
            db, session_id=session_id,
            drug_name=(request.form.get('drug_name') or '').strip(),
            dose=(request.form.get('dose') or '').strip(),
            frequency=(request.form.get('frequency') or '').strip(),
        )
        flash('Medication added.', 'success')
        return _session_redirect(sess, session_id, '#history')

    @app.route('/clinical-history/investigations/<int:session_id>', methods=['GET', 'POST'])
    @login_required
    @roles_required(*CLINICAL_ROLES)
    def gi_investigations(session_id):
        db = get_db()
        sess = history_service.get_session(db, session_id)
        if not sess:
            flash('Session not found.', 'error')
            return redirect(url_for('ward_dashboard'))

        if request.method == 'POST':
            order_type = (request.form.get('order_type') or 'lab').strip()
            item_code = (request.form.get('item_code') or '').strip()
            custom = (request.form.get('custom_item') or '').strip()
            item_name = custom
            if not item_name and item_code:
                for _t, _label, items in ORDER_TYPES:
                    for code, name in items:
                        if code == item_code:
                            item_name = name
                            break
            if not item_name:
                flash('Choose an investigation from the list or type a custom order.', 'error')
                return _session_redirect(sess, session_id, '#investigations')
            from gi_platform import order_service
            approval = order_service.initial_approval_status(order_type)
            db.execute(
                """
                INSERT INTO gi_investigation_order
                (session_id, ward_patient_id, order_type, item_code, item_name, custom_note,
                 created_by, approval_status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (session_id, sess['ward_patient_id'], order_type, item_code or 'custom',
                 item_name, custom if custom else None, session.get('user_id'), approval),
            )
            order_id = db.execute('SELECT last_insert_rowid() AS id').fetchone()['id']
            db.commit()
            if approval == 'pending_registrar' and sess['ward_patient_id']:
                workforce_service.create_task(
                    db, ward_patient_id=sess['ward_patient_id'],
                    task_type='registry',
                    title=f"Approve order: {item_name}",
                    assigned_role='registrar',
                    notes=f"Session #{session_id} — registrar approval required.",
                    created_by=session.get('user_id'),
                )
                if order_type == 'endoscopy':
                    pass  # HO task after registrar approves + schedules
                elif order_type == 'imaging':
                    workforce_service.create_task(
                        db, ward_patient_id=sess['ward_patient_id'],
                        task_type='investigations',
                        title=f"Arrange imaging: {item_name}",
                        assigned_role='house_officer',
                        notes=f"After registrar approval — session #{session_id}.",
                        created_by=session.get('user_id'),
                    )
            elif approval == 'approved' and order_type == 'lab' and sess['ward_patient_id']:
                workforce_service.create_task(
                    db, ward_patient_id=sess['ward_patient_id'],
                    task_type='labs',
                    title=f"Arrange: {item_name}",
                    assigned_role='house_officer',
                    notes=f"Lab order auto-approved — session #{session_id}.",
                    created_by=session.get('user_id'),
                )
            from gi_platform import audit_service
            audit_service.log_event(
                db, action='order_created', entity_type='gi_investigation_order',
                entity_id=order_id, user_id=session.get('user_id'), details={'item': item_name},
            )
            _log_clinical(db, sess, session_id, activity_type='investigation_order',
                          title=f'Ordered: {item_name}', source_type='order', source_id=order_id)
            flash(
                f'Order submitted{" for registrar approval" if approval == "pending_registrar" else ""}: {item_name}',
                'success',
            )
            return _session_redirect(sess, session_id, '#investigations')

        if sess['complaint_code']:
            _ensure_suggestions(db, session_id, sess['complaint_code'])
        suggestions = db.execute(
            "SELECT * FROM gi_investigation_suggestion WHERE session_id = ? ORDER BY id DESC",
            (session_id,),
        ).fetchall()

        orders = db.execute(
            "SELECT * FROM gi_investigation_order WHERE session_id = ? ORDER BY id DESC",
            (session_id,),
        ).fetchall()
        return render_template(
            'gi/investigations.html',
            sess=sess, suggestions=suggestions, orders=orders,
            order_types=ORDER_TYPES,
            back_url=_workflow_or_session_url(sess, session_id),
        )

    @app.route('/clinical-history/scores/<int:session_id>', methods=['GET', 'POST'])
    @login_required
    @roles_required(*CLINICAL_ROLES)
    def gi_scores(session_id):
        db = get_db()
        sess = history_service.get_session(db, session_id)
        if not sess:
            flash('Session not found.', 'error')
            return redirect(url_for('ward_dashboard'))
        if request.method == 'POST':
            from gi_platform import score_service
            if (request.form.get('action') or '') == 'recalculate':
                score_service.auto_calculate_and_store(
                    db, session_id=session_id, ward_patient_id=sess['ward_patient_id'],
                )
                flash('Clinical scores recalculated from labs and history.', 'success')
            else:
                score_name = (request.form.get('score_name') or 'Rockall').strip()
                age = request.form.get('age', type=int) or 0
                shock = request.form.get('shock') or 'none'
                comorbidity = request.form.get('comorbidity') or 'none'
                diagnosis = request.form.get('diagnosis') or 'none'
                stigmata = request.form.get('stigmata') or 'none'
                value = age + {'none': 0, 'hr100': 1, 'sbp100': 2, 'both': 3}.get(shock, 0)
                value += {'none': 0, 'heart_failure': 2, 'ischaemic_heart': 2, 'other': 3}.get(comorbidity, 0)
                value += {'mallory_weiss': 0, 'other': 1, 'malignancy': 2}.get(diagnosis, 0)
                value += {'none': 0, 'dark_spot': 2, 'blood': 2, 'adherent_clot': 2, 'spurting': 3}.get(stigmata, 0)
                if value <= 2:
                    interp = 'Low risk — early discharge may be appropriate.'
                elif value <= 4:
                    interp = 'Intermediate risk — ward observation and early endoscopy.'
                else:
                    interp = 'High risk — close monitoring, resuscitation, urgent endoscopy.'
                db.execute(
                    """
                    INSERT INTO gi_clinical_score_result
                    (session_id, ward_patient_id, score_code, score_name, score_value, interpretation, inputs_json, auto_calculated)
                    VALUES (?, ?, 'rockall_post', ?, ?, ?, ?, 0)
                    """,
                    (session_id, sess['ward_patient_id'], score_name, value, interp, json.dumps({
                        'age': age, 'shock': shock, 'comorbidity': comorbidity,
                        'diagnosis': diagnosis, 'stigmata': stigmata,
                    })),
                )
                db.commit()
                flash(f'{score_name} score: {value} — {interp}', 'success')
            return _session_redirect(sess, session_id, '#history')
        from gi_platform import score_service
        from gi_platform.score_registry import SCORE_GROUPS, SCORE_REGISTRY
        rows = score_service.scores_for_patient(db, session_id=session_id)
        suggested = score_service.discover_scores_from_knowledge(
            db, score_service.build_patient_context(
                db, ward_patient_id=sess['ward_patient_id'], session_id=session_id,
                complaint_code=sess['complaint_code'] or '',
            ),
        )
        live = score_service.calculate_scores(
            db, session_id=session_id, ward_patient_id=sess['ward_patient_id'],
        )
        score_objects = db.execute(
            "SELECT title, summary, slug FROM gi_knowledge_object WHERE object_type = 'score' AND status = 'published'"
        ).fetchall()
        return render_template(
            'gi/scores.html', sess=sess, scores=rows, score_catalog=score_objects,
            score_groups=SCORE_GROUPS, score_registry=SCORE_REGISTRY,
            suggested_scores=suggested, live_scores=live,
            back_url=_workflow_or_session_url(sess, session_id),
        )

    @app.route('/data-exchange')
    @login_required
    @roles_required('admin')
    def gi_import_manager():
        from gi_platform import import_service, nav_permissions as navperm
        jobs = import_service.list_jobs(get_db())
        enriched = []
        for j in jobs:
            summary = import_service.parse_summary(j)
            enriched.append({
                'job': j,
                'summary': summary,
                'has_file': import_service.job_has_download(j),
            })
        return render_template(
            'gi/import_manager.html', jobs=enriched, back_url=url_for('ward_dashboard'),
            module_intro=navperm.intro('import_manager'),
            status_labels=import_service.JOB_STATUS_LABELS,
        )

    @app.route('/data-exchange/job', methods=['POST'])
    @login_required
    @roles_required('admin')
    def gi_import_create_job():
        from gi_platform import import_service
        db = get_db()
        job_type = (request.form.get('job_type') or 'knowledge_import').strip()
        filename = (request.form.get('filename') or '').strip()
        stored_path = ''
        if request.files.get('upload_file') and request.files['upload_file'].filename:
            stored_path, filename = import_service.save_upload(request.files['upload_file'])
        elif job_type == 'knowledge_import' and not filename:
            flash('Please upload a PDF file or enter a filename reference.', 'error')
            return redirect(url_for('gi_import_manager'))
        job_id, summary = import_service.create_job(
            db, job_type=job_type, filename=filename,
            created_by=session.get('user_id'), stored_path=stored_path,
        )
        if summary.get('object_id'):
            flash(summary.get('message') or summary.get('message_en', f'Import job #{job_id} done.'), 'success')
        elif summary.get('message') or summary.get('message_en'):
            flash(summary.get('message') or summary['message_en'], 'success')
        else:
            flash(f'Import job #{job_id} processed.', 'success')
        return redirect(url_for('gi_import_manager'))

    @app.route('/data-exchange/job/<int:job_id>/file')
    @login_required
    @roles_required('admin')
    def gi_import_download(job_id):
        from gi_platform import import_service
        from flask import send_file
        db = get_db()
        job = import_service.get_job(db, job_id)
        if not job:
            flash('Import job not found.', 'error')
            return redirect(url_for('gi_import_manager'))
        path = import_service.job_download_path(job)
        if not path:
            flash('No uploaded file is stored for this job.', 'error')
            return redirect(url_for('gi_import_manager'))
        return send_file(path, as_attachment=True, download_name=job['filename'] or 'import.pdf')

    def _require_full_access():
        from flask import session as flask_session
        from gi_platform.constants import has_full_access
        user = get_db().execute(
            'SELECT role FROM user WHERE id = ?', (flask_session.get('user_id'),)
        ).fetchone()
        return user and has_full_access(user['role'])

    @app.route('/login-promo/<int:image_id>')
    def gi_login_promo_image(image_id):
        from gi_platform import login_promo_service
        from flask import send_file
        row = login_promo_service.get_image(get_db(), image_id)
        if not row or not row['is_active']:
            return ('Not found', 404)
        path = login_promo_service.file_path(row)
        if not path:
            return ('Not found', 404)
        return send_file(path)

    @app.route('/admin/login-promo-file/<int:image_id>')
    @login_required
    def gi_login_promo_admin_file(image_id):
        from gi_platform import login_promo_service
        from flask import send_file
        if not _require_full_access():
            return ('Forbidden', 403)
        row = login_promo_service.get_image(get_db(), image_id)
        path = login_promo_service.file_path(row) if row else None
        if not path:
            return ('Not found', 404)
        return send_file(path)

    @app.route('/admin/login-promotions', methods=['GET', 'POST'])
    @login_required
    def gi_login_promotions():
        from gi_platform import login_promo_service, nav_permissions as navperm
        if not _require_full_access():
            flash('Login promotions can only be managed by Admin or Head of Department.', 'error')
            return redirect(url_for('dashboard'))
        db = get_db()
        from flask import session as flask_session
        if request.method == 'POST':
            action = (request.form.get('action') or 'upload').strip()
            if action == 'delete':
                image_id = request.form.get('image_id', type=int)
                if image_id and login_promo_service.delete_image(db, image_id):
                    flash('Promotional image removed.', 'success')
                else:
                    flash('Image not found.', 'error')
            elif action == 'toggle':
                image_id = request.form.get('image_id', type=int)
                active = request.form.get('active') == '1'
                if image_id:
                    login_promo_service.toggle_active(db, image_id, active)
                    flash('Image visibility updated.', 'success')
            else:
                file = request.files.get('image_file')
                if not file or not file.filename:
                    flash('Choose an image file to upload.', 'error')
                else:
                    try:
                        login_promo_service.save_upload(
                            db, file,
                            uploaded_by=flask_session.get('user_id'),
                            label=(request.form.get('label') or '').strip(),
                            link_url=(request.form.get('link_url') or '').strip(),
                        )
                        flash('Promotional image uploaded.', 'success')
                    except ValueError as exc:
                        flash(str(exc), 'error')
            return redirect(url_for('gi_login_promotions'))
        images = login_promo_service.list_all(db)
        active_count = sum(1 for i in images if i['is_active'])
        today_preview = login_promo_service.daily_display_images(db)
        return render_template(
            'gi/login_promotions.html',
            images=images,
            active_count=active_count,
            today_preview=today_preview,
            max_slots=login_promo_service.MAX_VISIBLE_SLOTS,
            module_intro=navperm.intro('login_promotions'),
        )
