"""Sync research registry columns from structured colonoscopy payload."""

from __future__ import annotations

from datetime import datetime

from advanced_reports.note_generators import _fmt_list
from advanced_reports.services import parse_payload


def _now() -> str:
    return datetime.utcnow().isoformat()


def _val(payload: dict, key: str) -> str:
    raw = payload.get(key)
    if raw is None:
        return ''
    if isinstance(raw, list):
        return _fmt_list(raw)
    return str(raw).strip()


def _bbps_total(payload: dict) -> str:
    scores = []
    for key in ('bbps_right', 'bbps_transverse', 'bbps_left'):
        raw = _val(payload, key)
        if raw and raw[0].isdigit():
            scores.append(raw[0])
    if len(scores) == 3:
        return str(sum(int(s) for s in scores))
    return ''


def _ensure_colonoscopy_tables_if_needed(dbconn) -> None:
    row = dbconn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='colonoscopy_research' LIMIT 1"
    ).fetchone()
    if row:
        return
    from db_schema_registry import ensure_module_schema
    ensure_module_schema(dbconn, 'colonoscopy_reports')


def sync_research_row(dbconn, report_id: int, payload_json: str | None) -> None:
    _ensure_colonoscopy_tables_if_needed(dbconn)
    payload = parse_payload(payload_json)
    row = dbconn.execute(
        'SELECT id FROM colonoscopy_research WHERE report_id = ?', (report_id,)
    ).fetchone()
    fields = {
        'indication_summary': _val(payload, 'indication_category') or _val(payload, 'indication_detail'),
        'urgency': _val(payload, 'urgency'),
        'asa_class': _val(payload, 'asa_class'),
        'caecum_reached': _val(payload, 'caecum_reached'),
        'ti_intubated': _val(payload, 'ti_intubated'),
        'withdrawal_time_min': _val(payload, 'withdrawal_time_min'),
        'bbps_right': _val(payload, 'bbps_right'),
        'bbps_transverse': _val(payload, 'bbps_transverse'),
        'bbps_left': _val(payload, 'bbps_left'),
        'bbps_total': _bbps_total(payload),
        'prep_regimen': _val(payload, 'prep_regimen'),
        'polypectomy_performed': _val(payload, 'polypectomy_performed'),
        'polyps_resected_count': _val(payload, 'polyps_resected_count'),
        'adenoma_documented': _val(payload, 'adenoma_documented'),
        'immediate_complication': _val(payload, 'immediate_complication'),
        'complication_types': _val(payload, 'complication_types'),
        'procedure_completed': _val(payload, 'procedure_completed'),
        'surveillance_interval': _val(payload, 'surveillance_interval'),
        'follow_up_procedure': _val(payload, 'follow_up_procedure'),
        'updated_at': _now(),
    }
    if row:
        sets = ', '.join(f'{k} = ?' for k in fields)
        dbconn.execute(
            f'UPDATE colonoscopy_research SET {sets} WHERE report_id = ?',
            (*fields.values(), report_id),
        )
    else:
        cols = 'report_id, ' + ', '.join(fields)
        placeholders = '?, ' + ', '.join('?' for _ in fields)
        dbconn.execute(
            f'INSERT INTO colonoscopy_research ({cols}) VALUES ({placeholders})',
            (report_id, *fields.values()),
        )


def ensure_research_row(dbconn, report_id: int) -> None:
    _ensure_colonoscopy_tables_if_needed(dbconn)
    row = dbconn.execute(
        'SELECT id FROM colonoscopy_research WHERE report_id = ?', (report_id,)
    ).fetchone()
    if not row:
        dbconn.execute(
            'INSERT INTO colonoscopy_research (report_id, updated_at) VALUES (?, ?)',
            (report_id, _now()),
        )
