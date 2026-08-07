"""Unified patient identity bridge — links MRN across booking, ward, GI modules."""

from __future__ import annotations


def normalize_mrn(mrn: str | None) -> str:
    return (mrn or '').strip().upper()


def resolve_mrn(db, *, ward_patient_id: int | None = None,
                appointment_id: int | None = None) -> str:
    if ward_patient_id:
        row = db.execute(
            "SELECT mrn FROM ward_patient WHERE id = ?", (ward_patient_id,)
        ).fetchone()
        if row and row['mrn']:
            return normalize_mrn(row['mrn'])
    if appointment_id:
        row = db.execute(
            "SELECT mrn FROM appointment WHERE id = ?", (appointment_id,)
        ).fetchone()
        if row and row['mrn']:
            return normalize_mrn(row['mrn'])
    return ''


def link_identity(db, *, mrn: str, ward_patient_id: int | None = None,
                  appointment_id: int | None = None, patient_name: str = '') -> int:
    """Create or update gi_patient_identity row."""
    mrn = normalize_mrn(mrn)
    if not mrn:
        raise ValueError('MRN is required to link patient identity.')
    existing = db.execute(
        "SELECT id FROM gi_patient_identity WHERE mrn = ?", (mrn,)
    ).fetchone()
    if existing:
        db.execute(
            """
            UPDATE gi_patient_identity
            SET ward_patient_id = COALESCE(?, ward_patient_id),
                appointment_id = COALESCE(?, appointment_id),
                patient_name = COALESCE(NULLIF(?, ''), patient_name),
                updated_at = datetime('now')
            WHERE id = ?
            """,
            (ward_patient_id, appointment_id, patient_name, existing['id']),
        )
        db.commit()
        return existing['id']
    cur = db.execute(
        """
        INSERT INTO gi_patient_identity (mrn, patient_name, ward_patient_id, appointment_id)
        VALUES (?, ?, ?, ?)
        """,
        (mrn, patient_name, ward_patient_id, appointment_id),
    )
    db.commit()
    return cur.lastrowid


def get_identity_by_mrn(db, mrn: str):
    return db.execute(
        "SELECT * FROM gi_patient_identity WHERE mrn = ?", (normalize_mrn(mrn),)
    ).fetchone()


def get_latest_history_session(db, ward_patient_id: int) -> int | None:
    row = db.execute(
        """
        SELECT id FROM gi_history_session
        WHERE ward_patient_id = ?
        ORDER BY updated_at DESC, id DESC LIMIT 1
        """,
        (ward_patient_id,),
    ).fetchone()
    return row['id'] if row else None


def sync_ward_patient_mrn(db, ward_patient_id: int) -> None:
    """Ensure gi_patient_identity exists for ward patient."""
    wp = db.execute(
        "SELECT id, mrn, patient_name FROM ward_patient WHERE id = ?", (ward_patient_id,)
    ).fetchone()
    if wp and wp['mrn']:
        link_identity(db, mrn=wp['mrn'], ward_patient_id=ward_patient_id,
                      patient_name=wp['patient_name'])


def list_appointments_for_mrn(db, mrn: str, *, limit: int = 20) -> list:
    """Booking appointments matching MRN (case-insensitive)."""
    mrn_n = normalize_mrn(mrn)
    if not mrn_n:
        return []
    return db.execute(
        """
        SELECT id, patient_name, mrn, procedure_type, appointment_date,
               clinical_notes, referral, no_show, created_at
        FROM appointment
        WHERE UPPER(TRIM(mrn)) = ?
        ORDER BY appointment_date DESC, id DESC
        LIMIT ?
        """,
        (mrn_n, limit),
    ).fetchall()


def list_appointments_for_ward_patient(db, ward_patient_id: int, *, limit: int = 20) -> list:
    wp = db.execute(
        "SELECT mrn FROM ward_patient WHERE id = ?", (ward_patient_id,)
    ).fetchone()
    if not wp or not wp['mrn']:
        return []
    return list_appointments_for_mrn(db, wp['mrn'], limit=limit)


# Maps a ward gi_lab_result.test_name (case-insensitive) to the matching
# appointment column, so a new procedure booking can be pre-filled from
# labs already recorded on the ward instead of re-typing them.
_LAB_TO_APPOINTMENT_FIELD = {
    'hb': 'on_admission_hb', 'hemoglobin': 'on_admission_hb', 'haemoglobin': 'on_admission_hb',
    'platelet': 'platelet', 'platelets': 'platelet',
    'inr': 'inr',
    'bilirubin': 'total_bilirubin', 'total bilirubin': 'total_bilirubin', 'tb': 'total_bilirubin',
    'alt': 'alt',
    'ggt': 'ggt',
    'alp': 'alp',
    'tlc': 'tlc', 'wbc': 'tlc',
}


def latest_ward_labs_for_appointment_fields(db, *, mrn: str) -> dict[str, str]:
    """Latest numeric ward lab per test, mapped to appointment.* field names.

    Used to offer a "Prefill from ward labs" action when booking a
    procedure for a patient who already has recent ward results — never
    applied automatically/silently, so a clinician's own typed value is
    never overwritten without them choosing to.
    """
    mrn = normalize_mrn(mrn)
    if not mrn:
        return {}
    from gi_platform import lab_propagation
    labs = lab_propagation.list_labs_for_patient(db, mrn=mrn, limit=100)
    out: dict[str, str] = {}
    for lab in labs:  # already newest-first
        name = (lab.get('test_name') or '').strip().lower()
        field = _LAB_TO_APPOINTMENT_FIELD.get(name)
        if not field or field in out:
            continue
        value = (lab.get('result_value') or '').strip()
        if value:
            out[field] = value
    return out
