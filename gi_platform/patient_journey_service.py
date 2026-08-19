"""Patient journey timeline — links ward, procedures, labs, research."""

from __future__ import annotations

import json

from gi_platform.constants import JOURNEY_EVENT_TYPES


def add_event(
    db, *,
    event_type: str,
    title: str,
    ward_patient_id: int | None = None,
    appointment_id: int | None = None,
    mrn: str = '',
    patient_name: str = '',
    details: dict | None = None,
    created_by: int | None = None,
    source_module: str = '',
    source_id: int | None = None,
) -> int:
    if ward_patient_id and (not mrn or not patient_name):
        wp = db.execute(
            'SELECT mrn, patient_name FROM ward_patient WHERE id = ?', (ward_patient_id,)
        ).fetchone()
        if wp:
            mrn = mrn or (wp['mrn'] or '')
            patient_name = patient_name or (wp['patient_name'] or '')

    cur = db.execute(
        """
        INSERT INTO gi_journey_event
        (ward_patient_id, appointment_id, mrn, patient_name, event_type, title,
         details_json, created_by, source_module, source_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (ward_patient_id, appointment_id, mrn or None, patient_name or None,
         event_type, title, json.dumps(details or {}), created_by,
         source_module or None, source_id),
    )
    db.commit()
    return cur.lastrowid


def timeline_for_patient(db, *, ward_patient_id: int | None = None, mrn: str = '') -> list:
    if ward_patient_id:
        return db.execute(
            """
            SELECT e.*, u.full_name AS author_name
            FROM gi_journey_event e
            LEFT JOIN user u ON u.id = e.created_by
            WHERE e.ward_patient_id = ?
            ORDER BY e.event_at ASC, e.id ASC
            """,
            (ward_patient_id,),
        ).fetchall()
    if mrn:
        return db.execute(
            """
            SELECT e.*, u.full_name AS author_name
            FROM gi_journey_event e
            LEFT JOIN user u ON u.id = e.created_by
            WHERE e.mrn = ?
            ORDER BY e.event_at ASC, e.id ASC
            """,
            (mrn,),
        ).fetchall()
    return []


def record_lab_result(
    db, *, test_name: str, result_value: str, result_unit: str = '',
    ward_patient_id: int | None = None, session_id: int | None = None,
    order_id: int | None = None, mrn: str = '', recorded_by: int | None = None,
) -> int:
    cur = db.execute(
        """
        INSERT INTO gi_lab_result
        (ward_patient_id, session_id, order_id, mrn, test_name, result_value, result_unit, recorded_by)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (ward_patient_id, session_id, order_id, mrn or None,
         test_name, result_value, result_unit or None, recorded_by),
    )
    rid = cur.lastrowid
    add_event(
        db, event_type='investigation_result', title=f'Lab: {test_name} = {result_value}',
        ward_patient_id=ward_patient_id, mrn=mrn, created_by=recorded_by,
        source_module='labs', source_id=rid,
        details={'test_name': test_name, 'value': result_value, 'unit': result_unit},
    )
    db.commit()
    try:
        from gi_platform import lab_propagation
        lab_propagation.after_lab_result_saved(
            db,
            ward_patient_id=ward_patient_id,
            session_id=session_id,
            result_id=rid,
            recalculate_scores=True,
        )
    except Exception:
        pass
    return rid


def labs_for_patient(db, *, ward_patient_id: int | None = None, mrn: str = '') -> list:
    if ward_patient_id:
        return db.execute(
            'SELECT * FROM gi_lab_result WHERE ward_patient_id = ? ORDER BY recorded_at DESC',
            (ward_patient_id,),
        ).fetchall()
    if mrn:
        return db.execute(
            'SELECT * FROM gi_lab_result WHERE mrn = ? ORDER BY recorded_at DESC', (mrn,)
        ).fetchall()
    return []


def sync_research_variables_from_journey(db, enrollment_id: int) -> int:
    """Auto-populate research enrollment payload from journey + labs."""
    enr = db.execute(
        'SELECT * FROM gi_research_enrollment WHERE id = ?', (enrollment_id,)
    ).fetchone()
    if not enr:
        return 0
    variables = db.execute(
        'SELECT * FROM gi_research_variable WHERE registry_id = ?', (enr['registry_id'],)
    ).fetchall()
    payload = json.loads(enr['payload_json'] or '{}')
    updated = 0
    wp_id = enr['ward_patient_id']
    mrn = enr['mrn'] or ''
    labs = labs_for_patient(db, ward_patient_id=wp_id, mrn=mrn)
    lab_map = {l['test_name'].lower(): l['result_value'] for l in labs}
    for var in variables:
        code = (var['code'] or var['name'] or '').lower()
        src = (var['source_type'] or '').lower()
        if code in payload and payload[code]:
            continue
        if src == 'lab' and code in lab_map:
            payload[code] = lab_map[code]
            updated += 1
        elif src == 'mrn' and mrn:
            payload[code or 'mrn'] = mrn
            updated += 1
    if updated:
        db.execute(
            'UPDATE gi_research_enrollment SET payload_json = ? WHERE id = ?',
            (json.dumps(payload), enrollment_id),
        )
        db.commit()
    return updated
