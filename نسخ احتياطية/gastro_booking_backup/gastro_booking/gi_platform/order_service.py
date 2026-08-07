"""Investigation order approval rules and procedure scheduling."""

from __future__ import annotations

from datetime import datetime

# Labs auto-approved; imaging + endoscopy need registrar
REGISTRAR_APPROVAL_TYPES = frozenset({'imaging', 'endoscopy'})

ENDOSCOPY_ITEM_CODES = frozenset({
    'proc.egd', 'proc.colonoscopy', 'proc.flex_sig', 'proc.ercp', 'proc.eus', 'proc.capsule',
})

PROCEDURE_TYPE_MAP = {
    'proc.egd': 'upper_gi',
    'proc.colonoscopy': 'colonoscopy',
    'proc.ercp': 'ercp',
    'proc.flex_sig': 'sigmoidoscopy',
    'proc.eus': 'eus',
    'proc.capsule': 'capsule_endoscopy',
}

_NAME_TO_PROCEDURE = (
    ('ercp', 'ercp'),
    ('enteroscop', 'enteroscopy'),
    ('capsule', 'capsule_endoscopy'),
    ('eus', 'eus'),
    ('emr', 'emr'),
    ('esd', 'esd'),
    ('sigmoid', 'sigmoidoscopy'),
    ('proctoscop', 'proctoscopy'),
    ('colon', 'colonoscopy'),
    ('peg', 'peg_tube'),
    ('upper', 'upper_gi'),
    ('egd', 'upper_gi'),
    ('endoscop', 'upper_gi'),
)


def initial_approval_status(order_type: str) -> str:
    if order_type == 'lab':
        return 'approved'
    if order_type in REGISTRAR_APPROVAL_TYPES:
        return 'pending_registrar'
    return 'approved'


def requires_registrar(order_type: str) -> bool:
    return order_type in REGISTRAR_APPROVAL_TYPES


def is_schedulable_procedure(order_type: str, item_code: str = '') -> bool:
    return order_type == 'endoscopy' or (item_code or '').startswith('proc.')


def procedure_type_for_order(item_code: str, item_name: str = '') -> str:
    if item_code in PROCEDURE_TYPE_MAP:
        return PROCEDURE_TYPE_MAP[item_code]
    name = (item_name or '').lower()
    for needle, proc in _NAME_TO_PROCEDURE:
        if needle in name:
            return proc
    return 'upper_gi'


def create_procedure_appointment(
    db, *, order_id: int, scheduled_date: str, scheduled_time: str = '',
    booked_by_username: str = '', booked_by_role: str = '',
) -> int | None:
    """Book endoscopy/ERCP slot when registrar approves."""
    order = db.execute(
        """
        SELECT o.*, wp.patient_name, wp.mrn, wp.age, wp.gender
        FROM gi_investigation_order o
        LEFT JOIN ward_patient wp ON wp.id = o.ward_patient_id
        WHERE o.id = ?
        """,
        (order_id,),
    ).fetchone()
    if not order:
        return None
    proc_type = procedure_type_for_order(order['item_code'] or '', order['item_name'])
    patient_name = order['patient_name'] or 'Ward patient'
    mrn = order['mrn'] or ''
    age = 0
    try:
        age = int(order['age']) if order['age'] else 0
    except (TypeError, ValueError):
        age = 0
    gender = order['gender'] or 'Unknown'
    notes = f"Registrar-approved from ward order #{order_id}"
    if scheduled_time:
        notes += f" · Preferred time: {scheduled_time}"
    cur = db.execute(
        """
        INSERT INTO appointment
        (patient_name, gender, age, phone, mrn, clinical_notes, on_admission_hb, platelet, inr,
         total_bilirubin, ggt, alp, tlc, comorbs_etiology, referral, procedure_type,
         appointment_date, is_bleeding, is_override, no_show, booked_by_username, booked_by_role, created_at)
        VALUES (?, ?, ?, ?, ?, ?, '', '', '', '', '', '', '', '', 'Ward', ?, ?, 0, 0, 0, ?, ?, ?)
        """,
        (
            patient_name, gender, age, '0000000000', mrn, notes,
            proc_type, scheduled_date,
            booked_by_username or 'registrar', booked_by_role or 'registrar',
            datetime.utcnow().isoformat(),
        ),
    )
    appt_id = cur.lastrowid
    db.execute(
        """
        UPDATE gi_investigation_order
        SET scheduled_date = ?, scheduled_time = ?, appointment_id = ?, status = 'scheduled'
        WHERE id = ?
        """,
        (scheduled_date, scheduled_time or None, appt_id, order_id),
    )
    db.commit()
    return appt_id
