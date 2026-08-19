"""Colonoscopy routes — registry, patient overview, follow-up API."""

from __future__ import annotations

from datetime import datetime

from flask import flash, jsonify, redirect, render_template, request, send_file, url_for

import session_service
from advanced_reports.services import parse_payload
from colonoscopy_reports.registry import build_registry_export, get_registry_rows
from gi_platform.constants import has_full_access

CAN_ACCESS = ('admin', 'specialist', 'nurse_manager', 'consultant', 'hod', 'registrar', 'general_endoscopy', 'pg_trainee')
ROLE_ADMIN = 'admin'


def register_colonoscopy_routes(app, *, get_db, login_required, roles_required):
    @app.route('/colonoscopy/research-registry')
    @login_required
    @roles_required(*CAN_ACCESS)
    def colonoscopy_research_registry():
        start_str = request.args.get('start', '')
        end_str = request.args.get('end', '')
        rows = None
        error = None
        if start_str and end_str:
            try:
                start_d = datetime.strptime(start_str, '%Y-%m-%d').date()
                end_d = datetime.strptime(end_str, '%Y-%m-%d').date()
                if end_d < start_d:
                    error = 'End date must be on or after start date.'
                else:
                    rows = get_registry_rows(get_db(), start_d.isoformat(), end_d.isoformat())
            except ValueError:
                error = 'Invalid date format.'
        return render_template(
            'colonoscopy/research_registry.html',
            rows=rows, start=start_str, end=end_str, error=error,
        )

    @app.route('/colonoscopy/research-registry/export')
    @login_required
    @roles_required(*CAN_ACCESS)
    def colonoscopy_research_registry_export():
        start_str = request.args.get('start', '')
        end_str = request.args.get('end', '')
        if not start_str or not end_str:
            flash('Select a date range first.', 'error')
            return redirect(url_for('colonoscopy_research_registry'))
        try:
            start_d = datetime.strptime(start_str, '%Y-%m-%d').date()
            end_d = datetime.strptime(end_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Invalid date format.', 'error')
            return redirect(url_for('colonoscopy_research_registry'))
        rows = get_registry_rows(get_db(), start_d.isoformat(), end_d.isoformat())
        wb = build_registry_export(rows)
        from io import BytesIO
        buf = BytesIO()
        wb.save(buf)
        buf.seek(0)
        filename = f'colonoscopy_registry_{datetime.utcnow().strftime("%Y%m%d_%H%M%S")}.xlsx'
        return send_file(
            buf,
            as_attachment=True,
            download_name=filename,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )

    @app.route('/patient-colonoscopy-overview/<int:appointment_id>')
    @login_required
    @roles_required(*CAN_ACCESS)
    def patient_colonoscopy_overview(appointment_id):
        db = get_db()
        appt = db.execute('SELECT * FROM appointment WHERE id = ?', (appointment_id,)).fetchone()
        from advanced_reports.configs import get_config
        from advanced_reports.services import appointment_matches_procedure
        cfg = get_config('colonoscopy_v2')
        if not appt or not appointment_matches_procedure(cfg, appt['procedure_type']):
            flash('Not a colonoscopy / polypectomy appointment.', 'error')
            return redirect(url_for('dashboard'))
        mrn = (appt['mrn'] or '').strip()
        sessions_raw = session_service.list_sessions_for_types(
            db, ('colonoscopy', 'polypectomy'), mrn, fallback_row=appt,
        )
        session_map = session_service.number_sessions(sessions_raw)
        sessions = []
        timeline_events = []

        for s in sessions_raw:
            report = db.execute(
                'SELECT * FROM colonoscopy_v2_report WHERE appointment_id = ?', (s['id'],)
            ).fetchone()
            endoscopist_name = None
            indication = ''
            if report:
                if report['endoscopist_id']:
                    e = db.execute(
                        'SELECT full_name FROM endoscopist WHERE id = ?', (report['endoscopist_id'],)
                    ).fetchone()
                    endoscopist_name = e['full_name'] if e else None
                payload = parse_payload(report['payload_json'])
                indication = payload.get('indication_category') or payload.get('indication_detail') or ''
                if isinstance(indication, list):
                    indication = ', '.join(indication)
            followups = []
            if report:
                followups = db.execute(
                    'SELECT * FROM colonoscopy_followup WHERE report_id = ? ORDER BY followup_date, id',
                    (report['id'],),
                ).fetchall()
            sn = session_map.get(s['id'], 1)
            sessions.append({
                'appointment': s,
                'report': report,
                'followups': followups,
                'session_number': sn,
                'endoscopist_name': endoscopist_name,
            })
            timeline_events.append({
                'type': 'session',
                'date': s['appointment_date'],
                'session_number': sn,
                'appointment_id': s['id'],
                'report_id': report['id'] if report else None,
                'status': report['status'] if report else None,
                'indication': indication,
                'endoscopist_name': endoscopist_name,
            })
            for fu in followups:
                timeline_events.append({
                    'type': 'followup',
                    'date': fu['followup_date'] or s['appointment_date'],
                    'session_number': sn,
                    'followup': fu,
                })

        timeline_events.sort(key=lambda e: (e['date'], 0 if e['type'] == 'session' else 1))
        latest_session = sessions[-1] if sessions else None
        return render_template(
            'colonoscopy/patient_overview.html',
            appt=appt,
            mrn=mrn,
            sessions=sessions,
            timeline_events=timeline_events,
            has_linked_history=bool(mrn),
            latest_session=latest_session,
            followup_module='colonoscopy',
        )

    def _followup_row_json(row):
        return {k: row[k] for k in row.keys()}

    @app.route('/api/colonoscopy/<int:report_id>/followups')
    @login_required
    @roles_required(*CAN_ACCESS)
    def colonoscopy_followups_list(report_id):
        rows = get_db().execute(
            'SELECT * FROM colonoscopy_followup WHERE report_id = ? ORDER BY followup_date, id',
            (report_id,),
        ).fetchall()
        return jsonify({'followups': [_followup_row_json(r) for r in rows]})

    @app.route('/api/colonoscopy/<int:report_id>/followups', methods=['POST'])
    @login_required
    @roles_required(*CAN_ACCESS)
    def colonoscopy_followup_create(report_id):
        db = get_db()
        from flask import session as flask_session
        user_row = db.execute(
            'SELECT username FROM user WHERE id = ?', (flask_session.get('user_id'),)
        ).fetchone()
        username = user_row['username'] if user_row else 'system'
        now = datetime.utcnow().isoformat()
        data = request.get_json(force=True, silent=True) or {}
        cur = db.execute(
            """
            INSERT INTO colonoscopy_followup (
                report_id, followup_date, clinical_notes, histopathology_result,
                lab_results, imaging_results, clinical_status, outcome,
                management_plan, free_notes, created_by, created_at, updated_by, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                report_id,
                (data.get('followup_date') or '').strip(),
                (data.get('clinical_notes') or '').strip(),
                (data.get('histopathology_result') or '').strip(),
                (data.get('lab_results') or '').strip(),
                (data.get('imaging_results') or '').strip(),
                (data.get('clinical_status') or '').strip(),
                (data.get('outcome') or '').strip(),
                (data.get('management_plan') or '').strip(),
                (data.get('free_notes') or '').strip(),
                username, now, username, now,
            ),
        )
        db.commit()
        new_row = db.execute(
            'SELECT * FROM colonoscopy_followup WHERE id = ?', (cur.lastrowid,)
        ).fetchone()
        return jsonify(_followup_row_json(new_row)), 201

    @app.route('/api/colonoscopy-followup/<int:followup_id>', methods=['PUT'])
    @login_required
    @roles_required(*CAN_ACCESS)
    def colonoscopy_followup_update(followup_id):
        db = get_db()
        row = db.execute(
            'SELECT * FROM colonoscopy_followup WHERE id = ?', (followup_id,)
        ).fetchone()
        if not row:
            return jsonify({'error': 'Not found'}), 404
        from flask import session as flask_session
        user_row = db.execute(
            'SELECT username FROM user WHERE id = ?', (flask_session.get('user_id'),)
        ).fetchone()
        username = user_row['username'] if user_row else 'system'
        now = datetime.utcnow().isoformat()
        data = request.get_json(force=True, silent=True) or {}
        db.execute(
            """
            UPDATE colonoscopy_followup SET
                followup_date=?, clinical_notes=?, histopathology_result=?,
                lab_results=?, imaging_results=?, clinical_status=?, outcome=?,
                management_plan=?, free_notes=?, updated_by=?, updated_at=?
            WHERE id=?
            """,
            (
                (data.get('followup_date') or row['followup_date']).strip(),
                (data.get('clinical_notes') or '').strip(),
                (data.get('histopathology_result') or '').strip(),
                (data.get('lab_results') or '').strip(),
                (data.get('imaging_results') or '').strip(),
                (data.get('clinical_status') or '').strip(),
                (data.get('outcome') or '').strip(),
                (data.get('management_plan') or '').strip(),
                (data.get('free_notes') or '').strip(),
                username, now, followup_id,
            ),
        )
        db.commit()
        updated = db.execute(
            'SELECT * FROM colonoscopy_followup WHERE id = ?', (followup_id,)
        ).fetchone()
        return jsonify(_followup_row_json(updated))

    @app.route('/api/colonoscopy-followup/<int:followup_id>', methods=['DELETE'])
    @login_required
    @roles_required(*CAN_ACCESS)
    def colonoscopy_followup_delete(followup_id):
        db = get_db()
        row = db.execute(
            'SELECT * FROM colonoscopy_followup WHERE id = ?', (followup_id,)
        ).fetchone()
        if not row:
            return jsonify({'error': 'Not found'}), 404
        db.execute('DELETE FROM colonoscopy_followup WHERE id = ?', (followup_id,))
        db.commit()
        return jsonify({'ok': True})
