"""Patient journey timeline routes."""

from flask import flash, redirect, render_template, request, session, url_for

from gi_platform import patient_journey_service, research_service

JOURNEY_ROLES = (
    'admin', 'hod', 'consultant', 'specialist', 'registrar',
    'house_officer', 'pg_trainee', 'nurse_manager',
)
GI_RESEARCH_ROLES = (
    'admin', 'specialist', 'hod', 'consultant', 'registrar',
    'house_officer', 'pg_trainee', 'general_endoscopy',
)


def register_journey_routes(app, *, get_db, login_required, roles_required):
    @app.route('/journey/patient/<int:ward_patient_id>')
    @login_required
    @roles_required(*JOURNEY_ROLES)
    def gi_patient_journey(ward_patient_id):
        db = get_db()
        wp = db.execute('SELECT * FROM ward_patient WHERE id = ?', (ward_patient_id,)).fetchone()
        if not wp:
            flash('Patient not found.', 'error')
            return redirect(url_for('ward_dashboard'))
        events = patient_journey_service.timeline_for_patient(db, ward_patient_id=ward_patient_id)
        labs = patient_journey_service.labs_for_patient(db, ward_patient_id=ward_patient_id)
        return render_template(
            'gi/patient_journey.html',
            patient=wp, events=events, labs=labs,
            back_url=url_for('ward_patient_view', ward_patient_id=ward_patient_id),
        )

    @app.route('/journey/patient/<int:ward_patient_id>/lab', methods=['POST'])
    @login_required
    @roles_required(*JOURNEY_ROLES)
    def gi_patient_add_lab(ward_patient_id):
        db = get_db()
        patient_journey_service.record_lab_result(
            db,
            test_name=(request.form.get('test_name') or '').strip(),
            result_value=(request.form.get('result_value') or '').strip(),
            result_unit=(request.form.get('result_unit') or '').strip(),
            ward_patient_id=ward_patient_id,
            recorded_by=session.get('user_id'),
        )
        from gi_platform import activity_service
        activity_service.record_activity(
            db, user_id=session.get('user_id'),
            activity_type='lab_result', title='Lab result recorded',
            ward_patient_id=ward_patient_id,
            source_module='journey', source_type='lab_result',
        )
        flash('Lab result recorded.', 'success')
        return redirect(url_for('gi_patient_journey', ward_patient_id=ward_patient_id))

    @app.route('/research/enrollment/<int:enrollment_id>/sync', methods=['POST'])
    @login_required
    @roles_required(*GI_RESEARCH_ROLES)
    def gi_research_sync_enrollment(enrollment_id):
        db = get_db()
        from gi_platform import research_service as rs
        rs.auto_import_enrollment_data(db, enrollment_id)
        count = patient_journey_service.sync_research_variables_from_journey(db, enrollment_id)
        flash(f'Auto-import complete — synced {count} additional variables from patient journey.', 'success')
        enr = db.execute('SELECT registry_id FROM gi_research_enrollment WHERE id = ?', (enrollment_id,)).fetchone()
        if enr:
            return redirect(url_for('gi_research_capture', enrollment_id=enrollment_id))
        return redirect(url_for('gi_research_index'))
