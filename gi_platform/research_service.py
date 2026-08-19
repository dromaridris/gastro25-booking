"""SQLite Research Registry service."""

from __future__ import annotations

import json
from typing import Any


def list_registries(db, *, status: str | None = None) -> list[dict]:
    sql = "SELECT * FROM gi_research_registry WHERE 1=1"
    params: list[Any] = []
    if status:
        sql += " AND status = ?"
        params.append(status)
    sql += " ORDER BY updated_at DESC"
    return db.execute(sql, params).fetchall()


def list_registries_for_user(db, user_id: int) -> list[dict]:
    rows = db.execute(
        "SELECT * FROM gi_research_registry ORDER BY updated_at DESC"
    ).fetchall()
    out = []
    for r in rows:
        if r['lead_user_id'] == user_id or user_id in team_user_ids(r):
            out.append(r)
    return out


def get_registry(db, registry_id: int):
    return db.execute(
        "SELECT * FROM gi_research_registry WHERE id = ?", (registry_id,)
    ).fetchone()


def get_registry_by_code(db, code: str):
    return db.execute(
        "SELECT * FROM gi_research_registry WHERE code = ?", (code,)
    ).fetchone()


def create_registry(db, *, code: str, title: str, pi_name: str = '',
                    description: str = '', created_by: int | None = None,
                    status: str = 'active') -> int:
    cur = db.execute(
        """
        INSERT INTO gi_research_registry (code, title, pi_name, description, created_by, status)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (code, title, pi_name, description, created_by, status),
    )
    db.commit()
    return cur.lastrowid


def add_variable(db, registry_id: int, name: str, var_type: str = 'text',
                 required: bool = False, options: list | None = None,
                 code: str = '', source_type: str = '', sort_order: int = 0) -> int:
    cur = db.execute(
        """
        INSERT INTO gi_research_variable
        (registry_id, name, var_type, required, options_json, code, source_type, sort_order)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (registry_id, name, var_type, 1 if required else 0, json.dumps(options or []),
         code, source_type, sort_order),
    )
    db.commit()
    return cur.lastrowid


def list_variables(db, registry_id: int) -> list[dict]:
    return db.execute(
        "SELECT * FROM gi_research_variable WHERE registry_id = ? ORDER BY sort_order, id",
        (registry_id,),
    ).fetchall()


def list_capture_variables(db, registry_id: int) -> list[dict]:
    """Variables approved for data capture and export."""
    return db.execute(
        """
        SELECT * FROM gi_research_variable
        WHERE registry_id = ?
          AND COALESCE(approval_status, 'approved') IN ('approved', '')
        ORDER BY sort_order, id
        """,
        (registry_id,),
    ).fetchall()


def registry_ready_for_enrollment(registry) -> bool:
    if not registry:
        return False
    if registry['status'] != 'active':
        return False
    hod = (registry['hod_status'] or '').strip()
    return hod not in ('pending_approval', 'needs_revision')


def enrollment_exists(
    db,
    registry_id: int,
    *,
    mrn: str = '',
    ward_patient_id: int | None = None,
) -> bool:
    mrn = (mrn or '').strip()
    if ward_patient_id:
        row = db.execute(
            """
            SELECT 1 FROM gi_research_enrollment
            WHERE registry_id = ? AND ward_patient_id = ?
              AND COALESCE(status, 'active') != 'withdrawn'
            LIMIT 1
            """,
            (registry_id, ward_patient_id),
        ).fetchone()
        if row:
            return True
    if mrn:
        row = db.execute(
            """
            SELECT 1 FROM gi_research_enrollment
            WHERE registry_id = ? AND mrn = ?
              AND COALESCE(status, 'active') != 'withdrawn'
            LIMIT 1
            """,
            (registry_id, mrn),
        ).fetchone()
        if row:
            return True
    return False


def resolve_appointment_id(db, *, mrn: str = '', ward_patient_id: int | None = None) -> int | None:
    if ward_patient_id and not mrn:
        row = db.execute(
            'SELECT mrn FROM ward_patient WHERE id = ?', (ward_patient_id,),
        ).fetchone()
        if row and row['mrn']:
            mrn = (row['mrn'] or '').strip()
    mrn = (mrn or '').strip()
    if mrn:
        row = db.execute(
            """
            SELECT id FROM appointment
            WHERE mrn = ? ORDER BY appointment_date DESC, id DESC LIMIT 1
            """,
            (mrn,),
        ).fetchone()
        if row:
            return int(row['id'])
    return None


def withdraw_enrollment(db, enrollment_id: int) -> bool:
    row = get_enrollment(db, enrollment_id)
    if not row or (row['status'] or 'active') == 'withdrawn':
        return False
    db.execute(
        "UPDATE gi_research_enrollment SET status = 'withdrawn' WHERE id = ?",
        (enrollment_id,),
    )
    db.commit()
    return True


def enroll_patient(db, registry_id: int, *, ward_patient_id: int | None = None,
                   appointment_id: int | None = None, mrn: str = '',
                   payload: dict | None = None, enrolled_by: int | None = None,
                   responsible_user_id: int | None = None) -> int:
    if responsible_user_id is None:
        responsible_user_id = enrolled_by
    cur = db.execute(
        """
        INSERT INTO gi_research_enrollment
        (registry_id, ward_patient_id, appointment_id, mrn, payload_json, enrolled_by, responsible_user_id)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (registry_id, ward_patient_id, appointment_id, mrn,
         json.dumps(payload or {}), enrolled_by, responsible_user_id),
    )
    db.commit()
    return cur.lastrowid


def list_enrollments(db, registry_id: int) -> list[dict]:
    return db.execute(
        """
        SELECT e.*, wp.patient_name AS ward_patient_name
        FROM gi_research_enrollment e
        LEFT JOIN ward_patient wp ON wp.id = e.ward_patient_id
        WHERE e.registry_id = ?
        ORDER BY e.enrolled_at DESC
        """,
        (registry_id,),
    ).fetchall()


def update_enrollment_payload(db, enrollment_id: int, payload: dict) -> None:
    db.execute(
        "UPDATE gi_research_enrollment SET payload_json = ? WHERE id = ?",
        (json.dumps(payload), enrollment_id),
    )
    db.commit()


def get_enrollment(db, enrollment_id: int):
    return db.execute(
        "SELECT * FROM gi_research_enrollment WHERE id = ?", (enrollment_id,)
    ).fetchone()


def delete_variable(db, variable_id: int) -> None:
    db.execute("DELETE FROM gi_research_variable WHERE id = ?", (variable_id,))
    db.commit()


def export_registry_csv(db, registry_id: int) -> str:
    """Return CSV text for enrollments with variable columns."""
    import csv
    import io

    variables = list_capture_variables(db, registry_id)
    enrollments = [
        e for e in list_enrollments(db, registry_id)
        if (e['status'] or 'active') != 'withdrawn'
    ]
    headers = ['enrollment_id', 'mrn', 'ward_patient_id', 'ward_patient_name', 'enrolled_at', 'status']
    headers += [v['code'] or v['name'] for v in variables]

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(headers)
    for e in enrollments:
        payload = json.loads(e['payload_json'] or '{}')
        row = [e['id'], e['mrn'] or '', e['ward_patient_id'] or '',
               e['ward_patient_name'] or '', e['enrolled_at'], e['status'] or 'active']
        for v in variables:
            key = v['code'] or v['name']
            row.append(payload.get(key, ''))
        writer.writerow(row)
    return buf.getvalue()


def registry_analytics(db, registry_id: int) -> dict:
    enrollments = [
        e for e in list_enrollments(db, registry_id)
        if (e['status'] or 'active') != 'withdrawn'
    ]
    variables = list_capture_variables(db, registry_id)
    filled = 0
    total_fields = 0
    for e in enrollments:
        payload = json.loads(e['payload_json'] or '{}')
        for v in variables:
            total_fields += 1
            key = v['code'] or v['name']
            if payload.get(key) not in (None, '', []):
                filled += 1
    by_user = db.execute(
        """
        SELECT u.full_name, u.id AS user_id, COUNT(e.id) AS patients,
               COUNT(DISTINCT date(e.enrolled_at)) AS active_days
        FROM gi_research_enrollment e
        LEFT JOIN user u ON u.id = e.responsible_user_id
        WHERE e.registry_id = ? AND COALESCE(e.status, 'active') != 'withdrawn'
        GROUP BY e.responsible_user_id
        ORDER BY patients DESC
        """,
        (registry_id,),
    ).fetchall()
    return {
        'enrollment_count': len(enrollments),
        'variable_count': len(variables),
        'completeness_pct': round((filled / total_fields) * 100, 1) if total_fields else 0,
        'team_activity': by_user,
    }


def assign_hod_project(db, *, code: str, title: str, lead_user_id: int,
                       team_user_ids: list[int], assigned_by_hod_id: int,
                       description: str = '') -> int:
    cur = db.execute(
        """
        INSERT INTO gi_research_registry
        (code, title, description, lead_user_id, team_user_ids, assigned_by_hod_id,
         hod_status, status, created_by)
        VALUES (?, ?, ?, ?, ?, ?, 'pending_approval', 'draft', ?)
        """,
        (code, title, description, lead_user_id, json.dumps(_team_without_lead(lead_user_id, team_user_ids)),
         assigned_by_hod_id, assigned_by_hod_id),
    )
    db.commit()
    return cur.lastrowid


def _team_without_lead(lead_user_id: int | None, team_user_ids: list[int]) -> list[int]:
    seen: set[int] = set()
    out: list[int] = []
    for uid in team_user_ids:
        if not uid or uid == lead_user_id or uid in seen:
            continue
        seen.add(uid)
        out.append(uid)
    return out


def update_registry_team(
    db,
    registry_id: int,
    *,
    lead_user_id: int,
    team_user_ids: list[int],
) -> bool:
    reg = get_registry(db, registry_id)
    if not reg or not lead_user_id:
        return False
    team = _team_without_lead(lead_user_id, team_user_ids)
    db.execute(
        """
        UPDATE gi_research_registry
        SET lead_user_id = ?, team_user_ids = ?
        WHERE id = ?
        """,
        (lead_user_id, json.dumps(team), registry_id),
    )
    db.commit()
    return True


def remove_team_member(db, registry_id: int, user_id: int) -> bool:
    reg = get_registry(db, registry_id)
    if not reg or reg['lead_user_id'] == user_id:
        return False
    team = [tid for tid in team_user_ids(reg) if tid != user_id]
    db.execute(
        'UPDATE gi_research_registry SET team_user_ids = ? WHERE id = ?',
        (json.dumps(team), registry_id),
    )
    db.commit()
    return True


def propose_variable(db, registry_id: int, *, name: str, var_type: str = 'text',
                     proposed_by: int, code: str = '', source_type: str = '') -> int:
    cur = db.execute(
        """
        INSERT INTO gi_research_variable
        (registry_id, name, var_type, code, source_type, approval_status, proposed_by, required)
        VALUES (?, ?, ?, ?, ?, 'pending_hod', ?, 0)
        """,
        (registry_id, name, var_type, code or None, source_type or None, proposed_by),
    )
    db.commit()
    return cur.lastrowid


def review_variable(db, variable_id: int, *, approve: bool, reviewer_id: int,
                    review_note: str = '') -> None:
    status = 'approved' if approve else 'needs_revision'
    db.execute(
        """
        UPDATE gi_research_variable
        SET approval_status = ?, review_note = ?
        WHERE id = ?
        """,
        (status, review_note.strip(), variable_id),
    )
    db.commit()


def hod_review_project(db, registry_id: int, *, approve: bool, note: str = '') -> None:
    status = 'active' if approve else 'needs_revision'
    reg_status = 'active' if approve else 'draft'
    db.execute(
        """
        UPDATE gi_research_registry
        SET hod_status = ?, hod_review_note = ?, status = ?
        WHERE id = ?
        """,
        (status, note.strip(), reg_status, registry_id),
    )
    db.commit()


def team_user_ids(registry_row) -> list[int]:
    try:
        return json.loads(registry_row['team_user_ids'] or '[]')
    except (json.JSONDecodeError, TypeError):
        return []


from gi_platform.constants import has_full_access


def user_can_access_registry(db, registry_id: int, user_id: int | None, role: str | None) -> bool:
    if has_full_access(role) or role in ('admin', 'specialist'):
        return True
    if not user_id:
        return False
    reg = get_registry(db, registry_id)
    if not reg:
        return False
    if reg['lead_user_id'] == user_id:
        return True
    return user_id in team_user_ids(reg)


def auto_import_enrollment_data(db, enrollment_id: int) -> None:
    """Pre-fill research payload from ward, booking, and procedure reports."""
    enrollment = get_enrollment(db, enrollment_id)
    if not enrollment:
        return
    variables = list_capture_variables(db, enrollment['registry_id'])
    payload = json.loads(enrollment['payload_json'] or '{}')
    auto_fields = _collect_auto_fields(db, enrollment)
    changed = _merge_auto_fields(payload, variables, auto_fields)
    if changed:
        update_enrollment_payload(db, enrollment_id, payload)


def _merge_auto_fields(payload: dict, variables: list, auto_fields: dict) -> bool:
    aliases = {
        'hb': ('hb', 'on_admission_hb', 'lab_hb'),
        'platelet': ('platelet', 'platelets', 'lab_platelets'),
        'inr': ('inr', 'lab_inr'),
        'bilirubin': ('total_bilirubin', 'lab_total_bilirubin'),
        'ggt': ('ggt', 'lab_ggt'),
        'alp': ('alp', 'lab_alp'),
        'wbc': ('tlc', 'lab_wbc'),
        'procedure': ('procedure_type', 'procedure'),
        'impression': ('impression',),
        'procedure_note': ('procedure_note', 'findings'),
        'sedation': ('sedation',),
        'indication': ('indication', 'clinical_notes'),
    }
    changed = False
    for v in variables:
        key = v['code'] or v['name']
        if payload.get(key):
            continue
        src = (v['source_type'] or '').lower().strip()
        candidates = []
        if src:
            candidates.append(src)
            if src in aliases:
                candidates.extend(aliases[src])
        key_lower = key.lower().replace(' ', '_')
        candidates.append(key_lower)
        if key_lower in aliases:
            candidates.extend(aliases[key_lower])
        for cand in candidates:
            val = auto_fields.get(cand)
            if val not in (None, '', []):
                payload[key] = str(val)
                changed = True
                break
    return changed


def _merge_report_table_fields(db, fields: dict, appointment_id: int, procedure_type: str) -> None:
    """Merge denormalized EGD/COL research columns when structured reports exist."""
    pairs = (
        ('upper_gi', 'upper_gi_v2_report', 'upper_gi_research'),
        ('peg_tube', 'upper_gi_v2_report', 'upper_gi_research'),
        ('colonoscopy', 'colonoscopy_v2_report', 'colonoscopy_research'),
        ('polypectomy', 'colonoscopy_v2_report', 'colonoscopy_research'),
    )
    for proc, report_table, research_table in pairs:
        if procedure_type != proc:
            continue
        try:
            report = db.execute(
                f'SELECT id FROM {report_table} WHERE appointment_id = ?',
                (appointment_id,),
            ).fetchone()
        except Exception:
            report = None
        if not report:
            continue
        try:
            rs = db.execute(
                f'SELECT * FROM {research_table} WHERE report_id = ?',
                (report['id'],),
            ).fetchone()
        except Exception:
            rs = None
        if not rs:
            continue
        for key in rs.keys():
            if key in ('id', 'report_id', 'updated_at'):
                continue
            val = rs[key]
            if val not in (None, '', []):
                fields[str(key).lower()] = val
        break


def _collect_auto_fields(db, enrollment) -> dict:
    """Gather demographics, labs, and procedure fields from linked clinical records."""
    fields: dict[str, Any] = {}
    ward_row = None
    if enrollment['ward_patient_id']:
        ward_row = db.execute(
            'SELECT * FROM ward_patient WHERE id = ?', (enrollment['ward_patient_id'],)
        ).fetchone()
    appt = None
    if enrollment['appointment_id']:
        appt = db.execute(
            'SELECT * FROM appointment WHERE id = ?', (enrollment['appointment_id'],)
        ).fetchone()
    mrn = (enrollment['mrn'] or '').strip()
    if ward_row:
        mrn = mrn or (ward_row['mrn'] or '').strip()
        fields.update({
            'mrn': mrn,
            'patient_name': ward_row['patient_name'] or '',
            'age': str(ward_row['age'] or ''),
            'gender': ward_row['gender'] or '',
        })
    if not appt and mrn:
        appt = db.execute(
            'SELECT * FROM appointment WHERE mrn = ? ORDER BY appointment_date DESC LIMIT 1',
            (mrn,),
        ).fetchone()
    if appt:
        fields.setdefault('mrn', appt['mrn'] or mrn)
        fields.setdefault('patient_name', appt['patient_name'] or '')
        fields.setdefault('age', str(appt['age'] or ''))
        fields.setdefault('gender', appt['gender'] or '')
        fields.update({
            'procedure_type': appt['procedure_type'] or '',
            'on_admission_hb': appt['on_admission_hb'] or '',
            'platelet': appt['platelet'] or '',
            'inr': appt['inr'] or '',
            'total_bilirubin': appt['total_bilirubin'] or '',
            'ggt': appt['ggt'] or '',
            'alp': appt['alp'] or '',
            'tlc': appt['tlc'] or '',
            'clinical_notes': appt['clinical_notes'] or '',
            'appointment_date': appt['appointment_date'] or '',
        })
        aid = appt['id']
        proc = (appt['procedure_type'] or '').strip()
        _merge_report_table_fields(db, fields, aid, proc)
        for table, extra_cols in (
            ('ercp_report', (
                'impression', 'procedure_note', 'sedation', 'indication',
                'lab_hb', 'lab_platelets', 'lab_inr', 'lab_total_bilirubin',
                'cholangiogram_findings', 'therapeutic_procedures', 'complications',
            )),
            ('eus_report', ('impression', 'procedure_note', 'sedation', 'anesthesiologist')),
            ('capsule_report', ('impression', 'procedure_note', 'sedation')),
            ('upper_gi_v2_report', ('impression', 'procedure_note', 'payload_json')),
            ('colonoscopy_v2_report', ('impression', 'procedure_note', 'payload_json')),
        ):
            try:
                row = db.execute(
                    f'SELECT * FROM {table} WHERE appointment_id = ?', (aid,)
                ).fetchone()
            except Exception:
                row = None
            if not row:
                continue
            for col in extra_cols:
                if col == 'payload_json':
                    continue
                if col in row.keys() and row[col]:
                    fields[col] = row[col]
            raw = row['payload_json'] if 'payload_json' in row.keys() else None
            if raw:
                try:
                    nested = json.loads(raw or '{}')
                    if isinstance(nested, dict):
                        for nk, nv in nested.items():
                            if nv not in (None, '', [], {}) and nk not in fields:
                                fields[str(nk).lower()] = (
                                    nv if not isinstance(nv, (list, dict)) else json.dumps(nv)
                                )
                except (json.JSONDecodeError, TypeError):
                    pass
    elif mrn:
        fields.setdefault('mrn', mrn)
    return fields
