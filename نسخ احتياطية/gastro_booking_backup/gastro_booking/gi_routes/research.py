"""Research registry routes — separate from ERCP research registry."""

from flask import flash, redirect, render_template, request, session, url_for, Response

from gi_platform import audit_service, research_service

GI_RESEARCH_INDEX_ROLES = ('admin', 'specialist', 'hod')
GI_RESEARCH_ROLES = ('admin', 'specialist', 'hod', 'consultant', 'registrar',
                     'house_officer', 'pg_trainee', 'general_endoscopy')
GI_RESEARCH_WRITE = ('admin', 'specialist', 'hod', 'consultant', 'registrar',
                     'house_officer', 'pg_trainee', 'general_endoscopy')
GI_RESEARCH_HOD = ('admin', 'hod')
GI_RESEARCH_REVIEW = ('admin', 'specialist', 'hod')


def register_research_routes(app, *, get_db, login_required, roles_required):
    def _registry_access(db, registry_id, user_row):
        role = user_row['role'] if user_row else ''
        uid = session.get('user_id')
        return research_service.user_can_access_registry(db, registry_id, uid, role)

    @app.route('/research')
    @login_required
    @roles_required(*GI_RESEARCH_INDEX_ROLES)
    def gi_research_index():
        db = get_db()
        registries = db.execute(
            """
            SELECT r.*, u.full_name AS lead_name,
                   (SELECT COUNT(*) FROM gi_research_enrollment e
                    WHERE e.registry_id = r.id
                      AND COALESCE(e.status, 'active') != 'withdrawn') AS enrollment_count
            FROM gi_research_registry r
            LEFT JOIN user u ON u.id = r.lead_user_id
            ORDER BY r.updated_at DESC
            """
        ).fetchall()
        ward_patient_id = request.args.get('ward_patient_id', type=int)
        from gi_platform import nav_permissions as navperm
        return render_template(
            'gi/research_index.html', registries=registries,
            ward_patient_id=ward_patient_id,
            module_intro=navperm.intro('research'),
        )

    @app.route('/research/new', methods=['GET', 'POST'])
    @login_required
    @roles_required(*GI_RESEARCH_WRITE)
    def gi_research_new():
        if request.method == 'POST':
            code = (request.form.get('code') or '').strip()
            title = (request.form.get('title') or '').strip()
            if not code or not title:
                flash('Code and title required.', 'error')
            else:
                rid = research_service.create_registry(
                    get_db(), code=code, title=title,
                    pi_name=(request.form.get('pi_name') or '').strip(),
                    description=(request.form.get('description') or '').strip(),
                    created_by=session.get('user_id'),
                )
                flash('Research registry created.', 'success')
                return redirect(url_for('gi_research_detail', registry_id=rid))
        return render_template('gi/research_form.html')

    @app.route('/research/<int:registry_id>')
    @login_required
    @roles_required(*GI_RESEARCH_ROLES)
    def gi_research_detail(registry_id):
        db = get_db()
        user = db.execute(
            'SELECT role FROM user WHERE id = ?', (session.get('user_id'),)
        ).fetchone()
        if not _registry_access(db, registry_id, user):
            flash('You do not have access to this research project.', 'error')
            return redirect(url_for('gi_workforce_board'))
        registry = research_service.get_registry(db, registry_id)
        if not registry:
            flash('Registry not found.', 'error')
            return redirect(url_for('gi_research_index'))
        variables = research_service.list_variables(db, registry_id)
        enrollments = research_service.list_enrollments(db, registry_id)
        analytics = research_service.registry_analytics(db, registry_id)
        ward_patient_id = request.args.get('ward_patient_id', type=int)
        role = user['role'] if user else ''
        lead_user = None
        if registry['lead_user_id']:
            lead_user = db.execute(
                'SELECT id, full_name, username FROM user WHERE id = ?',
                (registry['lead_user_id'],),
            ).fetchone()
        team_users = []
        for tid in research_service.team_user_ids(registry):
            tu = db.execute(
                'SELECT id, full_name, username FROM user WHERE id = ?', (tid,)
            ).fetchone()
            if tu:
                team_users.append(tu)
        can_manage_team = role in GI_RESEARCH_HOD
        from gi_platform import nav_permissions as navperm
        return render_template(
            'gi/research_detail.html',
            registry=registry, variables=variables, enrollments=enrollments,
            analytics=analytics, ward_patient_id=ward_patient_id,
            can_hod_review=navperm.can_review_hod_research(role),
            can_manage_team=can_manage_team,
            is_lead=registry['lead_user_id'] == session.get('user_id'),
            lead_user=lead_user, team_users=team_users,
            team_activity=analytics.get('team_activity') or [],
            module_intro=navperm.intro('research'),
        )

    @app.route('/research/<int:registry_id>/variables/new', methods=['GET', 'POST'])
    @login_required
    @roles_required(*GI_RESEARCH_WRITE)
    def gi_research_add_variable(registry_id):
        registry = research_service.get_registry(get_db(), registry_id)
        if not registry:
            flash('Registry not found.', 'error')
            return redirect(url_for('gi_research_index'))
        if request.method == 'POST':
            name = (request.form.get('name') or '').strip()
            if not name:
                flash('Variable name required.', 'error')
            else:
                options_raw = (request.form.get('options') or '').strip()
                options = [o.strip() for o in options_raw.split(',') if o.strip()] if options_raw else None
                research_service.add_variable(
                    get_db(), registry_id, name=name,
                    var_type=request.form.get('var_type') or 'text',
                    required=bool(request.form.get('required')),
                    code=(request.form.get('code') or '').strip(),
                    source_type=(request.form.get('source_type') or '').strip(),
                    sort_order=request.form.get('sort_order', type=int) or 0,
                    options=options,
                )
                flash('Variable added.', 'success')
                return redirect(url_for('gi_research_detail', registry_id=registry_id))
        return render_template('gi/research_variable_form.html', registry=registry)

    @app.route('/research/<int:registry_id>/enroll', methods=['POST'])
    @login_required
    @roles_required(*GI_RESEARCH_ROLES)
    def gi_research_enroll(registry_id):
        db = get_db()
        registry = research_service.get_registry(db, registry_id)
        if not registry:
            flash('Registry not found.', 'error')
            return redirect(url_for('gi_research_index'))
        if not research_service.registry_ready_for_enrollment(registry):
            flash('This project is not approved for enrollment yet.', 'error')
            return redirect(url_for('gi_research_detail', registry_id=registry_id))
        ward_patient_id = request.form.get('ward_patient_id', type=int)
        mrn = (request.form.get('mrn') or '').strip()
        if not ward_patient_id and not mrn:
            flash('Ward patient ID or MRN required for enrollment.', 'error')
            return redirect(url_for('gi_research_detail', registry_id=registry_id))
        if ward_patient_id:
            from gi_platform import patient_identity_service
            patient_identity_service.sync_ward_patient_mrn(db, ward_patient_id)
            if not mrn:
                mrn = patient_identity_service.resolve_mrn(db, ward_patient_id=ward_patient_id) or ''
        if research_service.enrollment_exists(
            db, registry_id, mrn=mrn, ward_patient_id=ward_patient_id,
        ):
            flash('Patient already enrolled in this registry.', 'error')
            return redirect(url_for('gi_research_detail', registry_id=registry_id))
        appointment_id = request.form.get('appointment_id', type=int)
        if not appointment_id:
            appointment_id = research_service.resolve_appointment_id(
                db, mrn=mrn, ward_patient_id=ward_patient_id,
            )
        eid = research_service.enroll_patient(
            db, registry_id, ward_patient_id=ward_patient_id, mrn=mrn,
            appointment_id=appointment_id,
            enrolled_by=session.get('user_id'),
            responsible_user_id=session.get('user_id'),
        )
        research_service.auto_import_enrollment_data(db, eid)
        audit_service.log_event(
            db, action='research_enroll', entity_type='gi_research_enrollment',
            entity_id=eid, user_id=session.get('user_id'),
        )
        flash('Patient enrolled in research registry.', 'success')
        return redirect(url_for('gi_research_detail', registry_id=registry_id))

    @app.route('/research/enrollment/<int:enrollment_id>/capture', methods=['GET', 'POST'])
    @login_required
    @roles_required(*GI_RESEARCH_ROLES)
    def gi_research_capture(enrollment_id):
        db = get_db()
        enrollment = research_service.get_enrollment(db, enrollment_id)
        if not enrollment:
            flash('Enrollment not found.', 'error')
            return redirect(url_for('gi_workforce_board'))
        user = db.execute(
            'SELECT role FROM user WHERE id = ?', (session.get('user_id'),)
        ).fetchone()
        if not _registry_access(db, enrollment['registry_id'], user):
            flash('You do not have access to this research project.', 'error')
            return redirect(url_for('gi_workforce_board'))
        research_service.auto_import_enrollment_data(db, enrollment_id)
        enrollment = research_service.get_enrollment(db, enrollment_id)
        registry = research_service.get_registry(db, enrollment['registry_id'])
        variables = research_service.list_capture_variables(db, enrollment['registry_id'])
        import json
        from gi_platform import nav_permissions as navperm
        payload = json.loads(enrollment['payload_json'] or '{}')
        variables_display = []
        for v in variables:
            vd = dict(v)
            try:
                vd['options_list'] = json.loads(v['options_json'] or '[]')
            except (json.JSONDecodeError, TypeError):
                vd['options_list'] = []
            variables_display.append(vd)
        if request.method == 'POST':
            new_payload = dict(payload)
            for v in variables:
                key = v['code'] or v['name']
                field = f'var_{v["id"]}'
                new_payload[key] = (request.form.get(field) or '').strip()
            research_service.update_enrollment_payload(db, enrollment_id, new_payload)
            flash('Research data saved (does not alter clinical record).', 'success')
            return redirect(url_for('gi_research_detail', registry_id=enrollment['registry_id']))
        return render_template(
            'gi/research_capture.html',
            enrollment=enrollment, registry=registry, variables=variables_display, payload=payload,
            module_intro=navperm.intro('research_capture'),
        )

    @app.route('/research/<int:registry_id>/export')
    @login_required
    @roles_required(*GI_RESEARCH_ROLES)
    def gi_research_export(registry_id):
        csv_text = research_service.export_registry_csv(get_db(), registry_id)
        registry = research_service.get_registry(get_db(), registry_id)
        filename = f"{registry['code']}_export.csv" if registry else 'research_export.csv'
        return Response(
            csv_text, mimetype='text/csv',
            headers={'Content-Disposition': f'attachment; filename={filename}'},
        )

    @app.route('/research/<int:registry_id>/dashboard')
    @login_required
    @roles_required(*GI_RESEARCH_ROLES)
    def gi_research_dashboard(registry_id):
        db = get_db()
        registry = research_service.get_registry(db, registry_id)
        if not registry:
            flash('Registry not found.', 'error')
            return redirect(url_for('gi_research_index'))
        analytics = research_service.registry_analytics(db, registry_id)
        enrollments = research_service.list_enrollments(db, registry_id)
        return render_template(
            'gi/research_dashboard.html',
            registry=registry, analytics=analytics, enrollments=enrollments,
        )

    @app.route('/research/hod/assign', methods=['GET', 'POST'])
    @login_required
    @roles_required(*GI_RESEARCH_HOD)
    def gi_research_hod_assign():
        db = get_db()
        users = db.execute(
            "SELECT id, username, full_name, role FROM user WHERE is_approved=1 ORDER BY full_name"
        ).fetchall()
        if request.method == 'POST':
            from gi_platform import user_mention_service
            lead_text = (request.form.get('lead_usernames') or '').strip()
            team_text = (request.form.get('team_usernames') or '').strip()
            lead_ids = user_mention_service.resolve_mention_usernames(db, lead_text)
            team_ids = user_mention_service.resolve_mention_usernames(db, team_text)
            if not lead_ids:
                flash('Specify research lead with @username.', 'error')
            else:
                rid = research_service.assign_hod_project(
                    db,
                    code=(request.form.get('code') or '').strip(),
                    title=(request.form.get('title') or '').strip(),
                    lead_user_id=lead_ids[0],
                    team_user_ids=team_ids,
                    assigned_by_hod_id=session.get('user_id'),
                    description=(request.form.get('description') or '').strip(),
                )
                combined = ' '.join(
                    p for p in (lead_text, team_text, request.form.get('description') or '') if p
                )
                if '@' in combined:
                    user_mention_service.process_mentions(
                        db,
                        combined,
                        context_title=f'Research: {(request.form.get("title") or "").strip()}',
                        link_url=f'/research/{rid}',
                        source_module='research',
                        source_id=rid,
                        actor_id=session.get('user_id'),
                    )
                flash('Research project assigned to team.', 'success')
                return redirect(url_for('gi_research_detail', registry_id=rid))
        return render_template(
            'gi/research_hod_assign.html', users=users,
            module_intro='Assign a research project to a lead and team; approve variables before data collection.',
        )

    @app.route('/research/<int:registry_id>/hod-review', methods=['POST'])
    @login_required
    @roles_required(*GI_RESEARCH_REVIEW)
    def gi_research_hod_review(registry_id):
        approve = request.form.get('decision') == 'approve'
        research_service.hod_review_project(
            get_db(), registry_id, approve=approve,
            note=(request.form.get('note') or '').strip(),
        )
        flash('Project review saved.', 'success')
        return redirect(url_for('gi_research_detail', registry_id=registry_id))

    @app.route('/research/variables/<int:variable_id>/review', methods=['POST'])
    @login_required
    @roles_required(*GI_RESEARCH_REVIEW)
    def gi_research_variable_review(variable_id):
        approve = request.form.get('decision') == 'approve'
        research_service.review_variable(
            get_db(), variable_id, approve=approve,
            reviewer_id=session.get('user_id'),
            review_note=(request.form.get('note') or '').strip(),
        )
        flash('Variable review saved.', 'success')
        return redirect(request.referrer or url_for('gi_research_index'))

    @app.route('/research/variables/<int:variable_id>/delete', methods=['POST'])
    @login_required
    @roles_required(*GI_RESEARCH_REVIEW)
    def gi_research_delete_variable(variable_id):
        db = get_db()
        row = db.execute(
            'SELECT registry_id FROM gi_research_variable WHERE id = ?', (variable_id,)
        ).fetchone()
        if row:
            research_service.delete_variable(db, variable_id)
            flash('Variable deleted.', 'success')
            return redirect(url_for('gi_research_detail', registry_id=row['registry_id']))
        flash('Variable not found.', 'error')
        return redirect(url_for('gi_research_index'))

    @app.route('/research/enrollment/<int:enrollment_id>/withdraw', methods=['POST'])
    @login_required
    @roles_required(*GI_RESEARCH_WRITE)
    def gi_research_withdraw(enrollment_id):
        db = get_db()
        enrollment = research_service.get_enrollment(db, enrollment_id)
        if not enrollment:
            flash('Enrollment not found.', 'error')
            return redirect(url_for('gi_workforce_board'))
        user = db.execute(
            'SELECT role FROM user WHERE id = ?', (session.get('user_id'),)
        ).fetchone()
        if not _registry_access(db, enrollment['registry_id'], user):
            flash('You do not have access to this research project.', 'error')
            return redirect(url_for('gi_workforce_board'))
        if research_service.withdraw_enrollment(db, enrollment_id):
            audit_service.log_event(
                db, action='research_withdraw', entity_type='gi_research_enrollment',
                entity_id=enrollment_id, user_id=session.get('user_id'),
            )
            flash('Enrollment withdrawn.', 'success')
        else:
            flash('Could not withdraw enrollment.', 'error')
        return redirect(url_for('gi_research_detail', registry_id=enrollment['registry_id']))

    @app.route('/research/<int:registry_id>/team', methods=['POST'])
    @login_required
    @roles_required(*GI_RESEARCH_HOD)
    def gi_research_update_team(registry_id):
        db = get_db()
        registry = research_service.get_registry(db, registry_id)
        if not registry:
            flash('Registry not found.', 'error')
            return redirect(url_for('gi_research_index'))

        remove_id = request.form.get('remove_user_id', type=int)
        if remove_id:
            if research_service.remove_team_member(db, registry_id, remove_id):
                audit_service.log_event(
                    db, action='research_team_remove', entity_type='gi_research_registry',
                    entity_id=registry_id, user_id=session.get('user_id'),
                    details={'removed_user_id': remove_id},
                )
                flash('Team member removed.', 'success')
            else:
                flash('Cannot remove this member (not on team or is the lead).', 'error')
            return redirect(url_for('gi_research_detail', registry_id=registry_id))

        from gi_platform import user_mention_service
        lead_text = (request.form.get('lead_usernames') or '').strip()
        team_text = (request.form.get('team_usernames') or '').strip()
        lead_ids = user_mention_service.resolve_mention_usernames(db, lead_text)
        team_ids = user_mention_service.resolve_mention_usernames(db, team_text)
        if not lead_ids:
            flash('Research lead is required (@username).', 'error')
            return redirect(url_for('gi_research_detail', registry_id=registry_id))

        ok = research_service.update_registry_team(
            db, registry_id, lead_user_id=lead_ids[0], team_user_ids=team_ids,
        )
        if ok:
            audit_service.log_event(
                db, action='research_team_update', entity_type='gi_research_registry',
                entity_id=registry_id, user_id=session.get('user_id'),
                details={'lead_user_id': lead_ids[0], 'team_count': len(team_ids)},
            )
            combined = ' '.join(p for p in (lead_text, team_text) if p)
            if '@' in combined:
                user_mention_service.process_mentions(
                    db, combined,
                    context_title=f'Research team: {registry["title"]}',
                    link_url=f'/research/{registry_id}',
                    source_module='research',
                    source_id=registry_id,
                    actor_id=session.get('user_id'),
                )
            flash('Research team updated.', 'success')
        else:
            flash('Could not update team.', 'error')
        return redirect(url_for('gi_research_detail', registry_id=registry_id))

    @app.route('/research/<int:registry_id>/propose-variable', methods=['POST'])
    @login_required
    @roles_required(*GI_RESEARCH_WRITE)
    def gi_research_propose_variable(registry_id):
        name = (request.form.get('name') or '').strip()
        if name:
            research_service.propose_variable(
                get_db(), registry_id, name=name,
                var_type=request.form.get('var_type') or 'text',
                proposed_by=session.get('user_id'),
                code=(request.form.get('code') or '').strip(),
                source_type=(request.form.get('source_type') or '').strip(),
            )
            flash('Variable proposed — awaiting HOD approval.', 'success')
        return redirect(url_for('gi_research_detail', registry_id=registry_id))
