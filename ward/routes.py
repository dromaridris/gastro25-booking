"""Register ward routes on the existing Flask app — no ERCP changes."""

from flask import flash, jsonify, redirect, render_template, request, url_for

from ward import services as ward_services


WARD_ACCESS_ROLES = (
    'admin', 'hod', 'consultant', 'specialist', 'registrar', 'general_endoscopy',
    'house_officer', 'pg_trainee', 'nurse_manager', 'staff_nurse',
    'scheduler', 'endoscopy_staff',
)


def _bed_checklist_map(dbconn, beds) -> dict:
    """ward_patient_id → discharge checklist for occupied beds."""
    out = {}
    for b in beds:
        wpid = b['ward_patient_id'] if b['ward_patient_id'] else None
        if wpid and wpid not in out:
            out[wpid] = ward_services.get_discharge_checklist(dbconn, wpid)
    return out


def register_ward_routes(app, *, login_required, roles_required, get_db):
    @app.route('/ward')
    @login_required
    @roles_required(*WARD_ACCESS_ROLES)
    def ward_dashboard():
        dbconn = get_db()
        wards = ward_services.list_wards(dbconn)
        ward_id = request.args.get('ward_id', type=int)
        if not ward_id and wards:
            ward_id = wards[0]['id']
        ward = ward_services.get_ward(dbconn, ward_id) if ward_id else None
        beds = ward_services.list_beds(dbconn, ward_id) if ward_id else []
        stats = ward_services.ward_statistics(dbconn, ward_id) if ward_id else {}
        checklists = _bed_checklist_map(dbconn, beds) if beds else {}
        from gi_platform.constants import DISCHARGE_OUTCOMES
        return render_template(
            'ward/dashboard.html',
            wards=wards,
            ward=ward,
            beds=beds,
            stats=stats,
            discharge_outcomes=DISCHARGE_OUTCOMES,
            discharge_checklists=checklists,
        )

    @app.route('/ward/admit', methods=['POST'])
    @login_required
    @roles_required('admin', 'specialist', 'nurse_manager', 'pg_trainee')
    def ward_admit():
        dbconn = get_db()
        try:
            mrn = (request.form.get('mrn') or '').strip() or None
            mrn_skip = (request.form.get('mrn_skip_reason') or '').strip()
            if not mrn and not mrn_skip:
                raise ValueError(
                    'MRN is strongly recommended for booking/ward identity. '
                    'Enter an MRN, or provide a reason to admit without one.'
                )
            admission_id, ward_patient_id = ward_services.admit_patient(
                dbconn,
                bed_id=request.form.get('bed_id', type=int),
                patient_name=(request.form.get('patient_name') or '').strip(),
                mrn=mrn,
                age=(request.form.get('age') or '').strip() or None,
                gender=(request.form.get('gender') or '').strip() or None,
                referral=(request.form.get('referral') or '').strip() or None,
                notes=(request.form.get('notes') or '').strip() or None,
                user_id=getattr(request, 'current_user_id', None),
            )
            if mrn:
                from gi_platform import patient_identity_service
                patient_identity_service.sync_ward_patient_mrn(dbconn, ward_patient_id)
                flash('Patient admitted to ward bed (MRN linked).', 'success')
            else:
                flash(
                    f'Patient admitted without MRN ({mrn_skip}). '
                    'Add MRN on the patient page when available.',
                    'warning',
                )
            _ = admission_id
        except ValueError as exc:
            flash(str(exc), 'error')
        return redirect(request.referrer or url_for('ward_dashboard'))

    @app.route('/ward/transfer', methods=['POST'])
    @login_required
    @roles_required('admin', 'specialist', 'nurse_manager')
    def ward_transfer():
        dbconn = get_db()
        try:
            ward_services.transfer_patient(
                dbconn,
                from_bed_id=request.form.get('from_bed_id', type=int),
                to_bed_id=request.form.get('to_bed_id', type=int),
                notes=(request.form.get('notes') or '').strip() or None,
                user_id=getattr(request, 'current_user_id', None),
            )
            flash('Patient transferred.', 'success')
        except ValueError as exc:
            flash(str(exc), 'error')
        return redirect(request.referrer or url_for('ward_dashboard'))

    @app.route('/ward/discharge', methods=['POST'])
    @login_required
    @roles_required('admin', 'specialist', 'nurse_manager')
    def ward_discharge():
        dbconn = get_db()
        try:
            override = (request.form.get('override') or '').strip() in ('1', 'on', 'true', 'yes')
            ward_patient_id = ward_services.discharge_patient(
                dbconn,
                bed_id=request.form.get('bed_id', type=int),
                notes=(request.form.get('notes') or '').strip() or None,
                outcome=(request.form.get('outcome') or 'discharged').strip(),
                override=override,
                override_reason=(request.form.get('override_reason') or '').strip() or None,
                user_id=getattr(request, 'current_user_id', None),
            )
            flash('Patient discharged from ward bed.', 'success')
            from gi_platform import patient_journey_service
            if ward_patient_id:
                outcome = (request.form.get('outcome') or 'discharged').strip()
                patient_journey_service.add_event(
                    dbconn, event_type='discharge',
                    title=f'Discharge — {outcome.upper()}',
                    ward_patient_id=ward_patient_id,
                    created_by=getattr(request, 'current_user_id', None),
                    details={'outcome': outcome},
                )
        except ValueError as exc:
            flash(str(exc), 'error')
        return redirect(request.referrer or url_for('ward_dashboard'))

    @app.route('/ward/patient/<int:ward_patient_id>/discharge-checklist')
    @login_required
    @roles_required(*WARD_ACCESS_ROLES)
    def ward_discharge_checklist(ward_patient_id):
        dbconn = get_db()
        return jsonify(ward_services.get_discharge_checklist(dbconn, ward_patient_id))

    @app.route('/ward/extra-bed', methods=['POST'])
    @login_required
    @roles_required('admin', 'specialist', 'nurse_manager')
    def ward_add_extra_bed():
        dbconn = get_db()
        ward_id = request.form.get('ward_id', type=int)
        if ward_id:
            ward_services.add_extra_bed(dbconn, ward_id)
            flash('Temporary extra bed added.', 'success')
        return redirect(url_for('ward_dashboard', ward_id=ward_id))

    @app.route('/ward/patient/<int:ward_patient_id>')
    @login_required
    @roles_required(*WARD_ACCESS_ROLES)
    def ward_patient_view(ward_patient_id):
        dbconn = get_db()
        patient = ward_services.get_ward_patient(dbconn, ward_patient_id)
        if not patient:
            flash('Ward patient not found.', 'error')
            return redirect(url_for('ward_dashboard'))
        admission = ward_services.get_active_admission(dbconn, ward_patient_id)
        notes = ward_services.list_clinical_notes(dbconn, ward_patient_id)
        from gi_platform import workforce_service

        workforce_service.seed_default_tasks(dbconn, ward_patient_id, getattr(request, 'current_user_id', None))
        tasks = workforce_service.list_tasks_for_patient(dbconn, ward_patient_id)

        from gi_platform import history_service

        generated_history = history_service.get_latest_narrative_for_patient(dbconn, ward_patient_id)

        from gi_platform import patient_identity_service
        patient_identity_service.sync_ward_patient_mrn(dbconn, ward_patient_id)
        discharge_summaries = ward_services.list_discharge_summaries(dbconn, ward_patient_id)
        discharge_checklist = ward_services.get_discharge_checklist(dbconn, ward_patient_id)
        linked_appointments = patient_identity_service.list_appointments_for_ward_patient(
            dbconn, ward_patient_id
        )
        from gi_platform import lab_propagation
        lab_results = lab_propagation.list_labs_for_patient(dbconn, ward_patient_id=ward_patient_id, limit=30)
        labs_prefill = lab_propagation.format_labs_block(lab_results) if lab_results else ''

        return render_template(
            'ward/patient.html',
            patient=patient,
            admission=admission,
            notes=notes,
            tasks=tasks,
            generated_history=generated_history,
            discharge_summaries=discharge_summaries,
            discharge_checklist=discharge_checklist,
            linked_appointments=linked_appointments,
            lab_results=lab_results,
            labs_prefill=labs_prefill,
        )

    @app.route('/ward/patient/<int:ward_patient_id>/mrn', methods=['POST'])
    @login_required
    @roles_required('admin', 'specialist', 'nurse_manager', 'pg_trainee', 'registrar')
    def ward_patient_update_mrn(ward_patient_id):
        dbconn = get_db()
        mrn = (request.form.get('mrn') or '').strip()
        if not mrn:
            flash('MRN is required.', 'error')
            return redirect(url_for('ward_patient_view', ward_patient_id=ward_patient_id))
        dbconn.execute(
            "UPDATE ward_patient SET mrn = ?, updated_at = datetime('now') WHERE id = ?",
            (mrn, ward_patient_id),
        )
        dbconn.commit()
        from gi_platform import patient_identity_service
        patient = ward_services.get_ward_patient(dbconn, ward_patient_id)
        patient_identity_service.link_identity(
            dbconn,
            mrn=mrn,
            ward_patient_id=ward_patient_id,
            patient_name=(patient['patient_name'] if patient else '') or '',
        )
        flash('MRN saved and identity linked to booking records.', 'success')
        return redirect(url_for('ward_patient_view', ward_patient_id=ward_patient_id))

    @app.route('/ward/patient/<int:ward_patient_id>/note', methods=['POST'])
    @login_required
    @roles_required(*WARD_ACCESS_ROLES)
    def ward_patient_add_note(ward_patient_id):
        dbconn = get_db()
        ward_services.add_clinical_note(
            dbconn,
            ward_patient_id=ward_patient_id,
            note_type=(request.form.get('note_type') or 'progress').strip(),
            body=(request.form.get('body') or '').strip(),
            user_id=getattr(request, 'current_user_id', None),
        )
        from gi_platform import activity_service, patient_journey_service
        uid = getattr(request, 'current_user_id', None)
        activity_service.record_activity(
            dbconn, user_id=uid, activity_type='clinical_note',
            title='Clinical note saved', ward_patient_id=ward_patient_id,
            source_module='ward', source_type='note',
        )
        patient_journey_service.add_event(
            dbconn, event_type='note', title='Clinical note saved',
            ward_patient_id=ward_patient_id, created_by=uid,
            source_module='ward', source_type='note',
        )
        flash('Clinical note saved.', 'success')
        return redirect(url_for('ward_patient_view', ward_patient_id=ward_patient_id))

    @app.route('/ward/bed/<int:bed_id>/ready', methods=['POST'])
    @login_required
    @roles_required('admin', 'specialist', 'nurse_manager', 'staff_nurse')
    def ward_bed_ready(bed_id):
        dbconn = get_db()
        ward_services.mark_bed_ready(dbconn, bed_id)
        flash('Bed marked available.', 'success')
        return redirect(request.referrer or url_for('ward_dashboard'))

    @app.route('/ward/patient/<int:ward_patient_id>/discharge-summary', methods=['POST'])
    @login_required
    @roles_required('admin', 'specialist', 'consultant', 'registrar')
    def ward_discharge_summary(ward_patient_id):
        dbconn = get_db()
        ward_services.save_discharge_summary(
            dbconn,
            ward_patient_id=ward_patient_id,
            summary_text=(request.form.get('summary_text') or '').strip(),
            follow_up_plan=(request.form.get('follow_up_plan') or '').strip(),
            user_id=getattr(request, 'current_user_id', None),
        )
        flash('Discharge summary saved.', 'success')
        return redirect(url_for('ward_patient_view', ward_patient_id=ward_patient_id))

    @app.route('/ward/analytics')
    @login_required
    @roles_required('admin', 'hod', 'consultant', 'specialist', 'nurse_manager')
    def ward_analytics():
        dbconn = get_db()
        wards = ward_services.list_wards(dbconn)
        ward_id = request.args.get('ward_id', type=int) or (wards[0]['id'] if wards else None)
        stats = ward_services.ward_extended_analytics(dbconn, ward_id) if ward_id else {}
        return render_template('ward/analytics.html', wards=wards, ward_id=ward_id, stats=stats)
