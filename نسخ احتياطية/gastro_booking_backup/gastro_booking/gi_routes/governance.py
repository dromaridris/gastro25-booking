"""Clinical governance & registrar approval routes."""

from flask import flash, redirect, render_template, request, session, url_for

from gi_platform import audit_service, governance_clinical_service, governance_service, logbook_service
from gi_platform.constants import (
    AUDIT_STATUSES, CANMEDS_DOMAINS, CHECKLIST_TYPES, CLINICAL_STAFF_ROLES,
    DOCUMENT_TYPES, INCIDENT_CATEGORIES, INCIDENT_SEVERITIES, MM_STATUSES,
)

GOVERNANCE_ROLES = ('admin', 'hod', 'consultant', 'specialist')
MM_JC_ROLES = ('admin', 'hod', 'consultant', 'specialist', 'registrar')
REGISTRAR_APPROVE_ROLES = ('admin', 'hod', 'consultant', 'specialist', 'registrar')
STAFF_ROLES = tuple(CLINICAL_STAFF_ROLES)


def _acting_role(db):
    uid = session.get('user_id')
    if not uid:
        return None
    row = db.execute('SELECT role FROM user WHERE id = ?', (uid,)).fetchone()
    return row['role'] if row else None


def register_governance_routes(app, *, get_db, login_required, roles_required):
    @app.route('/governance')
    @login_required
    @roles_required(*GOVERNANCE_ROLES)
    def gi_governance_dashboard():
        db = get_db()
        data = governance_service.get_hod_dashboard(db)
        data['kpis'] = governance_clinical_service.quality_kpis(db)
        from gi_platform import nav_permissions as navperm
        data['module_intro'] = navperm.intro('governance')
        return render_template('gi/governance_dashboard.html', **data)

    @app.route('/governance/logbook')
    @login_required
    @roles_required(*GOVERNANCE_ROLES)
    def gi_governance_logbook():
        db = get_db()
        role_filter = request.args.get('role', '')
        entries = logbook_service.list_department_entries(
            db, role=role_filter or None, limit=500,
        )
        staff = db.execute(
            f"SELECT id, full_name, role FROM user WHERE role IN ({','.join('?'*len(CLINICAL_STAFF_ROLES))}) AND is_approved=1 ORDER BY full_name",
            tuple(CLINICAL_STAFF_ROLES),
        ).fetchall()
        from gi_platform import nav_permissions as navperm
        return render_template(
            'gi/governance_logbook.html', entries=entries, staff=staff,
            role_filter=role_filter, canmeds_domains=CANMEDS_DOMAINS,
            module_intro=navperm.intro('governance_logbook'),
        )

    @app.route('/governance/logbook/<int:entry_id>', methods=['GET', 'POST'])
    @login_required
    @roles_required(*GOVERNANCE_ROLES)
    def gi_logbook_evaluate(entry_id):
        db = get_db()
        entry = logbook_service.get_entry(db, entry_id)
        if not entry:
            flash('Entry not found.', 'error')
            return redirect(url_for('gi_governance_logbook'))
        if request.method == 'POST':
            logbook_service.add_evaluation(
                db, entry_id=entry_id, evaluator_id=session.get('user_id'),
                competency_domain=request.form.get('competency_domain', 'medical_expert'),
                score=request.form.get('score', type=int) or 3,
                note=(request.form.get('note') or '').strip(),
            )
            flash('CanMEDS evaluation saved.', 'success')
            return redirect(url_for('gi_logbook_evaluate', entry_id=entry_id))
        evaluations = logbook_service.list_evaluations(db, entry_id)
        summary = logbook_service.staff_summary(db, entry['user_id'])
        return render_template(
            'gi/logbook_evaluate.html', entry=entry, evaluations=evaluations,
            summary=summary, canmeds_domains=CANMEDS_DOMAINS,
        )

    @app.route('/governance/my-logbook')
    @login_required
    @roles_required(*STAFF_ROLES)
    def gi_my_logbook():
        db = get_db()
        grouped = logbook_service.list_entries_grouped_by_patient(db, session.get('user_id'))
        summary = logbook_service.staff_summary(db, session.get('user_id'))
        from gi_platform import nav_permissions as navperm
        return render_template(
            'gi/my_logbook.html', grouped=grouped, summary=summary,
            module_intro=navperm.intro('my_logbook'),
        )

    @app.route('/governance/staff/<int:user_id>')
    @login_required
    @roles_required(*GOVERNANCE_ROLES)
    def gi_staff_profile(user_id):
        db = get_db()
        user = db.execute('SELECT * FROM user WHERE id = ?', (user_id,)).fetchone()
        if not user:
            flash('User not found.', 'error')
            return redirect(url_for('gi_governance_logbook'))
        entries = logbook_service.list_entries_for_user(db, user_id, limit=100)
        summary = logbook_service.staff_summary(db, user_id)
        return render_template(
            'gi/staff_profile.html', user=user, entries=entries, summary=summary,
        )

    @app.route('/governance/incidents', methods=['GET', 'POST'])
    @login_required
    @roles_required(*GOVERNANCE_ROLES, 'registrar', 'nurse_manager')
    def gi_gov_incidents():
        db = get_db()
        if request.method == 'POST':
            governance_clinical_service.create_incident(
                db,
                incident_date=(request.form.get('incident_date') or '').strip(),
                category=request.form.get('category', 'other'),
                severity=request.form.get('severity', 'minor'),
                description=(request.form.get('description') or '').strip(),
                reported_by_id=session.get('user_id'),
                mrn=(request.form.get('mrn') or '').strip(),
                patient_name=(request.form.get('patient_name') or '').strip(),
            )
            flash('Incident reported.', 'success')
            return redirect(url_for('gi_gov_incidents'))
        incidents = governance_clinical_service.list_incidents(db)
        return render_template(
            'gi/gov_incidents.html', incidents=incidents,
            categories=INCIDENT_CATEGORIES, severities=INCIDENT_SEVERITIES,
            module_intro='Report and review patient safety incidents and near-misses.',
        )

    @app.route('/governance/incidents/<int:incident_id>/review', methods=['POST'])
    @login_required
    @roles_required(*GOVERNANCE_ROLES)
    def gi_gov_incident_review(incident_id):
        db = get_db()
        governance_clinical_service.review_incident(
            db, incident_id, reviewer_id=session.get('user_id'),
            root_cause=(request.form.get('root_cause') or '').strip(),
            corrective_action=(request.form.get('corrective_action') or '').strip(),
            preventive_action=(request.form.get('preventive_action') or '').strip(),
            status='closed',
        )
        flash('Incident reviewed.', 'success')
        return redirect(url_for('gi_gov_incidents'))

    @app.route('/governance/mm', methods=['GET', 'POST'])
    @login_required
    @roles_required(*MM_JC_ROLES)
    def gi_gov_mm():
        db = get_db()
        from gi_platform import nav_permissions as navperm
        if request.method == 'POST':
            role = _acting_role(db)
            if not navperm.can_assign_mm_presenters(db, session.get('user_id'), role):
                flash('You do not have permission to schedule M&M cases.', 'error')
                return redirect(url_for('gi_gov_mm'))
            case_id = governance_clinical_service.create_mm_case(
                db,
                case_summary=(request.form.get('case_summary') or '').strip(),
                presentation_date=(request.form.get('presentation_date') or '').strip(),
                mrn=(request.form.get('mrn') or '').strip(),
                patient_name=(request.form.get('patient_name') or '').strip(),
                presenter_id=session.get('user_id'),
                is_important=bool(request.form.get('is_important')),
                training_route=(request.form.get('training_route') or '').strip(),
                assigned_usernames=(request.form.get('assigned_usernames') or '').strip(),
                presenter_usernames=(request.form.get('presenter_usernames') or '').strip(),
                assigned_by_id=session.get('user_id'),
            )
            n = governance_clinical_service.training_assignment_count(db, 'mm', case_id)
            flash(
                f'M&M case created.'
                + (f' {n} presenter task(s) sent.' if n else ''),
                'success',
            )
            return redirect(url_for('gi_gov_mm'))
        cases = governance_clinical_service.list_mm_cases(db)
        role = _acting_role(db)
        return render_template(
            'gi/gov_mm.html', cases=cases, statuses=MM_STATUSES,
            can_assign_training=navperm.can_assign_mm_presenters(db, session.get('user_id'), role),
            module_intro=navperm.intro('mm'),
        )

    @app.route('/governance/journal-club', methods=['GET', 'POST'])
    @login_required
    @roles_required(*MM_JC_ROLES)
    def gi_gov_journal_club():
        db = get_db()
        from gi_platform import nav_permissions as navperm
        if request.method == 'POST':
            role = _acting_role(db)
            if not navperm.can_assign_mm_presenters(db, session.get('user_id'), role):
                flash('You do not have permission to schedule journal club sessions.', 'error')
                return redirect(url_for('gi_gov_journal_club'))
            session_id = governance_clinical_service.create_journal_club(
                db,
                title=(request.form.get('title') or '').strip(),
                session_date=(request.form.get('session_date') or '').strip(),
                article_reference=(request.form.get('article_reference') or '').strip(),
                assigned_usernames=(request.form.get('assigned_usernames') or '').strip(),
                presenter_usernames=(request.form.get('presenter_usernames') or '').strip(),
                training_route=(request.form.get('training_route') or '').strip(),
                is_important=bool(request.form.get('is_important')),
                notes=(request.form.get('notes') or '').strip(),
                created_by_id=session.get('user_id'),
            )
            n = governance_clinical_service.training_assignment_count(db, 'journal_club', session_id)
            flash(
                f'Journal club session scheduled.'
                + (f' {n} presenter task(s) sent.' if n else ''),
                'success',
            )
            return redirect(url_for('gi_gov_journal_club'))
        sessions = governance_clinical_service.list_journal_clubs(db)
        role = _acting_role(db)
        return render_template(
            'gi/gov_journal_club.html', sessions=sessions,
            can_assign_training=navperm.can_assign_mm_presenters(db, session.get('user_id'), role),
            module_intro=navperm.intro('journal_club'),
        )

    @app.route('/governance/audits', methods=['GET', 'POST'])
    @login_required
    @roles_required(*GOVERNANCE_ROLES)
    def gi_gov_audits():
        db = get_db()
        if request.method == 'POST':
            governance_clinical_service.create_audit(
                db,
                title=(request.form.get('title') or '').strip(),
                objective=(request.form.get('objective') or '').strip(),
                methodology=(request.form.get('methodology') or '').strip(),
                investigator_id=session.get('user_id'),
            )
            flash('Audit project created.', 'success')
            return redirect(url_for('gi_gov_audits'))
        audits = governance_clinical_service.list_audits(db)
        from gi_platform import nav_permissions as navperm
        return render_template(
            'gi/gov_audits.html', audits=audits, statuses=AUDIT_STATUSES,
            module_intro='Plan and track clinical audits — measure care against standards.',
        )

    @app.route('/governance/documents', methods=['GET', 'POST'])
    @login_required
    @roles_required(*GOVERNANCE_ROLES)
    def gi_gov_documents():
        db = get_db()
        if request.method == 'POST':
            governance_clinical_service.create_document(
                db,
                title=(request.form.get('title') or '').strip(),
                document_type=request.form.get('document_type', 'sop'),
                content_summary=(request.form.get('content_summary') or '').strip(),
            )
            flash('Document created.', 'success')
            return redirect(url_for('gi_gov_documents'))
        documents = governance_clinical_service.list_documents(db)
        return render_template(
            'gi/gov_documents.html', documents=documents, doc_types=DOCUMENT_TYPES,
            module_intro='Department SOPs, protocols, and policies — versioned and trackable.',
        )

    @app.route('/governance/documents/<int:doc_id>/ack', methods=['POST'])
    @login_required
    @roles_required(*STAFF_ROLES)
    def gi_gov_document_ack(doc_id):
        governance_clinical_service.acknowledge_document(get_db(), doc_id, session.get('user_id'))
        flash('Document acknowledged.', 'success')
        return redirect(url_for('gi_gov_documents'))

    @app.route('/governance/checklists', methods=['GET', 'POST'])
    @login_required
    @roles_required(*GOVERNANCE_ROLES, 'registrar', 'nurse_manager')
    def gi_gov_checklists():
        db = get_db()
        if request.method == 'POST':
            items = [x.strip() for x in request.form.getlist('item') if x.strip()]
            governance_clinical_service.create_checklist(
                db,
                checklist_type=request.form.get('checklist_type', 'endoscopy_safety'),
                items=items,
                completed_by_id=session.get('user_id'),
            )
            flash('Checklist saved.', 'success')
            return redirect(url_for('gi_gov_checklists'))
        checklists = governance_clinical_service.list_checklists(db)
        from gi_platform import nav_permissions as navperm
        return render_template(
            'gi/gov_checklists.html', checklists=checklists, types=CHECKLIST_TYPES,
            module_intro=navperm.intro('checklists'),
        )

    @app.route('/governance/logbook/export')
    @login_required
    @roles_required(*GOVERNANCE_ROLES)
    def gi_logbook_export():
        import io
        from openpyxl import Workbook
        db = get_db()
        rows = logbook_service.export_logbook_rows(db)
        wb = Workbook()
        ws = wb.active
        ws.title = 'Logbook'
        ws.append([
            'Date', 'Staff name', 'Role', 'Activity type', 'Description',
            'MRN', 'Patient name', 'Source module', 'CanMEDS domain',
            'Entrustment score (1-5)', 'Evaluator', 'Evaluation note', 'Evaluated at',
        ])
        for r in rows:
            ws.append([
                (r['created_at'] or '')[:19], r['staff_name'], r['staff_role'],
                r['activity_type'], r['title'], r['mrn'] or '',
                r['patient_name'] or r['ward_patient_name'] or '',
                r['source_module'] or '', r['competency_domain'] or '',
                r['canmeds_score'] or '', r['evaluator_name'] or '',
                r['evaluator_note'] or '', (r['evaluated_at'] or '')[:19],
            ])
        buf = io.BytesIO()
        wb.save(buf)
        from flask import send_file
        return send_file(
            buf, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True, download_name='department_logbook.xlsx',
        )

    @app.route('/governance/approvals')
    @login_required
    @roles_required(*REGISTRAR_APPROVE_ROLES)
    def gi_registrar_approvals():
        db = get_db()
        data = governance_service.get_hod_dashboard(db)
        from gi_platform import nav_permissions as navperm
        data['module_intro'] = navperm.intro('registrar_approvals')
        return render_template('gi/registrar_approvals.html', **data)

    @app.route('/governance/orders/<int:order_id>/approve', methods=['POST'])
    @login_required
    @roles_required(*REGISTRAR_APPROVE_ROLES)
    def gi_approve_order(order_id):
        db = get_db()
        decision = request.form.get('decision', 'approve')
        status = 'approved' if decision == 'approve' else 'rejected'
        order = db.execute('SELECT * FROM gi_investigation_order WHERE id = ?', (order_id,)).fetchone()
        from gi_platform import order_service, workforce_service
        sched_date = (request.form.get('scheduled_date') or '').strip()
        sched_time = (request.form.get('scheduled_time') or '').strip()
        if status == 'approved' and order and order_service.is_schedulable_procedure(
            order['order_type'], order['item_code'] or ''
        ) and not sched_date:
            flash('Set procedure date before approving endoscopy/ERCP orders.', 'error')
            return redirect(url_for('gi_registrar_approvals'))
        db.execute(
            """
            UPDATE gi_investigation_order
            SET approval_status = ?, approved_by = ?, approved_at = datetime('now'),
                rejection_note = ?
            WHERE id = ?
            """,
            (status, session.get('user_id'),
             (request.form.get('note') or '').strip() if status == 'rejected' else None,
             order_id),
        )
        db.commit()
        if status == 'approved' and order:
            if order_service.is_schedulable_procedure(order['order_type'], order['item_code'] or ''):
                user = db.execute('SELECT username, role FROM user WHERE id = ?', (session.get('user_id'),)).fetchone()
                appt_id = order_service.create_procedure_appointment(
                    db, order_id=order_id, scheduled_date=sched_date, scheduled_time=sched_time,
                    booked_by_username=user['username'] if user else '',
                    booked_by_role=user['role'] if user else '',
                )
                if order['ward_patient_id']:
                    workforce_service.create_task(
                        db, ward_patient_id=order['ward_patient_id'],
                        task_type='endoscopy_booking',
                        title=f"Procedure scheduled: {order['item_name']}",
                        assigned_role='house_officer',
                        notes=f"Booking #{appt_id} · {sched_date} {sched_time}".strip(),
                        created_by=session.get('user_id'),
                    )
                flash(f'Order approved and procedure booked for {sched_date}.', 'success')
            else:
                flash('Order approved.', 'success')
                if order['ward_patient_id'] and order['order_type'] == 'imaging':
                    workforce_service.create_task(
                        db, ward_patient_id=order['ward_patient_id'],
                        task_type='investigations',
                        title=f"Arrange imaging: {order['item_name']}",
                        assigned_role='house_officer',
                        notes=f"Approved order #{order_id}",
                        created_by=session.get('user_id'),
                    )
        else:
            flash(f'Order {status}.', 'success')
        audit_service.log_event(
            db, action=f'order_{status}', entity_type='gi_investigation_order',
            entity_id=order_id, user_id=session.get('user_id'),
        )
        return redirect(request.referrer or url_for('gi_registrar_approvals'))

    @app.route('/governance/plans/<int:plan_id>/approve', methods=['POST'])
    @login_required
    @roles_required(*REGISTRAR_APPROVE_ROLES)
    def gi_approve_plan(plan_id):
        db = get_db()
        decision = request.form.get('decision', 'approve')
        status = 'approved' if decision == 'approve' else 'rejected'
        db.execute(
            """
            UPDATE gi_management_plan
            SET approval_status = ?, approved_by = ?, approved_at = datetime('now'),
                rejection_note = ?
            WHERE id = ?
            """,
            (status, session.get('user_id'),
             (request.form.get('note') or '').strip() if status == 'rejected' else None,
             plan_id),
        )
        db.commit()
        audit_service.log_event(
            db, action=f'plan_{status}', entity_type='gi_management_plan',
            entity_id=plan_id, user_id=session.get('user_id'),
        )
        flash(f'Management plan {status}.', 'success')
        return redirect(request.referrer or url_for('gi_registrar_approvals'))
