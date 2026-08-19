"""Dedicated laboratory module — batch ordering and result entry."""

from flask import flash, jsonify, redirect, render_template, request, session, url_for

from gi_platform import lab_service, score_service
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
    """Group lab orders by test category (e.g. CBC, LFT) — each category appears once,
    with its own list of tests, so the UI can render one collapsible dropdown per category
    instead of repeating the category name on every row."""
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

        orders = lab_service.list_lab_orders(db, ward_patient_id=ward_patient_id)
        results = lab_service.list_lab_results(db, ward_patient_id=ward_patient_id)
        scores = score_service.scores_for_patient(db, ward_patient_id=ward_patient_id)
        catalog = categories_with_tests()
        orders_by_category = _group_orders_by_category(orders)
        return render_template(
            'gi/laboratory.html',
            patient=patient,
            ward_patient_id=ward_patient_id,
            session_id=session_id,
            orders=orders,
            orders_by_category=orders_by_category,
            results=results,
            scores=scores,
            catalog=catalog,
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
