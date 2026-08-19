"""Business logic for advanced endoscopy reports."""

from __future__ import annotations

import json
import os
from datetime import datetime

import report_service
from advanced_reports.configs import PROCEDURE_REGISTRY, get_config
from advanced_reports.note_generators import generate_capsule_note, generate_eus_note, generate_structured_note

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.environ.get('GASTRO_DATA_DIR', BASE_DIR)

IMAGE_MAX_DIMENSION = 1600
IMAGE_JPEG_QUALITY = 78


def _now() -> str:
    return datetime.utcnow().isoformat()


def image_dir(cfg: dict) -> str:
    path = os.path.join(DATA_DIR, cfg['image_dir'])
    os.makedirs(path, exist_ok=True)
    return path


def parse_payload(raw: str | None) -> dict:
    if not raw:
        return {}
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, TypeError):
        return {}


def serialize_payload(data: dict) -> str:
    return json.dumps(data or {}, ensure_ascii=False)


def get_or_create(db, procedure_key: str, appointment_id: int, username: str):
    cfg = get_config(procedure_key)
    report, created = report_service.get_or_create_report(
        db, cfg['table'], 'appointment_id', appointment_id, username,
    )
    if created:
        payload = {}
        appt = db.execute('SELECT * FROM appointment WHERE id = ?', (appointment_id,)).fetchone()
        if appt:
            payload['prefill_labs'] = {
                'hb': appt['on_admission_hb'] or '',
                'platelet': appt['platelet'] or '',
                'inr': appt['inr'] or '',
            }
        db.execute(
            f"UPDATE {cfg['table']} SET payload_json = ? WHERE id = ?",
            (serialize_payload(payload), report['id']),
        )
        report = db.execute(f"SELECT * FROM {cfg['table']} WHERE id = ?", (report['id'],)).fetchone()
    return report, created


def save_report(db, procedure_key: str, report_id: int, payload: dict) -> None:
    """Persist report fields. Only keys present in payload are updated."""
    cfg = get_config(procedure_key)
    fields = {}

    if 'clinical' in payload:
        clinical_payload = payload['clinical'] if isinstance(payload.get('clinical'), dict) else {}
        fields['payload_json'] = serialize_payload(clinical_payload)

    if 'endoscopist_id' in payload:
        eid = payload.get('endoscopist_id')
        try:
            fields['endoscopist_id'] = int(eid) if eid not in (None, '', 'null') else None
        except (TypeError, ValueError):
            fields['endoscopist_id'] = None

    for key in ('technician', 'assistants', 'procedure_note', 'impression', 'clinical_plan'):
        if key in payload:
            fields[key] = (payload.get(key) or '').strip()

    if cfg.get('has_anesthesiologist') and 'anesthesiologist' in payload:
        fields['anesthesiologist'] = (payload.get('anesthesiologist') or '').strip()

    if cfg.get('has_sedation') and 'sedation' in payload:
        fields['sedation'] = payload.get('sedation') or ''

    # Sync impression/plan from clinical synthesis when explicitly saved together
    if 'clinical' in payload and isinstance(payload.get('clinical'), dict):
        clinical_payload = payload['clinical']
        if 'impression' not in payload and clinical_payload.get('impression_primary'):
            fields.setdefault('impression', str(clinical_payload['impression_primary']).strip())
        if 'clinical_plan' not in payload and clinical_payload.get('clinical_plan'):
            fields.setdefault('clinical_plan', str(clinical_payload['clinical_plan']).strip())

    if fields:
        report_service.save_fields(db, cfg['table'], report_id, fields)

    if procedure_key == 'upper_gi_v2':
        from egd_reports.research_sync import ensure_research_row, sync_research_row
        row = db.execute(
            f"SELECT payload_json FROM {cfg['table']} WHERE id = ?", (report_id,)
        ).fetchone()
        if row:
            ensure_research_row(db, report_id)
            sync_research_row(db, report_id, row['payload_json'])

    if procedure_key == 'colonoscopy_v2':
        from colonoscopy_reports.research_sync import ensure_research_row, sync_research_row
        row = db.execute(
            f"SELECT payload_json FROM {cfg['table']} WHERE id = ?", (report_id,)
        ).fetchone()
        if row:
            ensure_research_row(db, report_id)
            sync_research_row(db, report_id, row['payload_json'])


def _fmt_list(val) -> str:
    if isinstance(val, list):
        return ', '.join(str(v).strip() for v in val if str(v).strip())
    if isinstance(val, str) and val.strip():
        return val.strip()
    return ''


def _section_lines(cfg: dict, payload: dict) -> list[tuple[str, str]]:
    lines = []
    for section in cfg['sections']:
        for field in section['fields']:
            key = field['key']
            val = payload.get(key)
            if val in (None, '', [], {}):
                continue
            if field['type'] == 'multi_checkbox':
                text = _fmt_list(val)
            else:
                text = str(val).strip()
            if text:
                lines.append((field['label'], text))
    return lines


def _is_egd_procedure(procedure_key: str, cfg: dict) -> bool:
    return (
        procedure_key == 'upper_gi_v2'
        or cfg.get('key') == 'upper_gi_v2'
        or cfg.get('table') == 'upper_gi_v2_report'
        or (cfg.get('procedure_type') == 'upper_gi' and cfg.get('table') == 'upper_gi_v2_report')
    )


def _is_colonoscopy_procedure(procedure_key: str, cfg: dict) -> bool:
    return (
        procedure_key == 'colonoscopy_v2'
        or cfg.get('key') == 'colonoscopy_v2'
        or cfg.get('table') == 'colonoscopy_v2_report'
        or (cfg.get('procedure_type') == 'colonoscopy' and cfg.get('table') == 'colonoscopy_v2_report')
    )


def generate_procedure_note(procedure_key: str, report_row) -> str:
    cfg = get_config(procedure_key)
    payload = parse_payload(report_row['payload_json'])

    if procedure_key == 'capsule':
        return generate_capsule_note(payload, report_row)

    if procedure_key == 'eus':
        return generate_eus_note(payload, report_row)

    if _is_egd_procedure(procedure_key, cfg):
        from egd_reports.narrative import generate_upper_gi_note
        return generate_upper_gi_note(payload, report_row)

    if _is_colonoscopy_procedure(procedure_key, cfg):
        from colonoscopy_reports.narrative import generate_colonoscopy_note
        return generate_colonoscopy_note(payload, report_row)

    return generate_structured_note(cfg, payload, report_row)


def print_procedure_fields(procedure_key: str, report_row) -> list[tuple[str, str]]:
    cfg = get_config(procedure_key)
    if _is_egd_procedure(procedure_key, cfg) or _is_colonoscopy_procedure(procedure_key, cfg):
        from advanced_reports.print_metadata import build_print_metadata
        return build_print_metadata(procedure_key, report_row)
    payload = parse_payload(report_row['payload_json'])
    return _section_lines(cfg, payload)


def procedure_key_for_type(procedure_type: str) -> str | None:
    for key, cfg in PROCEDURE_REGISTRY.items():
        allowed = cfg.get('booking_procedure_types') or (cfg['procedure_type'],)
        if procedure_type in allowed:
            return key
    return None


def appointment_matches_procedure(cfg: dict, procedure_type: str) -> bool:
    allowed = cfg.get('booking_procedure_types') or (cfg['procedure_type'],)
    return procedure_type in allowed
