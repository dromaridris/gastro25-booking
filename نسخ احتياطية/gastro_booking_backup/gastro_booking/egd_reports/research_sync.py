"""Sync research registry columns from structured EGD payload."""

from __future__ import annotations

from datetime import datetime

from advanced_reports.services import parse_payload
from advanced_reports.note_generators import _fmt_list


def _now() -> str:
    return datetime.utcnow().isoformat()


def _val(payload: dict, key: str) -> str:
    raw = payload.get(key)
    if raw is None:
        return ''
    if isinstance(raw, list):
        return _fmt_list(raw)
    return str(raw).strip()


def _ensure_egd_tables_if_needed(dbconn) -> None:
    row = dbconn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='upper_gi_research' LIMIT 1"
    ).fetchone()
    if row:
        return
    from db_schema_registry import ensure_module_schema
    ensure_module_schema(dbconn, 'egd_reports')


def sync_research_row(dbconn, report_id: int, payload_json: str | None) -> None:
    _ensure_egd_tables_if_needed(dbconn)
    payload = parse_payload(payload_json)
    row = dbconn.execute(
        'SELECT id FROM upper_gi_research WHERE report_id = ?', (report_id,)
    ).fetchone()
    fields = {
        'indication_summary': _val(payload, 'indication_category') or _val(payload, 'indication_detail'),
        'urgency': _val(payload, 'urgency'),
        'asa_class': _val(payload, 'asa_class'),
        'd2_reached': _val(payload, 'd2_reached'),
        'retroflexion_performed': _val(payload, 'retroflexion_performed'),
        'procedure_duration_min': _val(payload, 'procedure_duration_min'),
        'variceal_banding_performed': _val(payload, 'variceal_banding_performed'),
        'bands_placed': _val(payload, 'bands_placed'),
        'variceal_grade': _val(payload, 'variceal_grade'),
        'active_bleeding_at_banding': _val(payload, 'active_bleeding_at_banding'),
        'hemostasis_achieved_banding': _val(payload, 'hemostasis_achieved_banding'),
        'hemostasis_performed': _val(payload, 'hemostasis_performed'),
        'forrest_classification': _val(payload, 'forrest_classification'),
        'hemostasis_success': _val(payload, 'hemostasis_success'),
        'sclerotherapy_performed': _val(payload, 'sclerotherapy_performed'),
        'intervention_peg': _val(payload, 'intervention_peg'),
        'intervention_polypectomy': _val(payload, 'intervention_polypectomy'),
        'intervention_dilatation': _val(payload, 'intervention_dilatation'),
        'intervention_emr_esd': _val(payload, 'intervention_emr_esd'),
        'other_interventions_detail': _val(payload, 'other_interventions_detail'),
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
            f'UPDATE upper_gi_research SET {sets} WHERE report_id = ?',
            (*fields.values(), report_id),
        )
    else:
        cols = 'report_id, ' + ', '.join(fields)
        placeholders = '?, ' + ', '.join('?' for _ in fields)
        dbconn.execute(
            f'INSERT INTO upper_gi_research ({cols}) VALUES ({placeholders})',
            (report_id, *fields.values()),
        )


def ensure_research_row(dbconn, report_id: int) -> None:
    _ensure_egd_tables_if_needed(dbconn)
    row = dbconn.execute(
        'SELECT id FROM upper_gi_research WHERE report_id = ?', (report_id,)
    ).fetchone()
    if not row:
        dbconn.execute(
            'INSERT INTO upper_gi_research (report_id, updated_at) VALUES (?, ?)',
            (report_id, _now()),
        )
