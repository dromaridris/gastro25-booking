"""Ward bed board, admission, transfer, discharge — SQLite implementation for Gastro25."""

from __future__ import annotations

from datetime import datetime

BED_AVAILABLE = 'available'
BED_OCCUPIED = 'occupied'
BED_CLEANING = 'cleaning'
BED_RESERVED = 'reserved'
BED_KIND_REGULAR = 'regular'
BED_KIND_EXTRA = 'extra'

MOVEMENT_ADMIT = 'admit'
MOVEMENT_TRANSFER = 'transfer'
MOVEMENT_DISCHARGE = 'discharge'

# Outcomes that may skip discharge summary when an override reason is provided.
DISCHARGE_OVERRIDE_OUTCOMES = frozenset({'lama', 'dor', 'expired'})
APPROVED_PLAN_STATUSES = frozenset({'approved'})


def _now_iso() -> str:
    return datetime.utcnow().isoformat()


def list_wards(dbconn):
    return dbconn.execute('SELECT * FROM ward ORDER BY name').fetchall()


def get_ward(dbconn, ward_id: int):
    return dbconn.execute('SELECT * FROM ward WHERE id = ?', (ward_id,)).fetchone()


def list_beds(dbconn, ward_id: int):
    return dbconn.execute(
        """
        SELECT b.*, a.id AS admission_id, a.ward_patient_id, a.admitted_at,
               p.patient_name, p.mrn, p.age, p.gender
        FROM ward_bed b
        LEFT JOIN ward_admission a ON a.bed_id = b.id AND a.is_active = 1 AND a.discharged_at IS NULL
        LEFT JOIN ward_patient p ON p.id = a.ward_patient_id
        WHERE b.ward_id = ? AND b.is_active = 1
        ORDER BY b.bed_kind, b.sort_order, b.label
        """,
        (ward_id,),
    ).fetchall()


def ward_statistics(dbconn, ward_id: int) -> dict:
    beds = dbconn.execute(
        "SELECT status, bed_kind, COUNT(1) AS n FROM ward_bed WHERE ward_id = ? AND is_active = 1 GROUP BY status, bed_kind",
        (ward_id,),
    ).fetchall()
    stats = {
        'total': 0,
        'occupied': 0,
        'available': 0,
        'cleaning': 0,
        'reserved': 0,
        'regular': 0,
        'extra': 0,
    }
    for row in beds:
        stats['total'] += row['n']
        stats[row['status']] = stats.get(row['status'], 0) + row['n']
        stats[row['bed_kind']] = stats.get(row['bed_kind'], 0) + row['n']
    stats['occupancy_pct'] = round((stats['occupied'] / stats['total']) * 100, 1) if stats['total'] else 0
    return stats


def add_extra_bed(dbconn, ward_id: int) -> int:
    existing = dbconn.execute(
        "SELECT label FROM ward_bed WHERE ward_id = ? AND bed_kind = 'extra' ORDER BY sort_order DESC LIMIT 1",
        (ward_id,),
    ).fetchone()
    next_n = 1
    if existing and existing['label'].startswith('Extra '):
        try:
            next_n = int(existing['label'].split(' ', 1)[1]) + 1
        except ValueError:
            next_n = dbconn.execute(
                "SELECT COUNT(1) FROM ward_bed WHERE ward_id = ? AND bed_kind = 'extra'",
                (ward_id,),
            ).fetchone()[0] + 1
    label = f'Extra {next_n}'
    sort_order = 1000 + next_n
    cur = dbconn.execute(
        "INSERT INTO ward_bed (ward_id, label, bed_kind, sort_order, status) VALUES (?, ?, 'extra', ?, 'available')",
        (ward_id, label, sort_order),
    )
    dbconn.commit()
    return cur.lastrowid


def create_or_get_patient(dbconn, *, patient_name, mrn=None, age=None, gender=None, referral=None):
    if mrn:
        row = dbconn.execute('SELECT * FROM ward_patient WHERE mrn = ?', (mrn,)).fetchone()
        if row:
            dbconn.execute(
                "UPDATE ward_patient SET patient_name = ?, age = ?, gender = ?, referral = ?, updated_at = ? WHERE id = ?",
                (patient_name, age, gender, referral, _now_iso(), row['id']),
            )
            dbconn.commit()
            return row['id']
    cur = dbconn.execute(
        "INSERT INTO ward_patient (mrn, patient_name, age, gender, referral) VALUES (?, ?, ?, ?, ?)",
        (mrn, patient_name, age, gender, referral),
    )
    dbconn.commit()
    return cur.lastrowid


def admit_patient(dbconn, *, bed_id, patient_name, mrn=None, age=None, gender=None, referral=None, notes=None, user_id=None):
    bed = dbconn.execute('SELECT * FROM ward_bed WHERE id = ? AND is_active = 1', (bed_id,)).fetchone()
    if not bed:
        raise ValueError('Bed not found.')
    if bed['status'] not in (BED_AVAILABLE, BED_RESERVED):
        raise ValueError('Bed is not available.')
    active = dbconn.execute(
        "SELECT id FROM ward_admission WHERE bed_id = ? AND is_active = 1 AND discharged_at IS NULL",
        (bed_id,),
    ).fetchone()
    if active:
        raise ValueError('Bed is already occupied.')

    ward_patient_id = create_or_get_patient(
        dbconn, patient_name=patient_name, mrn=mrn, age=age, gender=gender, referral=referral
    )
    cur = dbconn.execute(
        """
        INSERT INTO ward_admission (ward_patient_id, bed_id, admitted_by_user_id, notes)
        VALUES (?, ?, ?, ?)
        """,
        (ward_patient_id, bed_id, user_id, notes),
    )
    admission_id = cur.lastrowid
    dbconn.execute("UPDATE ward_bed SET status = ? WHERE id = ?", (BED_OCCUPIED, bed_id))
    dbconn.execute(
        """
        INSERT INTO ward_movement (ward_patient_id, to_bed_id, movement_type, notes, moved_by_user_id)
        VALUES (?, ?, ?, ?, ?)
        """,
        (ward_patient_id, bed_id, MOVEMENT_ADMIT, notes, user_id),
    )
    dbconn.commit()
    return admission_id, ward_patient_id


def transfer_patient(dbconn, *, from_bed_id, to_bed_id, notes=None, user_id=None):
    occ = dbconn.execute(
        """
        SELECT a.* FROM ward_admission a
        WHERE a.bed_id = ? AND a.is_active = 1 AND a.discharged_at IS NULL
        """,
        (from_bed_id,),
    ).fetchone()
    if not occ:
        raise ValueError('Source bed has no active patient.')
    to_bed = dbconn.execute('SELECT * FROM ward_bed WHERE id = ?', (to_bed_id,)).fetchone()
    if not to_bed or to_bed['status'] not in (BED_AVAILABLE, BED_RESERVED):
        raise ValueError('Destination bed is not available.')
    if dbconn.execute(
        "SELECT id FROM ward_admission WHERE bed_id = ? AND is_active = 1 AND discharged_at IS NULL",
        (to_bed_id,),
    ).fetchone():
        raise ValueError('Destination bed is occupied.')

    dbconn.execute("UPDATE ward_admission SET bed_id = ? WHERE id = ?", (to_bed_id, occ['id']))
    dbconn.execute("UPDATE ward_bed SET status = ? WHERE id = ?", (BED_CLEANING, from_bed_id))
    dbconn.execute("UPDATE ward_bed SET status = ? WHERE id = ?", (BED_OCCUPIED, to_bed_id))
    dbconn.execute(
        """
        INSERT INTO ward_movement (ward_patient_id, from_bed_id, to_bed_id, movement_type, notes, moved_by_user_id)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (occ['ward_patient_id'], from_bed_id, to_bed_id, MOVEMENT_TRANSFER, notes, user_id),
    )
    dbconn.commit()


def get_discharge_checklist(dbconn, ward_patient_id: int) -> dict:
    """Readiness for discharge: summary (hard), final diagnosis + approved plan (soft)."""
    summaries = list_discharge_summaries(dbconn, ward_patient_id)
    has_summary = any((s['summary_text'] or '').strip() for s in summaries)

    sess = dbconn.execute(
        """
        SELECT id, final_diagnosis FROM gi_history_session
        WHERE ward_patient_id = ?
        ORDER BY updated_at DESC, id DESC LIMIT 1
        """,
        (ward_patient_id,),
    ).fetchone()
    final_dx = ''
    if sess:
        try:
            final_dx = (sess['final_diagnosis'] or '').strip()
        except (KeyError, IndexError, TypeError):
            final_dx = ''
    has_final_diagnosis = bool(final_dx)

    plan = dbconn.execute(
        """
        SELECT p.id, p.approval_status FROM gi_management_plan p
        WHERE p.ward_patient_id = ?
        ORDER BY p.id DESC LIMIT 1
        """,
        (ward_patient_id,),
    ).fetchone()
    if not plan and sess:
        plan = dbconn.execute(
            """
            SELECT id, approval_status FROM gi_management_plan
            WHERE session_id = ?
            ORDER BY id DESC LIMIT 1
            """,
            (sess['id'],),
        ).fetchone()
    plan_status = (plan['approval_status'] if plan else None) or None
    has_approved_plan = bool(plan_status and plan_status in APPROVED_PLAN_STATUSES)

    return {
        'ward_patient_id': ward_patient_id,
        'has_summary': has_summary,
        'has_final_diagnosis': has_final_diagnosis,
        'final_diagnosis': final_dx,
        'has_approved_plan': has_approved_plan,
        'plan_status': plan_status,
        'summary_required': True,
        'ready_for_routine_discharge': has_summary,
    }


def evaluate_discharge_gate(
    checklist: dict,
    *,
    outcome: str | None = None,
    override: bool = False,
    override_reason: str | None = None,
) -> tuple[bool, str | None]:
    """Return (allowed, error_message). Summary required unless LAMA/DOR/expired or explicit override + reason."""
    outcome_val = (outcome or 'discharged').strip().lower()
    reason = (override_reason or '').strip()
    if checklist.get('has_summary'):
        return True, None
    can_override = override or outcome_val in DISCHARGE_OVERRIDE_OUTCOMES
    if can_override:
        if not reason:
            return (
                False,
                'Discharge summary missing — provide an override reason '
                '(required for LAMA / DOR / expired, or explicit override).',
            )
        return True, None
    return (
        False,
        'Discharge summary required before routine discharge. '
        'Save a summary on the patient page, or choose LAMA/DOR/Expired with a reason, '
        'or check override and enter a reason.',
    )


def discharge_patient(
    dbconn,
    *,
    bed_id,
    notes=None,
    user_id=None,
    outcome=None,
    override=False,
    override_reason=None,
    enforce_gate=True,
):
    occ = dbconn.execute(
        """
        SELECT * FROM ward_admission
        WHERE bed_id = ? AND is_active = 1 AND discharged_at IS NULL
        """,
        (bed_id,),
    ).fetchone()
    if not occ:
        raise ValueError('Bed has no active patient.')
    outcome_val = (outcome or 'discharged').strip().lower()
    if enforce_gate:
        checklist = get_discharge_checklist(dbconn, occ['ward_patient_id'])
        ok, err = evaluate_discharge_gate(
            checklist,
            outcome=outcome_val,
            override=override,
            override_reason=override_reason,
        )
        if not ok:
            raise ValueError(err)
    now = _now_iso()
    dbconn.execute(
        """
        UPDATE ward_admission
        SET discharged_at = ?, is_active = 0, discharge_outcome = ?
        WHERE id = ?
        """,
        (now, outcome_val, occ['id']),
    )
    dbconn.execute("UPDATE ward_bed SET status = ? WHERE id = ?", (BED_CLEANING, bed_id))
    note_text = notes or ''
    if outcome_val:
        note_text = f"Outcome: {outcome_val.upper()}" + (f" — {notes}" if notes else '')
    reason = (override_reason or '').strip()
    if reason and (override or outcome_val in DISCHARGE_OVERRIDE_OUTCOMES):
        note_text = (note_text + f' | Override: {reason}').strip(' |')
    dbconn.execute(
        """
        INSERT INTO ward_movement (ward_patient_id, from_bed_id, movement_type, notes, moved_by_user_id)
        VALUES (?, ?, ?, ?, ?)
        """,
        (occ['ward_patient_id'], bed_id, MOVEMENT_DISCHARGE, note_text, user_id),
    )
    dbconn.commit()
    return occ['ward_patient_id']


def get_ward_patient(dbconn, ward_patient_id: int):
    return dbconn.execute('SELECT * FROM ward_patient WHERE id = ?', (ward_patient_id,)).fetchone()


def get_active_admission(dbconn, ward_patient_id: int):
    return dbconn.execute(
        """
        SELECT a.*, b.label AS bed_label, b.bed_kind
        FROM ward_admission a
        JOIN ward_bed b ON b.id = a.bed_id
        WHERE a.ward_patient_id = ? AND a.is_active = 1 AND a.discharged_at IS NULL
        ORDER BY a.admitted_at DESC LIMIT 1
        """,
        (ward_patient_id,),
    ).fetchone()


def list_clinical_notes(dbconn, ward_patient_id: int):
    return dbconn.execute(
        "SELECT * FROM ward_clinical_note WHERE ward_patient_id = ? ORDER BY created_at DESC",
        (ward_patient_id,),
    ).fetchall()


def add_clinical_note(dbconn, *, ward_patient_id, note_type, body, user_id=None):
    dbconn.execute(
        "INSERT INTO ward_clinical_note (ward_patient_id, note_type, body, created_by_user_id) VALUES (?, ?, ?, ?)",
        (ward_patient_id, note_type, body, user_id),
    )
    dbconn.commit()


def mark_bed_ready(dbconn, bed_id: int) -> None:
    bed = dbconn.execute('SELECT * FROM ward_bed WHERE id = ?', (bed_id,)).fetchone()
    if not bed:
        raise ValueError('Bed not found.')
    if bed['status'] != BED_CLEANING:
        raise ValueError('Only beds awaiting cleaning can be marked ready.')
    dbconn.execute("UPDATE ward_bed SET status = ? WHERE id = ?", (BED_AVAILABLE, bed_id))
    dbconn.commit()


def save_discharge_summary(dbconn, *, ward_patient_id: int, summary_text: str,
                           follow_up_plan: str = '', user_id=None) -> int:
    admission = get_active_admission(dbconn, ward_patient_id)
    cur = dbconn.execute(
        """
        INSERT INTO ward_discharge_summary
        (ward_patient_id, admission_id, summary_text, follow_up_plan, discharged_by)
        VALUES (?, ?, ?, ?, ?)
        """,
        (ward_patient_id, admission['id'] if admission else None,
         summary_text, follow_up_plan, user_id),
    )
    dbconn.commit()
    return cur.lastrowid


def list_discharge_summaries(dbconn, ward_patient_id: int) -> list:
    return dbconn.execute(
        "SELECT * FROM ward_discharge_summary WHERE ward_patient_id = ? ORDER BY created_at DESC",
        (ward_patient_id,),
    ).fetchall()


def ward_extended_analytics(dbconn, ward_id: int) -> dict:
    base = ward_statistics(dbconn, ward_id)
    admissions_30d = dbconn.execute(
        """
        SELECT COUNT(*) AS c FROM ward_admission a
        JOIN ward_bed b ON b.id = a.bed_id
        WHERE b.ward_id = ? AND a.admitted_at >= datetime('now', '-30 days')
        """,
        (ward_id,),
    ).fetchone()['c']
    discharges_30d = dbconn.execute(
        """
        SELECT COUNT(*) AS c FROM ward_admission a
        JOIN ward_bed b ON b.id = a.bed_id
        WHERE b.ward_id = ? AND a.discharged_at >= datetime('now', '-30 days')
        """,
        (ward_id,),
    ).fetchone()['c']
    avg_los = dbconn.execute(
        """
        SELECT AVG(
            (julianday(a.discharged_at) - julianday(a.admitted_at)) * 24
        ) AS hours
        FROM ward_admission a
        JOIN ward_bed b ON b.id = a.bed_id
        WHERE b.ward_id = ? AND a.discharged_at IS NOT NULL
        AND a.discharged_at >= datetime('now', '-90 days')
        """,
        (ward_id,),
    ).fetchone()['hours']
    base['admissions_30d'] = admissions_30d
    base['discharges_30d'] = discharges_30d
    base['avg_los_hours'] = round(avg_los, 1) if avg_los else 0
    return base
