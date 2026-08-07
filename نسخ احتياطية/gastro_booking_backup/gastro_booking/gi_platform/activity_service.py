"""Unified clinical/academic activity tracking — logbook + attendance."""

from __future__ import annotations

import json
from datetime import date, datetime

from gi_platform.constants import CLINICAL_STAFF_ROLES


def _today() -> str:
    return date.today().isoformat()


def record_activity(
    db,
    *,
    user_id: int | None,
    activity_type: str,
    title: str,
    ward_patient_id: int | None = None,
    session_id: int | None = None,
    mrn: str = '',
    patient_name: str = '',
    source_module: str = '',
    source_type: str = '',
    source_id: int | None = None,
    appointment_id: int | None = None,
    details: dict | None = None,
) -> int | None:
    """Log activity for any clinical staff member and mark daily attendance."""
    if not user_id:
        return None
    user = db.execute('SELECT role, full_name FROM user WHERE id = ?', (user_id,)).fetchone()
    if not user or user['role'] not in CLINICAL_STAFF_ROLES:
        return None

    if ward_patient_id and (not mrn or not patient_name):
        wp = db.execute(
            'SELECT mrn, patient_name FROM ward_patient WHERE id = ?', (ward_patient_id,)
        ).fetchone()
        if wp:
            mrn = mrn or (wp['mrn'] or '')
            patient_name = patient_name or (wp['patient_name'] or '')

    if appointment_id and (not mrn or not patient_name):
        ap = db.execute(
            'SELECT mrn, patient_name FROM appointment WHERE id = ?', (appointment_id,)
        ).fetchone()
        if ap:
            mrn = mrn or (ap['mrn'] or '')
            patient_name = patient_name or (ap['patient_name'] or '')

    existing = None
    if source_module and source_type and source_id:
        existing = db.execute(
            """
            SELECT id FROM gi_portfolio_entry
            WHERE user_id = ? AND source_module = ? AND source_type = ? AND source_id = ?
            LIMIT 1
            """,
            (user_id, source_module, source_type, source_id),
        ).fetchone()

    payload = json.dumps(details or {})
    if existing:
        entry_id = existing['id']
    else:
        cur = db.execute(
            """
            INSERT INTO gi_portfolio_entry
            (user_id, ward_patient_id, session_id, activity_type, title, details_json,
             mrn, patient_name, source_module, source_type, source_id, appointment_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (user_id, ward_patient_id, session_id, activity_type, title, payload,
             mrn or None, patient_name or None, source_module or None,
             source_type or None, source_id, appointment_id),
        )
        entry_id = cur.lastrowid

    _mark_present(db, user_id)
    db.commit()
    return entry_id


def _mark_present(db, user_id: int) -> None:
    today = _today()
    row = db.execute(
        'SELECT id, activity_count FROM gi_attendance_record WHERE user_id = ? AND attendance_date = ?',
        (user_id, today),
    ).fetchone()
    if row:
        db.execute(
            """
            UPDATE gi_attendance_record
            SET status = 'present', activity_count = activity_count + 1, computed_at = datetime('now')
            WHERE id = ?
            """,
            (row['id'],),
        )
    else:
        db.execute(
            """
            INSERT INTO gi_attendance_record (user_id, attendance_date, status, activity_count)
            VALUES (?, ?, 'present', 1)
            """,
            (user_id, today),
        )


ACTIVITY_ROUTE_MAP = {
    ('POST', '/api/book'): ('booking', 'appointment_booked', 'Booked appointment'),
    ('POST', '/ercp/'): ('ercp', 'ercp_report_save', 'ERCP report saved'),
    ('POST', '/dilatation/'): ('dilatation', 'dilatation_report_save', 'Dilatation report saved'),
    ('POST', '/procedure-reports/'): ('procedure_reports', 'procedure_report_save', 'Procedure report saved'),
    ('POST', '/ward/patient/'): ('ward', 'ward_note', 'Ward clinical note'),
    ('POST', '/clinical-history/'): ('clinical', 'clinical_action', 'Clinical workflow action'),
    ('POST', '/research/'): ('research', 'research_action', 'Research activity'),
    ('POST', '/knowledge-library/'): ('knowledge', 'knowledge_action', 'Knowledge library activity'),
}


def try_record_from_request(db, *, user_id: int | None, method: str, path: str) -> None:
    """Best-effort activity capture from HTTP requests without touching ERCP core."""
    if not user_id or method != 'POST':
        return
    for (m, prefix), (module, atype, title) in ACTIVITY_ROUTE_MAP.items():
        if m == method and path.startswith(prefix):
            record_activity(
                db, user_id=user_id, activity_type=atype, title=title,
                source_module=module, source_type='http_request',
                details={'path': path},
            )
            return
