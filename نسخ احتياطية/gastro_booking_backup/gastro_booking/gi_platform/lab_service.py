"""Laboratory orders and results — batch ordering, result entry, smart scoring trigger."""

from __future__ import annotations

from datetime import date

from gi_platform.lab_catalog import get_test


def create_lab_orders(
    db,
    *,
    test_codes: list[str],
    session_id: int | None = None,
    ward_patient_id: int | None = None,
    created_by: int | None = None,
    notes: str = '',
) -> list[int]:
    """Create multiple lab orders in one batch."""
    from gi_platform import order_service

    ids: list[int] = []
    approval = order_service.initial_approval_status('lab')
    for code in test_codes:
        test = get_test(code)
        if not test:
            continue
        db.execute(
            """
            INSERT INTO gi_investigation_order
            (session_id, ward_patient_id, order_type, item_code, item_name, category,
             custom_note, created_by, approval_status, status)
            VALUES (?, ?, 'lab', ?, ?, ?, ?, ?, ?, 'pending')
            """,
            (session_id, ward_patient_id, test.code, test.name, test.category,
             notes or None, created_by, approval),
        )
        ids.append(db.execute('SELECT last_insert_rowid() AS id').fetchone()['id'])
    if ids:
        db.commit()
        if ward_patient_id:
            from gi_platform import workforce_service
            names = [get_test(c).name for c in test_codes if get_test(c)]
            workforce_service.create_task(
                db, ward_patient_id=ward_patient_id, task_type='labs',
                title=f'Laboratory batch ({len(ids)} tests)',
                assigned_role='house_officer',
                notes='; '.join(names[:8]) + ('…' if len(names) > 8 else ''),
                created_by=created_by,
            )
    return ids


def list_lab_orders(
    db,
    *,
    ward_patient_id: int | None = None,
    session_id: int | None = None,
    status: str | None = None,
) -> list:
    sql = """
        SELECT o.*, u.full_name AS ordered_by_name
        FROM gi_investigation_order o
        LEFT JOIN user u ON u.id = o.created_by
        WHERE o.order_type = 'lab'
    """
    params: list = []
    if ward_patient_id:
        sql += ' AND o.ward_patient_id = ?'
        params.append(ward_patient_id)
    if session_id:
        sql += ' AND o.session_id = ?'
        params.append(session_id)
    if status:
        sql += ' AND o.status = ?'
        params.append(status)
    sql += ' ORDER BY o.created_at DESC'
    return db.execute(sql, params).fetchall()


def enter_lab_result(
    db,
    *,
    order_id: int | None = None,
    test_code: str = '',
    test_name: str = '',
    result_value: str,
    result_unit: str = '',
    reference_range: str = '',
    result_date: str = '',
    comments: str = '',
    attachment_path: str = '',
    ward_patient_id: int | None = None,
    session_id: int | None = None,
    recorded_by: int | None = None,
) -> int:
    test = get_test(test_code) if test_code else None
    if test:
        test_name = test_name or test.name
        result_unit = result_unit or test.unit
        reference_range = reference_range or test.ref_range
        test_code = test.code
    if not test_name:
        raise ValueError('Test name required')

    if order_id:
        order = db.execute('SELECT * FROM gi_investigation_order WHERE id = ?', (order_id,)).fetchone()
        if order:
            ward_patient_id = ward_patient_id or order['ward_patient_id']
            session_id = session_id or order['session_id']
            test_code = test_code or order['item_code'] or ''
            test_name = test_name or order['item_name']
            db.execute(
                "UPDATE gi_investigation_order SET status = 'completed' WHERE id = ?",
                (order_id,),
            )

    if not result_date:
        result_date = date.today().isoformat()

    cur = db.execute(
        """
        INSERT INTO gi_lab_result
        (ward_patient_id, session_id, order_id, test_code, test_name,
         result_value, result_unit, reference_range, result_date, status,
         comments, attachment_path, recorded_by)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'completed', ?, ?, ?)
        """,
        (ward_patient_id, session_id, order_id, test_code or None, test_name,
         result_value, result_unit or None, reference_range or None, result_date,
         comments or None, attachment_path or None, recorded_by),
    )
    result_id = cur.lastrowid

    from gi_platform import patient_journey_service
    mrn = ''
    if ward_patient_id:
        wp = db.execute('SELECT mrn FROM ward_patient WHERE id = ?', (ward_patient_id,)).fetchone()
        mrn = wp['mrn'] if wp else ''
    patient_journey_service.add_event(
        db, event_type='investigation_result',
        title=f'Lab result: {test_name} = {result_value}',
        ward_patient_id=ward_patient_id, mrn=mrn, created_by=recorded_by,
        source_module='laboratory', source_id=result_id,
        details={'test_code': test_code, 'value': result_value, 'unit': result_unit},
    )
    db.commit()

    from gi_platform import lab_propagation
    lab_propagation.after_lab_result_saved(
        db,
        ward_patient_id=ward_patient_id,
        session_id=session_id,
        result_id=result_id,
        recalculate_scores=True,
    )
    return result_id


def list_lab_results(
    db,
    *,
    ward_patient_id: int | None = None,
    session_id: int | None = None,
) -> list:
    if ward_patient_id:
        return db.execute(
            'SELECT * FROM gi_lab_result WHERE ward_patient_id = ? ORDER BY result_date DESC, recorded_at DESC',
            (ward_patient_id,),
        ).fetchall()
    if session_id:
        return db.execute(
            'SELECT * FROM gi_lab_result WHERE session_id = ? ORDER BY result_date DESC, recorded_at DESC',
            (session_id,),
        ).fetchall()
    return []


def pending_orders_with_results(db, ward_patient_id: int) -> list[dict]:
    orders = list_lab_orders(db, ward_patient_id=ward_patient_id, status='pending')
    out = []
    for o in orders:
        out.append(dict(o))
    return out


def trend_series(db, *, ward_patient_id: int, min_points: int = 2) -> list[dict]:
    """Group this patient's numeric lab results by test into chart-ready series.

    Only tests with at least ``min_points`` numeric results are included —
    a single value has nothing to trend. Non-numeric results (e.g. free-text
    findings) are silently skipped rather than breaking the chart.
    """
    rows = list_lab_results(db, ward_patient_id=ward_patient_id)
    by_test: dict[str, dict] = {}
    for r in rows:
        r = dict(r)
        name = (r.get('test_name') or r.get('test_code') or '').strip()
        raw_value = (r.get('result_value') or '').strip()
        date = (r.get('result_date') or (r.get('recorded_at') or '')[:10] or '').strip()
        if not name or not date:
            continue
        try:
            value = float(raw_value)
        except (TypeError, ValueError):
            continue
        entry = by_test.setdefault(name, {
            'test_name': name,
            'unit': (r.get('result_unit') or '').strip(),
            'points': [],
        })
        entry['points'].append({'date': date, 'value': value})

    series = []
    for entry in by_test.values():
        entry['points'].sort(key=lambda p: p['date'])
        if len(entry['points']) >= min_points:
            series.append(entry)
    series.sort(key=lambda s: s['test_name'].lower())
    return series
