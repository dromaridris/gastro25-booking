"""Platform phases 1–4 routes — documents, consults, branding, banner, calendar, education, archive."""

from __future__ import annotations

from datetime import date, timedelta

from flask import flash, jsonify, redirect, render_template, request, send_file, session, url_for

CLINICAL_ROLES = (
    'admin', 'specialist', 'pg_trainee', 'consultant', 'hod', 'registrar',
    'house_officer', 'general_endoscopy', 'nurse_manager',
)
WARD_DOC_ROLES = (
    'admin', 'hod', 'consultant', 'specialist', 'registrar', 'general_endoscopy',
    'house_officer', 'pg_trainee', 'nurse_manager', 'staff_nurse',
)
ADMIN_BRAND_ROLES = ('admin', 'hod', 'specialist')


def register_platform_phase_routes(app, *, get_db, login_required, roles_required):
    # --- Patient documents ---
    @app.route('/ward/patient/<int:ward_patient_id>/documents', methods=['GET', 'POST'])
    @login_required
    @roles_required(*WARD_DOC_ROLES)
    def gi_patient_documents(ward_patient_id):
        from gi_platform import patient_document_service as pds
        db = get_db()
        if request.method == 'POST':
            f = request.files.get('document_file')
            try:
                if not f or not f.filename:
                    raise ValueError('Choose a file to upload.')
                pds.upload(
                    db,
                    ward_patient_id=ward_patient_id,
                    title=(request.form.get('title') or '').strip(),
                    file_obj=f,
                    filename=f.filename,
                    content_type=f.content_type,
                    category=(request.form.get('category') or 'general').strip(),
                    notes=(request.form.get('notes') or '').strip(),
                    uploaded_by=session.get('user_id'),
                )
                flash('Document uploaded.', 'success')
            except ValueError as exc:
                flash(str(exc), 'error')
            return redirect(url_for('gi_patient_documents', ward_patient_id=ward_patient_id))
        docs = pds.list_for_patient(db, ward_patient_id)
        patient = db.execute('SELECT * FROM ward_patient WHERE id = ?', (ward_patient_id,)).fetchone()
        return render_template(
            'gi/patient_documents.html',
            ward_patient_id=ward_patient_id,
            patient=patient,
            documents=docs,
            back_url=url_for('ward_patient_view', ward_patient_id=ward_patient_id),
        )

    @app.route('/ward/patient/documents/<int:doc_id>/download')
    @login_required
    @roles_required(*WARD_DOC_ROLES)
    def gi_patient_document_download(doc_id):
        from gi_platform import patient_document_service as pds
        db = get_db()
        doc = pds.get_document(db, doc_id)
        if not doc:
            flash('Document not found.', 'error')
            return redirect(url_for('ward_dashboard'))
        path = pds.file_path(doc)
        if not path:
            flash('File missing on server.', 'error')
            return redirect(url_for('gi_patient_documents', ward_patient_id=doc['ward_patient_id']))
        return send_file(path, as_attachment=True, download_name=doc['original_filename'] or 'document')

    @app.route('/ward/patient/documents/<int:doc_id>/delete', methods=['POST'])
    @login_required
    @roles_required('admin', 'hod', 'consultant', 'specialist', 'registrar')
    def gi_patient_document_delete(doc_id):
        from gi_platform import patient_document_service as pds
        db = get_db()
        doc = pds.get_document(db, doc_id)
        if doc:
            pds.archive(db, doc_id)
            flash('Document removed.', 'success')
            return redirect(url_for('gi_patient_documents', ward_patient_id=doc['ward_patient_id']))
        flash('Document not found.', 'error')
        return redirect(url_for('ward_dashboard'))

    # --- Consult requests ---
    @app.route('/consult-requests')
    @login_required
    @roles_required(*CLINICAL_ROLES)
    def gi_consult_requests():
        from gi_platform import consult_service
        db = get_db()
        status = (request.args.get('status') or '').strip() or None
        rows = consult_service.list_requests(db, status=status)
        return render_template(
            'gi/consult_requests.html',
            requests=rows,
            status_filter=status or '',
            urgency_choices=consult_service.URGENCY_CHOICES,
        )

    @app.route('/consult-requests/new', methods=['GET', 'POST'])
    @login_required
    @roles_required(*CLINICAL_ROLES)
    def gi_consult_request_new():
        from gi_platform import consult_service
        db = get_db()
        ward_patient_id = request.args.get('ward_patient_id', type=int) or request.form.get('ward_patient_id', type=int)
        patients = db.execute(
            'SELECT id, patient_name, mrn FROM ward_patient ORDER BY patient_name LIMIT 200'
        ).fetchall()
        if request.method == 'POST':
            try:
                wp_id = int(request.form.get('ward_patient_id') or 0)
                rid = consult_service.create(
                    db,
                    ward_patient_id=wp_id,
                    specialty=(request.form.get('specialty') or '').strip(),
                    clinical_question=(request.form.get('clinical_question') or '').strip(),
                    urgency=(request.form.get('urgency') or 'routine').strip(),
                    requesting_user_id=session.get('user_id'),
                )
                flash('Consult request submitted.', 'success')
                return redirect(url_for('gi_consult_request_detail', request_id=rid))
            except (ValueError, TypeError) as exc:
                flash(str(exc), 'error')
        return render_template(
            'gi/consult_request_form.html',
            patients=patients,
            ward_patient_id=ward_patient_id,
            urgency_choices=consult_service.URGENCY_CHOICES,
        )

    @app.route('/consult-requests/<int:request_id>')
    @login_required
    @roles_required(*CLINICAL_ROLES)
    def gi_consult_request_detail(request_id):
        from gi_platform import consult_service
        db = get_db()
        req = consult_service.get_request(db, request_id)
        if not req:
            flash('Consult request not found.', 'error')
            return redirect(url_for('gi_consult_requests'))
        return render_template('gi/consult_request_detail.html', req=req)

    @app.route('/consult-requests/<int:request_id>/accept', methods=['POST'])
    @login_required
    @roles_required('admin', 'consultant', 'hod', 'specialist', 'registrar')
    def gi_consult_request_accept(request_id):
        from gi_platform import consult_service
        try:
            consult_service.accept(get_db(), request_id, user_id=session.get('user_id') or 0)
            flash('Consult accepted.', 'success')
        except ValueError as exc:
            flash(str(exc), 'error')
        return redirect(url_for('gi_consult_request_detail', request_id=request_id))

    @app.route('/consult-requests/<int:request_id>/complete', methods=['POST'])
    @login_required
    @roles_required('admin', 'consultant', 'hod', 'specialist', 'registrar')
    def gi_consult_request_complete(request_id):
        from gi_platform import consult_service
        try:
            consult_service.complete(
                get_db(), request_id,
                user_id=session.get('user_id') or 0,
                response_notes=(request.form.get('response_notes') or '').strip(),
            )
            flash('Consult completed.', 'success')
        except ValueError as exc:
            flash(str(exc), 'error')
        return redirect(url_for('gi_consult_request_detail', request_id=request_id))

    @app.route('/consult-requests/<int:request_id>/reject', methods=['POST'])
    @login_required
    @roles_required('admin', 'consultant', 'hod', 'specialist', 'registrar')
    def gi_consult_request_reject(request_id):
        from gi_platform import consult_service
        try:
            consult_service.reject(
                get_db(), request_id,
                reason=(request.form.get('reason') or '').strip(),
            )
            flash('Consult rejected.', 'success')
        except ValueError as exc:
            flash(str(exc), 'error')
        return redirect(url_for('gi_consult_request_detail', request_id=request_id))

    @app.route('/consult-requests/<int:request_id>/cancel', methods=['POST'])
    @login_required
    @roles_required(*CLINICAL_ROLES)
    def gi_consult_request_cancel(request_id):
        from gi_platform import consult_service
        try:
            consult_service.cancel(get_db(), request_id, user_id=session.get('user_id') or 0)
            flash('Consult cancelled.', 'success')
        except ValueError as exc:
            flash(str(exc), 'error')
        return redirect(url_for('gi_consult_request_detail', request_id=request_id))

    # --- Clinical AI admin ---
    @app.route('/admin/clinical-ai')
    @login_required
    @roles_required('admin', 'hod', 'specialist')
    def gi_clinical_ai_admin():
        from gi_platform import ai_service
        from gi_platform.clinical_ai.config import ClinicalAIConfig
        from gi_platform.clinical_ai.provider_health import provider_env_status
        from gi_platform.pdf_extract_service import _ocr_available
        db = get_db()
        cfg = ClinicalAIConfig.from_env(app.config)
        svc = ai_service.get_clinical_ai_service(db, app.config)
        config_data = svc.get_configuration(role=session.get('role'))
        return render_template(
            'gi/clinical_ai_admin.html',
            config=cfg.to_dict(),
            active_provider=config_data.get('active_provider'),
            provider_status=provider_env_status(),
            ocr_available=_ocr_available(),
        )

    @app.route('/admin/clinical-ai/test', methods=['POST'])
    @login_required
    @roles_required('admin', 'hod', 'specialist')
    def gi_clinical_ai_test():
        from gi_platform.clinical_ai.provider_health import test_provider
        provider_key = (request.form.get('provider_key') or 'stub').strip()
        result = test_provider(provider_key)
        flash(result.get('message') or ('OK' if result.get('ok') else 'Test failed'), 'success' if result.get('ok') else 'error')
        return redirect(url_for('gi_clinical_ai_admin'))

    # --- Branding ---
    @app.route('/admin/branding', methods=['GET', 'POST'])
    @login_required
    @roles_required(*ADMIN_BRAND_ROLES)
    def gi_admin_branding():
        from gi_platform import branding_service as bs
        db = get_db()
        if request.method == 'POST':
            fields = {
                'site_name': (request.form.get('site_name') or '').strip(),
                'slogan': (request.form.get('slogan') or '').strip(),
                'dept_subtitle': (request.form.get('dept_subtitle') or '').strip(),
                'primary_color': (request.form.get('primary_color') or '').strip(),
                'secondary_color': (request.form.get('secondary_color') or '').strip(),
                'show_hospital_logo': request.form.get('show_hospital_logo') == '1',
                'show_department_logo': request.form.get('show_department_logo') == '1',
            }
            current = bs.get_settings(db)
            if request.files.get('hospital_logo_file') and request.files['hospital_logo_file'].filename:
                fields['hospital_logo_filename'] = bs.save_upload(
                    request.files['hospital_logo_file'], kind='hospital',
                )
            else:
                fields['hospital_logo_filename'] = current['hospital_logo_filename']
            dept_file = request.files.get('department_logo_file') or request.files.get('logo_file')
            if dept_file and dept_file.filename:
                fields['logo_filename'] = bs.save_upload(dept_file, kind='department')
            else:
                fields['logo_filename'] = current['logo_filename']
            if request.files.get('favicon_file') and request.files['favicon_file'].filename:
                fields['favicon_filename'] = bs.save_upload(request.files['favicon_file'], kind='favicon')
            else:
                fields['favicon_filename'] = current['favicon_filename']
            if request.form.get('clear_hospital_logo') == '1':
                fields['hospital_logo_filename'] = ''
            if request.form.get('clear_department_logo') == '1':
                fields['logo_filename'] = ''
            bs.save_settings(db, fields=fields, updated_by=session.get('user_id'))
            flash('Branding saved.', 'success')
            return redirect(url_for('gi_admin_branding'))
        return render_template('gi/branding_admin.html', branding=bs.get_settings(db))

    @app.route('/branding/asset/<kind>')
    def gi_branding_asset(kind):
        from gi_platform import branding_service as bs
        settings = bs.get_settings(get_db())
        filename = bs.logo_filename_for_kind(settings, kind)
        path = bs.asset_path(filename)
        if not path:
            return ('', 404)
        return send_file(path)

    # --- Pharma banner admin ---
    @app.route('/admin/pharma-banner', methods=['GET', 'POST'])
    @login_required
    @roles_required('admin', 'hod', 'specialist')
    def gi_pharma_banner_admin():
        from gi_platform import pharma_banner_service as pbs
        db = get_db()
        if request.method == 'POST':
            action = (request.form.get('action') or 'create').strip()
            try:
                if action == 'create':
                    pbs.create(
                        db,
                        label=(request.form.get('label') or '').strip(),
                        message=(request.form.get('message') or '').strip(),
                        link_url=(request.form.get('link_url') or '').strip(),
                        sort_order=int(request.form.get('sort_order') or 0),
                    )
                    flash('Banner item added.', 'success')
                elif action == 'toggle':
                    pbs.update(db, int(request.form.get('banner_id')), is_active=int(request.form.get('is_active') or 0))
                    flash('Banner updated.', 'success')
                elif action == 'delete':
                    pbs.delete(db, int(request.form.get('banner_id')))
                    flash('Banner removed.', 'success')
            except (ValueError, TypeError) as exc:
                flash(str(exc), 'error')
            return redirect(url_for('gi_pharma_banner_admin'))
        return render_template('gi/pharma_banner_admin.html', banners=pbs.list_all(db))

    # --- Calendar hub ---
    @app.route('/calendar-hub')
    @login_required
    @roles_required(*CLINICAL_ROLES, 'scheduler', 'endoscopy_staff', 'staff_nurse')
    def gi_calendar_hub():
        from gi_platform import calendar_hub_service as chs
        db = get_db()
        today = date.today()
        from_date = (request.args.get('from') or (today - timedelta(days=7)).isoformat())[:10]
        to_date = (request.args.get('to') or (today + timedelta(days=21)).isoformat())[:10]
        events = chs.list_events(db, from_date=from_date, to_date=to_date, user_id=session.get('user_id'))
        grouped: dict[str, list] = {}
        for ev in events:
            grouped.setdefault(ev['event_date'], []).append(ev)
        sorted_days = sorted(grouped.keys())
        return render_template(
            'gi/calendar_hub.html',
            events=events,
            grouped=grouped,
            sorted_days=sorted_days,
            from_date=from_date,
            to_date=to_date,
        )

    @app.route('/calendar-hub/event', methods=['POST'])
    @login_required
    @roles_required('admin', 'hod', 'specialist', 'consultant')
    def gi_calendar_hub_add_event():
        from gi_platform import calendar_hub_service as chs
        try:
            chs.create_event(
                get_db(),
                title=(request.form.get('title') or '').strip(),
                event_date=(request.form.get('event_date') or '').strip(),
                event_type=(request.form.get('event_type') or 'general').strip(),
                description=(request.form.get('description') or '').strip(),
                link_url=(request.form.get('link_url') or '').strip(),
                created_by=session.get('user_id'),
            )
            flash('Calendar event added.', 'success')
        except ValueError as exc:
            flash(str(exc), 'error')
        return redirect(url_for('gi_calendar_hub'))

    # --- Education ---
    @app.route('/education')
    @login_required
    @roles_required(*CLINICAL_ROLES)
    def gi_education_index():
        from gi_platform import education_service as es
        db = get_db()
        user_filter = request.args.get('user_id', type=int)
        if user_filter and session.get('role') not in ('admin', 'hod', 'consultant', 'specialist'):
            user_filter = session.get('user_id')
        elif not user_filter and session.get('role') not in ('admin', 'hod', 'consultant', 'specialist'):
            user_filter = session.get('user_id')
        activities = es.list_activities(db, user_id=user_filter)
        users = db.execute(
            "SELECT id, full_name FROM user WHERE role IN ('pg_trainee','registrar','house_officer','consultant') ORDER BY full_name"
        ).fetchall()
        return render_template(
            'gi/education_index.html',
            activities=activities,
            activity_types=es.ACTIVITY_TYPES,
            users=users,
            user_filter=user_filter,
        )

    @app.route('/education/new', methods=['POST'])
    @login_required
    @roles_required(*CLINICAL_ROLES)
    def gi_education_create():
        from gi_platform import education_service as es
        try:
            uid = int(request.form.get('user_id') or session.get('user_id') or 0)
            es.create(
                get_db(),
                user_id=uid,
                title=(request.form.get('title') or '').strip(),
                activity_type=(request.form.get('activity_type') or 'other').strip(),
                activity_date=(request.form.get('activity_date') or date.today().isoformat()).strip(),
                description=(request.form.get('description') or '').strip(),
                duration_minutes=request.form.get('duration_minutes', type=int),
                location=(request.form.get('location') or '').strip(),
                created_by=session.get('user_id'),
            )
            flash('Education activity recorded.', 'success')
        except ValueError as exc:
            flash(str(exc), 'error')
        return redirect(url_for('gi_education_index'))

    @app.route('/education/<int:activity_id>/archive', methods=['POST'])
    @login_required
    @roles_required('admin', 'hod', 'consultant', 'specialist')
    def gi_education_archive(activity_id):
        from gi_platform import education_service as es
        es.archive(get_db(), activity_id)
        flash('Activity archived.', 'success')
        return redirect(url_for('gi_education_index'))

    # --- Archive ---
    @app.route('/archive')
    @login_required
    @roles_required('admin', 'hod', 'consultant', 'specialist', 'registrar')
    def gi_archive_index():
        from gi_platform import archive_service as ars
        record_type = (request.args.get('type') or '').strip() or None
        return render_template(
            'gi/archive_index.html',
            records=ars.list_records(get_db(), record_type=record_type),
            record_types=ars.RECORD_TYPES,
            type_filter=record_type or '',
        )

    @app.route('/archive/new', methods=['POST'])
    @login_required
    @roles_required('admin', 'hod', 'consultant', 'specialist')
    def gi_archive_create():
        from gi_platform import archive_service as ars
        f = request.files.get('archive_file')
        try:
            ars.create(
                get_db(),
                record_type=(request.form.get('record_type') or 'document').strip(),
                source_module=(request.form.get('source_module') or 'manual').strip(),
                title=(request.form.get('title') or '').strip(),
                summary=(request.form.get('summary') or '').strip(),
                file_obj=f if f and f.filename else None,
                filename=f.filename if f and f.filename else '',
                archived_by=session.get('user_id'),
            )
            flash('Archive record created.', 'success')
        except ValueError as exc:
            flash(str(exc), 'error')
        return redirect(url_for('gi_archive_index'))

    @app.route('/archive/<int:record_id>/download')
    @login_required
    @roles_required('admin', 'hod', 'consultant', 'specialist', 'registrar')
    def gi_archive_download(record_id):
        from gi_platform import archive_service as ars
        rec = ars.get_record(get_db(), record_id)
        if not rec:
            flash('Record not found.', 'error')
            return redirect(url_for('gi_archive_index'))
        path = ars.file_path(rec)
        if not path:
            flash('No file stored for this record.', 'error')
            return redirect(url_for('gi_archive_index'))
        return send_file(path, as_attachment=True, download_name=rec['title'])
