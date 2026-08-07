"""Routes for advanced endoscopy reports (EUS, Capsule, …)."""

from __future__ import annotations

import os

from flask import flash, jsonify, redirect, render_template, request, send_file, url_for

import image_service
import print_service
import qr_service
import report_service
from advanced_reports.clinical_note_policy import (
    is_structured_endoscopy,
    resolve_print_layout,
    sidebar_slot_count,
)
from advanced_reports.configs import PROCEDURE_REGISTRY, get_config
from advanced_reports.print_metadata import build_all_print_images, build_print_images, build_unified_print_rows
from advanced_reports.services import (
    generate_procedure_note,
    get_or_create,
    image_dir,
    parse_payload,
    print_procedure_fields,
    save_report,
)

CAN_ACCESS = ('admin', 'specialist', 'nurse_manager', 'consultant', 'hod')
COLONOSCOPY_ACCESS = CAN_ACCESS + ('registrar', 'general_endoscopy', 'pg_trainee')

from gi_platform.constants import has_full_access

ROLE_ADMIN = 'admin'

# Custom Flask endpoint names (when they differ from {procedure_key}_report_view).
REPORT_VIEW_ENDPOINTS = {
    'upper_gi_v2': 'upper_gi_report_view',
    'colonoscopy_v2': 'colonoscopy_report_view',
}


def _report_view_endpoint(procedure_key: str) -> str:
    return REPORT_VIEW_ENDPOINTS.get(procedure_key, f'{procedure_key}_report_view')


def register_advanced_report_routes(app, *, get_db, login_required, roles_required):
    import advanced_reports.services as svc

    def _cfg_from_report(procedure_key, report_id):
        cfg = get_config(procedure_key)
        db = get_db()
        report = db.execute(f"SELECT * FROM {cfg['table']} WHERE id = ?", (report_id,)).fetchone()
        return cfg, db, report

    def _report_view(procedure_key, appointment_id):
        cfg = get_config(procedure_key)
        db = get_db()
        appt = db.execute('SELECT * FROM appointment WHERE id = ?', (appointment_id,)).fetchone()
        from advanced_reports.services import appointment_matches_procedure
        if not appt or not appointment_matches_procedure(cfg, appt['procedure_type']):
            flash(f'That is not a {cfg["label"]} appointment.', 'error')
            return redirect(url_for('dashboard'))

        from flask import session as flask_session
        user_row = db.execute(
            'SELECT username, role FROM user WHERE id = ?', (flask_session.get('user_id'),)
        ).fetchone()
        username = user_row['username'] if user_row else 'system'

        report, _ = get_or_create(db, procedure_key, appointment_id, username)
        if procedure_key == 'upper_gi_v2':
            from egd_reports.research_sync import ensure_research_row
            ensure_research_row(db, report['id'])
        if procedure_key == 'colonoscopy_v2':
            from colonoscopy_reports.research_sync import ensure_research_row
            ensure_research_row(db, report['id'])
        db.commit()

        images = image_service.list_images(db, cfg['image_table'], 'report_id', report['id'])
        image_by_slot = image_service.index_by_slot(images)
        endoscopists = db.execute(
            'SELECT * FROM endoscopist WHERE is_active = 1 OR id = ? ORDER BY full_name',
            (report['endoscopist_id'] or 0,),
        ).fetchall()
        payload = parse_payload(report['payload_json'])

        from advanced_reports import vocabulary as adv_vocab
        if cfg.get('sedation_options_key') == 'ercp':
            sedation_options = adv_vocab.ERCP_SEDATION
        else:
            sedation_options = adv_vocab.SEDATION_TYPE

        anesthesiologists = []
        if cfg.get('has_anesthesiologist'):
            anesthesiologists = [
                row['anesthesiologist'] for row in db.execute(
                    "SELECT DISTINCT anesthesiologist FROM ercp_report "
                    "WHERE anesthesiologist != '' ORDER BY anesthesiologist"
                ).fetchall()
            ]
            eus_names = [
                row['anesthesiologist'] for row in db.execute(
                    "SELECT DISTINCT anesthesiologist FROM eus_report "
                    "WHERE anesthesiologist != '' ORDER BY anesthesiologist"
                ).fetchall()
            ]
            anesthesiologists = sorted(set(anesthesiologists + eus_names))

        template_extras = {}
        if procedure_key == 'upper_gi_v2':
            template_extras['patient_overview_url'] = url_for(
                'patient_upper_gi_overview', appointment_id=appointment_id,
            )
        if procedure_key == 'colonoscopy_v2':
            template_extras['patient_overview_url'] = url_for(
                'patient_colonoscopy_overview', appointment_id=appointment_id,
            )

        return render_template(
            'advanced_reports/editor.html',
            appt=appt,
            report=report,
            cfg=cfg,
            procedure_key=procedure_key,
            payload=payload,
            image_by_slot=image_by_slot,
            image_slots=range(1, cfg['image_slots'] + 1),
            endoscopists=endoscopists,
            sedation_options=sedation_options,
            anesthesiologists=anesthesiologists,
            is_locked=report_service.is_finalized(report),
            can_unlock=(user_row and has_full_access(user_row['role'])),
            **template_extras,
        )

    @app.route('/eus/<int:appointment_id>')
    @login_required
    @roles_required(*CAN_ACCESS)
    def eus_report_view(appointment_id):
        return _report_view('eus', appointment_id)

    @app.route('/capsule-endoscopy/<int:appointment_id>')
    @login_required
    @roles_required(*CAN_ACCESS)
    def capsule_report_view(appointment_id):
        return _report_view('capsule', appointment_id)

    _registered_views = {'eus', 'capsule', 'upper_gi_v2', 'colonoscopy_v2'}

    @app.route('/upper-gi/<int:appointment_id>', endpoint='upper_gi_report_view')
    @login_required
    @roles_required(*CAN_ACCESS)
    def upper_gi_structured_report_view(appointment_id):
        return _report_view('upper_gi_v2', appointment_id)

    @app.route('/colonoscopy/<int:appointment_id>', endpoint='colonoscopy_report_view')
    @login_required
    @roles_required(*COLONOSCOPY_ACCESS)
    def colonoscopy_structured_report_view(appointment_id):
        return _report_view('colonoscopy_v2', appointment_id)

    for _proc_key, _proc_cfg in PROCEDURE_REGISTRY.items():
        if _proc_key in _registered_views:
            continue

        def _make_view(pk=_proc_key, prefix=_proc_cfg['url_prefix'], ep=f'{_proc_key}_report_view'):
            @app.route(f'/{prefix}/<int:appointment_id>', endpoint=ep)
            @login_required
            @roles_required(*CAN_ACCESS)
            def _dynamic_view(appointment_id, _pk=pk):
                return _report_view(_pk, appointment_id)
            return _dynamic_view

        _make_view()

    def _register_actions(procedure_key):
        cfg = get_config(procedure_key)
        prefix = cfg['url_prefix']
        access_roles = COLONOSCOPY_ACCESS if procedure_key == 'colonoscopy_v2' else CAN_ACCESS

        @app.route(f'/{prefix}/<int:report_id>/save', methods=['POST'], endpoint=f'{procedure_key}_report_save')
        @login_required
        @roles_required(*access_roles)
        def _save(report_id, _pk=procedure_key):
            c = get_config(_pk)
            db = get_db()
            report = db.execute(f"SELECT * FROM {c['table']} WHERE id = ?", (report_id,)).fetchone()
            if not report:
                return jsonify({'error': 'Report not found.'}), 404
            if report_service.is_finalized(report):
                return jsonify({'error': 'Report is finalized and read-only.'}), 403
            payload = request.get_json(force=True, silent=True) or {}
            save_report(db, _pk, report_id, payload)
            db.commit()
            return jsonify({'ok': True})

        @app.route(f'/{prefix}/<int:report_id>/generate-note', methods=['POST'], endpoint=f'{procedure_key}_generate_note')
        @login_required
        @roles_required(*access_roles)
        def _generate_note(report_id, _pk=procedure_key):
            c = get_config(_pk)
            db = get_db()
            report = db.execute(f"SELECT * FROM {c['table']} WHERE id = ?", (report_id,)).fetchone()
            wants_json = (
                request.is_json
                or (request.content_type or '').startswith('application/json')
                or 'application/json' in (request.headers.get('Accept') or '')
            )
            if not report or report_service.is_finalized(report):
                if wants_json:
                    return jsonify({'error': 'Cannot generate note.'}), 403
                flash('Cannot generate note.', 'error')
                return redirect(request.referrer or url_for('dashboard'))

            try:
                body = request.get_json(force=True, silent=True)
                if body:
                    save_report(db, _pk, report_id, body)
                    report = db.execute(f"SELECT * FROM {c['table']} WHERE id = ?", (report_id,)).fetchone()

                note = generate_procedure_note(_pk, report)
                save_report(db, _pk, report_id, {'procedure_note': note})
                db.commit()
            except Exception as exc:
                db.rollback()
                if wants_json:
                    return jsonify({'error': f'Generate failed: {exc}'}), 500
                flash(f'Generate failed: {exc}', 'error')
                return redirect(request.referrer or url_for('dashboard'))

            if wants_json:
                return jsonify({'ok': True, 'procedure_note': note})

            flash('Procedure note generated.', 'success')
            return redirect(request.referrer or url_for('dashboard'))

        @app.route(f'/{prefix}/<int:report_id>/finalize', methods=['POST'], endpoint=f'{procedure_key}_finalize')
        @login_required
        @roles_required(*access_roles)
        def _finalize(report_id, _pk=procedure_key):
            c = get_config(_pk)
            db = get_db()
            report = db.execute(f"SELECT * FROM {c['table']} WHERE id = ?", (report_id,)).fetchone()
            if not report:
                flash('Report not found.', 'error')
                return redirect(url_for('dashboard'))
            if not report['endoscopist_id']:
                flash('Select an endoscopist before finalizing.', 'error')
                return redirect(request.referrer or url_for('dashboard'))
            from flask import session as flask_session
            user_row = db.execute('SELECT username FROM user WHERE id = ?', (flask_session.get('user_id'),)).fetchone()
            report_service.finalize_report(db, c['table'], report_id, user_row['username'])
            db.commit()
            flash('Report finalized.', 'success')
            return redirect(request.referrer or url_for('dashboard'))

        @app.route(f'/{prefix}/<int:report_id>/unlock', methods=['POST'], endpoint=f'{procedure_key}_unlock')
        @login_required
        @roles_required(ROLE_ADMIN)
        def _unlock(report_id, _pk=procedure_key):
            c = get_config(_pk)
            db = get_db()
            from flask import session as flask_session
            user_row = db.execute('SELECT username FROM user WHERE id = ?', (flask_session.get('user_id'),)).fetchone()
            report_service.unlock_report(db, c['table'], report_id, user_row['username'])
            db.commit()
            flash('Report unlocked for editing.', 'success')
            return redirect(request.referrer or url_for('dashboard'))

        @app.route(f'/{prefix}/<int:report_id>/image/<int:slot>', methods=['POST'], endpoint=f'{procedure_key}_image_upload')
        @login_required
        @roles_required(*access_roles)
        def _image_upload(report_id, slot, _pk=procedure_key):
            c = get_config(_pk)
            db = get_db()
            report = db.execute(f"SELECT * FROM {c['table']} WHERE id = ?", (report_id,)).fetchone()
            if not report or report_service.is_finalized(report):
                return jsonify({'error': 'Cannot upload.'}), 403
            file = request.files.get('image')
            if not file:
                return jsonify({'error': 'No image.'}), 400
            from flask import session as flask_session
            user_row = db.execute('SELECT username FROM user WHERE id = ?', (flask_session.get('user_id'),)).fetchone()
            fname = image_service.build_filename('report', report_id, slot)
            dest = os.path.join(image_dir(c), fname)
            image_service.compress_and_save(file, dest, svc.IMAGE_MAX_DIMENSION, svc.IMAGE_JPEG_QUALITY)
            image_service.upsert_image_record(
                db, c['image_table'], 'report_id', report_id, slot, fname, user_row['username'],
            )
            db.commit()
            return jsonify({'ok': True, 'url': url_for(f'{_pk}_image_serve', report_id=report_id, slot=slot)})

        @app.route(f'/{prefix}/<int:report_id>/image/<int:slot>', methods=['GET'], endpoint=f'{procedure_key}_image_serve')
        @login_required
        @roles_required(*access_roles)
        def _image_serve(report_id, slot, _pk=procedure_key):
            c = get_config(_pk)
            db = get_db()
            img = image_service.get_image_record(db, c['image_table'], 'report_id', report_id, slot)
            if not img:
                return '', 404
            path = os.path.join(image_dir(c), img['filename'])
            if not os.path.isfile(path):
                return '', 404
            return send_file(path, mimetype='image/jpeg')

        @app.route(f'/{prefix}/<int:report_id>/image/<int:slot>/delete', methods=['POST'], endpoint=f'{procedure_key}_image_delete')
        @login_required
        @roles_required(*access_roles)
        def _image_delete(report_id, slot, _pk=procedure_key):
            c = get_config(_pk)
            db = get_db()
            report = db.execute(f"SELECT * FROM {c['table']} WHERE id = ?", (report_id,)).fetchone()
            if not report or report_service.is_finalized(report):
                return jsonify({'error': 'Cannot delete.'}), 403
            img = image_service.get_image_record(db, c['image_table'], 'report_id', report_id, slot)
            if img:
                path = os.path.join(image_dir(c), img['filename'])
                if os.path.isfile(path):
                    os.remove(path)
                db.execute(f"DELETE FROM {c['image_table']} WHERE report_id = ? AND slot = ?", (report_id, slot))
                db.commit()
            return jsonify({'ok': True})

        @app.route(f'/{prefix}/<int:report_id>/print', endpoint=f'{procedure_key}_print')
        @login_required
        @roles_required(*access_roles)
        def _print(report_id, _pk=procedure_key):
            c = get_config(_pk)
            db = get_db()
            report = db.execute(f"SELECT * FROM {c['table']} WHERE id = ?", (report_id,)).fetchone()
            if not report:
                flash('Report not found.', 'error')
                return redirect(url_for('dashboard'))
            appt = db.execute('SELECT * FROM appointment WHERE id = ?', (report['appointment_id'],)).fetchone()
            endoscopist = None
            if report['endoscopist_id']:
                endoscopist = db.execute('SELECT * FROM endoscopist WHERE id = ?', (report['endoscopist_id'],)).fetchone()
            images = image_service.list_images(db, c['image_table'], 'report_id', report['id'])
            slots = image_service.ordered_slots(images, c['image_slots'])
            payload = parse_payload(report['payload_json'])
            image_slots_data = [
                {
                    'slot': slot,
                    'url': url_for(f'{_pk}_image_serve', report_id=report_id, slot=slot) if img else None,
                }
                for slot, img in slots
            ]
            procedure_fields = print_procedure_fields(_pk, report)
            sedation_display = (report['sedation'] or '').strip()
            if not sedation_display:
                for label, value in procedure_fields:
                    if label == 'Sedation':
                        sedation_display = value
                        break
            uploaded_count = sum(1 for _, img in slots if img)
            url_for_image = lambda slot: url_for(
                f'{_pk}_image_serve', report_id=report_id, slot=slot,
            )
            print_layout = resolve_print_layout(_pk, c, uploaded_count)
            sidebar_images = []
            print_image_items = []
            if print_layout == 'sidebar_images':
                sidebar_images, _ = build_print_images(
                    slots,
                    payload,
                    sidebar_max=sidebar_slot_count(c),
                    url_for_image=url_for_image,
                )
            elif is_structured_endoscopy(_pk, c) and uploaded_count >= 5:
                print_image_items = build_all_print_images(
                    slots, payload, url_for_image=url_for_image,
                )
            report_number = report_service.generate_report_number(c['report_prefix'], report['id'])
            # EGD: always regenerate — old drafts may contain label-dump notes.
            if _pk in ('upper_gi_v2', 'colonoscopy_v2') or c.get('table') in (
                'upper_gi_v2_report', 'colonoscopy_v2_report',
            ):
                note = generate_procedure_note(_pk, report)
            else:
                note = report['procedure_note'] or generate_procedure_note(_pk, report)
            assistants_lines = print_service.split_team_names(report['assistants'])
            unified_print_rows = None
            if is_structured_endoscopy(_pk, c):
                unified_print_rows = build_unified_print_rows(
                    _pk, report, appt, c, assistants_lines=assistants_lines,
                )
            view_endpoint = _report_view_endpoint(_pk)
            qr_url = url_for(view_endpoint, appointment_id=report['appointment_id'], _external=True)
            qr_result = qr_service.generate_for_print(qr_url)
            qr_data_uri = qr_result.get('data_uri') or ''
            qr_fallback_url = qr_result.get('fallback_url') or ''
            return render_template(
                'advanced_reports/print.html',
                appt=appt,
                report=report,
                cfg=c,
                procedure_key=_pk,
                endoscopist=endoscopist,
                report_number=report_number,
                procedure_fields=procedure_fields,
                note_text=note,
                image_slots=slots,
                image_slots_data=image_slots_data,
                sidebar_images=sidebar_images,
                print_image_items=print_image_items,
                print_layout=print_layout,
                unified_print_rows=unified_print_rows,
                sedation_display=sedation_display,
                assistants_lines=assistants_lines,
                qr_data_uri=qr_data_uri,
                qr_fallback_url=qr_fallback_url,
                codes_caption='Scan to open report',
            )

    for key in PROCEDURE_REGISTRY:
        _register_actions(key)
