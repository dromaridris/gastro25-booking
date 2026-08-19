"""Dedicated laboratory module — batch ordering and result entry."""

from flask import flash, jsonify, redirect, render_template, request, session, url_for

from gi_platform import lab_service, score_service
from gi_platform import lab_catalog
from gi_platform.lab_catalog import categories_with_tests, search_tests

CLINICAL_ROLES = (
    'admin', 'hod', 'consultant', 'specialist', 'registrar', 'general_endoscopy',
    'house_officer', 'pg_trainee', 'nurse_manager', 'staff_nurse',
)


def _ensure_session(db, ward_patient_id: int, user_id: int | None) -> int:
    from gi_platform import history_service
    row = db.execute(
        """
        SELECT id FROM gi_history_session
        WHERE ward_patient_id = ? AND status = 'open'
        ORDER BY id DESC LIMIT 1
        """,
        (ward_patient_id,),
    ).fetchone()
    if row:
        return row['id']
    return history_service.create_session(
        db, ward_patient_id=ward_patient_id, created_by=user_id,
        chief_complaint='Laboratory workup',
    )


def _group_orders_by_category(orders) -> list[dict]:
    """Group lab orders by test category (e.g. CBC, LFT) so the 'Requested
    tests' UI can render one collapsible dropdown per category instead of
    repeating the category name on every row."""
    groups: dict[str, dict] = {}
    order_index: list[str] = []
    for o in orders:
        label = (o['category'] if o['category'] else 'Other').strip() or 'Other'
        if label not in groups:
            groups[label] = {'category': label, 'items': [], 'pending_count': 0}
            order_index.append(label)
        groups[label]['items'].append(o)
        if o['status'] == 'pending':
            groups[label]['pending_count'] += 1
    return [groups[label] for label in order_index]


def register_laboratory_routes(app, *, get_db, login_required, roles_required):
    @app.route('/laboratory/patient/<int:ward_patient_id>', methods=['GET', 'POST'])
    @login_required
    @roles_required(*CLINICAL_ROLES)
    def gi_laboratory_patient(ward_patient_id):
        db = get_db()
        patient = db.execute('SELECT * FROM ward_patient WHERE id = ?', (ward_patient_id,)).fetchone()
        if not patient:
            flash('Patient not found.', 'error')
            return redirect(url_for('ward_dashboard'))

        session_id = _ensure_session(db, ward_patient_id, session.get('user_id'))

        if request.method == 'POST':
            action = (request.form.get('action') or 'order').strip()
            if action == 'order':
                raw = (request.form.get('selected_tests') or '').strip()
                codes = [c.strip() for c in raw.split(',') if c.strip()]
                if not codes:
                    flash('Select at least one investigation.', 'error')
                else:
                    ids = lab_service.create_lab_orders(
                        db, test_codes=codes, session_id=session_id,
                        ward_patient_id=ward_patient_id, created_by=session.get('user_id'),
                        notes=(request.form.get('order_notes') or '').strip(),
                    )
                    flash(f'{len(ids)} laboratory investigation(s) ordered.', 'success')
                return redirect(url_for('gi_laboratory_patient', ward_patient_id=ward_patient_id))

            if action == 'result':
                try:
                    lab_service.enter_lab_result(
                        db,
                        order_id=request.form.get('order_id', type=int),
                        test_code=(request.form.get('test_code') or '').strip(),
                        test_name=(request.form.get('test_name') or '').strip(),
                        result_value=(request.form.get('result_value') or '').strip(),
                        result_unit=(request.form.get('result_unit') or '').strip(),
                        reference_range=(request.form.get('reference_range') or '').strip(),
                        result_date=(request.form.get('result_date') or '').strip(),
                        comments=(request.form.get('comments') or '').strip(),
                        ward_patient_id=ward_patient_id,
                        session_id=session_id,
                        recorded_by=session.get('user_id'),
                    )
                    flash('Result saved — relevant scores recalculated automatically.', 'success')
                except ValueError as exc:
                    flash(str(exc), 'error')
                return redirect(url_for('gi_laboratory_patient', ward_patient_id=ward_patient_id))

            if action == 'result_panel':
                # One panel (e.g. CBC) entered as many individual results in
                # one submit — each filled field becomes its own gi_lab_result
                # row (so each parameter trends independently), while the one
                # originating order (if any) is marked completed once.
                order_id = request.form.get('order_id', type=int)
                result_date = (request.form.get('result_date') or '').strip()
                saved = 0
                for key in request.form:
                    if not key.startswith('field__'):
                        continue
                    value = (request.form.get(key) or '').strip()
                    if not value:
                        continue
                    code = key[len('field__'):]
                    try:
                        lab_service.enter_lab_result(
                            db,
                            order_id=order_id,
                            test_code=code,
                            result_value=value,
                            result_date=result_date,
                            ward_patient_id=ward_patient_id,
                            session_id=session_id,
                            recorded_by=session.get('user_id'),
                        )
                        saved += 1
                    except ValueError:
                        continue
                if saved:
                    flash(f'{saved} panel result(s) saved — relevant scores recalculated automatically.', 'success')
                else:
                    flash('No values entered — nothing was saved.', 'error')
                return redirect(url_for('gi_laboratory_patient', ward_patient_id=ward_patient_id))

            if action == 'result_table':
                # Unified "lab-report style" entry: one row per test across
                # every pending order (panels already expanded), submitted
                # together in a single screen instead of one dropdown+type
                # cycle per test.
                order_ids = request.form.getlist('row_order_id')
                codes = request.form.getlist('row_code')
                names = request.form.getlist('row_name')
                units = request.form.getlist('row_unit')
                ranges = request.form.getlist('row_range')
                values = request.form.getlist('row_value')
                result_date = (request.form.get('result_date') or '').strip()
                saved = 0
                for i, value in enumerate(values):
                    value = (value or '').strip()
                    if not value:
                        continue
                    try:
                        lab_service.enter_lab_result(
                            db,
                            order_id=int(order_ids[i]) if i < len(order_ids) and order_ids[i] else None,
                            test_code=codes[i] if i < len(codes) else '',
                            test_name=names[i] if i < len(names) else '',
                            result_value=value,
                            result_unit=units[i] if i < len(units) else '',
                            reference_range=ranges[i] if i < len(ranges) else '',
                            result_date=result_date,
                            ward_patient_id=ward_patient_id,
                            session_id=session_id,
                            recorded_by=session.get('user_id'),
                        )
                        saved += 1
                    except (ValueError, IndexError):
                        continue
                if saved:
                    flash(f'{saved} result(s) saved — relevant scores recalculated automatically.', 'success')
                else:
                    flash('No values entered — nothing was saved.', 'error')
                return redirect(url_for('gi_laboratory_patient', ward_patient_id=ward_patient_id))

        orders = lab_service.list_lab_orders(db, ward_patient_id=ward_patient_id)
        results = lab_service.list_lab_results(db, ward_patient_id=ward_patient_id)
        scores = score_service.scores_for_patient(db, ward_patient_id=ward_patient_id)
        catalog = categories_with_tests()
        panels = lab_catalog.panels_for_template()
        trend_series = lab_service.trend_series(db, ward_patient_id=ward_patient_id)

        # One row per test for every PENDING order — panels (CBC/LFT/U&E/
        # Coag) expand into their member tests; a single catalogued test
        # keeps its own unit/reference range; free-text (no catalog match)
        # AI-suggested items get one row with blank, still-editable unit/range.
        result_rows = []
        for o in orders:
            if o['status'] != 'pending':
                continue
            panel = lab_catalog.find_panel(f"{o['item_name']} {o['item_code'] or ''}")
            panel_key = None
            if panel:
                # Recover the panel's dict key by identity. If find_panel()
                # ever returns a panel object that isn't literally the same
                # object stored in PANELS (e.g. a copy), this lookup finds
                # nothing — fall through to the single-row branch below
                # instead of crashing the whole page with StopIteration.
                panel_key = next(
                    (k for k, v in lab_catalog.PANELS.items() if v is panel),
                    None,
                )
            if panel and panel_key is not None:
                for f in lab_catalog.panel_fields(panel_key):
                    result_rows.append({
                        'order_id': o['id'], 'code': f.code, 'name': f.name,
                        'unit': f.unit, 'range': f.ref_range, 'group': panel['label'],
                    })
                continue
            catalog_test = lab_catalog.LAB_BY_CODE.get(o['item_code'] or '')
            result_rows.append({
                'order_id': o['id'],
                'code': o['item_code'] or '',
                'name': o['item_name'],
                'unit': catalog_test.unit if catalog_test else '',
                'range': catalog_test.ref_range if catalog_test else '',
                'group': None,
            })

        orders_by_category = _group_orders_by_category(orders)

        return render_template(
            'gi/laboratory.html',
            patient=patient,
            ward_patient_id=ward_patient_id,
            panels=panels,
            result_rows=result_rows,
            session_id=session_id,
            orders=orders,
            orders_by_category=orders_by_category,
            results=results,
            scores=scores,
            catalog=catalog,
            trend_series=trend_series,
        )

    @app.route('/api/laboratory/search')
    @login_required
    @roles_required(*CLINICAL_ROLES)
    def gi_laboratory_search():
        q = (request.args.get('q') or '').strip()
        category = (request.args.get('category') or '').strip()
        tests = search_tests(q, category=category, limit=80)
        return jsonify([
            {'code': t.code, 'name': t.name, 'category': t.category,
             'unit': t.unit, 'ref_range': t.ref_range}
            for t in tests
        ])

    @app.route('/laboratory/patient/<int:ward_patient_id>/recalculate-scores', methods=['POST'])
    @login_required
    @roles_required(*CLINICAL_ROLES)
    def gi_laboratory_recalc_scores(ward_patient_id):
        db = get_db()
        session_id = _ensure_session(db, ward_patient_id, session.get('user_id'))
        score_service.auto_calculate_and_store(
            db, ward_patient_id=ward_patient_id, session_id=session_id,
        )
        flash('Clinical scores recalculated from available data.', 'success')
        return redirect(url_for('gi_laboratory_patient', ward_patient_id=ward_patient_id))
