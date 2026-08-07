"""Upper GI and Colonoscopy report routes — registered via migration_bootstrap."""

from __future__ import annotations

from flask import flash, jsonify, redirect, render_template, request, url_for

import report_service
from gi_platform.constants import has_full_access
from procedure_reports import services as pr_services


CAN_ACCESS = (
    'admin', 'hod', 'consultant', 'specialist', 'registrar', 'general_endoscopy',
    'endoscopy_staff', 'pg_trainee',
)


def register_procedure_report_routes(app, *, get_db, login_required, roles_required):
    def _report_view(procedure_key, appointment_id):
        db = get_db()
        cfg = pr_services.get_config(procedure_key)
        appt = db.execute('SELECT * FROM appointment WHERE id = ?', (appointment_id,)).fetchone()
        if not appt or appt['procedure_type'] != cfg['procedure_type']:
            flash(f'That is not a {cfg["label"]} appointment.', 'error')
            return redirect(url_for('dashboard'))
        from flask import session as flask_session
        user_row = db.execute(
            'SELECT username, role FROM user WHERE id = ?', (flask_session.get('user_id'),)
        ).fetchone()
        username = user_row['username'] if user_row else 'system'
        report, _ = pr_services.get_or_create(db, procedure_key, appointment_id, username)
        db.commit()
        endoscopists = db.execute(
            'SELECT * FROM endoscopist WHERE is_active = 1 OR id = ? ORDER BY full_name',
            (report['endoscopist_id'] or 0,),
        ).fetchall()
        tpl = f'procedure_reports/{procedure_key}_report.html'
        return render_template(
            tpl, appt=appt, report=report, endoscopists=endoscopists,
            procedure_label=cfg['label'], procedure_key=procedure_key,
            is_locked=report_service.is_finalized(report),
            can_unlock=(user_row and has_full_access(user_row['role'])),
        )

    @app.route('/procedure-reports/upper-gi/<int:appointment_id>')
    @login_required
    @roles_required(*CAN_ACCESS)
    def legacy_upper_gi_report_view(appointment_id):
        """Legacy Phase-8 simple report — kept for old data only; UI links to /upper-gi/."""
        return _report_view('upper_gi', appointment_id)

    @app.route('/procedure-reports/colonoscopy/<int:appointment_id>', endpoint='legacy_colonoscopy_report_view')
    @login_required
    @roles_required(*CAN_ACCESS)
    def legacy_colonoscopy_report_view(appointment_id):
        """Legacy Phase-8 simple report — kept for old data only; UI links to /colonoscopy/."""
        return _report_view('colonoscopy', appointment_id)

    @app.route('/procedure-reports/<procedure_key>/<int:report_id>/save', methods=['POST'])
    @login_required
    @roles_required(*CAN_ACCESS)
    def procedure_report_save(procedure_key, report_id):
        if procedure_key not in pr_services.PROCEDURE_CONFIG:
            return jsonify({'error': 'Unknown procedure'}), 404
        db = get_db()
        cfg = pr_services.get_config(procedure_key)
        report = db.execute(f"SELECT * FROM {cfg['table']} WHERE id = ?", (report_id,)).fetchone()
        if not report:
            return jsonify({'error': 'Report not found'}), 404
        if report_service.is_finalized(report):
            return jsonify({'error': 'Report is finalized.'}), 403
        payload = request.get_json(force=True, silent=True) or request.form.to_dict()
        pr_services.save_report(db, procedure_key, report_id, payload)
        return jsonify({'ok': True})

    @app.route('/procedure-reports/<procedure_key>/<int:report_id>/generate-note', methods=['POST'])
    @login_required
    @roles_required(*CAN_ACCESS)
    def procedure_report_generate_note(procedure_key, report_id):
        db = get_db()
        cfg = pr_services.get_config(procedure_key)
        report = db.execute(f"SELECT * FROM {cfg['table']} WHERE id = ?", (report_id,)).fetchone()
        if not report or report_service.is_finalized(report):
            flash('Cannot generate note.', 'error')
            return redirect(request.referrer or url_for('dashboard'))
        note = pr_services.generate_note(procedure_key, report)
        pr_services.save_report(db, procedure_key, report_id, {'procedure_note': note})
        flash('Procedure note generated.', 'success')
        return redirect(request.referrer or url_for('dashboard'))

    @app.route('/procedure-reports/<procedure_key>/<int:report_id>/finalize', methods=['POST'])
    @login_required
    @roles_required(*CAN_ACCESS)
    def procedure_report_finalize(procedure_key, report_id):
        db = get_db()
        cfg = pr_services.get_config(procedure_key)
        report = db.execute(f"SELECT * FROM {cfg['table']} WHERE id = ?", (report_id,)).fetchone()
        if not report:
            flash('Report not found.', 'error')
            return redirect(url_for('dashboard'))
        from flask import session as flask_session
        user_row = db.execute('SELECT username FROM user WHERE id = ?', (flask_session.get('user_id'),)).fetchone()
        report_service.finalize_report(db, cfg['table'], report_id, user_row['username'])
        db.commit()
        flash('Report finalized.', 'success')
        return redirect(request.referrer or url_for('dashboard'))

    @app.route('/procedure-reports/<procedure_key>/<int:report_id>/print')
    @login_required
    @roles_required(*CAN_ACCESS)
    def procedure_report_print(procedure_key, report_id):
        db = get_db()
        cfg = pr_services.get_config(procedure_key)
        report = db.execute(f"SELECT * FROM {cfg['table']} WHERE id = ?", (report_id,)).fetchone()
        if not report:
            flash('Report not found.', 'error')
            return redirect(url_for('dashboard'))
        appt = db.execute('SELECT * FROM appointment WHERE id = ?', (report['appointment_id'],)).fetchone()
        return render_template(
            'procedure_reports/print.html',
            report=report, appt=appt, procedure_label=cfg['label'],
            note_text=report['procedure_note'] or pr_services.generate_note(procedure_key, report),
        )
