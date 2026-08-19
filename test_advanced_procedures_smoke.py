"""Smoke tests for Phase 2/3 advanced endoscopy procedure modules."""

from __future__ import annotations

import os
import sqlite3
import tempfile

from advanced_reports.configs import PROCEDURE_REGISTRY, get_config
from advanced_reports.services import generate_procedure_note, get_or_create, save_report
from advanced_reports.procedure_catalog import PHASE2_PROCEDURES, PHASE3_PROCEDURES
from db_schema_registry import ensure_all_schemas

# Phase 2 keys excluding EGD/COL (have dedicated smoke tests)
PHASE2_KEYS = [p['key'] for p in PHASE2_PROCEDURES if p['key'] not in ('upper_gi_v2', 'colonoscopy_v2')]
PHASE3_KEYS = [p['key'] for p in PHASE3_PROCEDURES]

ALL_KEYS = PHASE2_KEYS + PHASE3_KEYS


class _Row:
    impression = ''
    clinical_plan = ''
    assistants = ''
    sedation = ''
    payload_json = '{}'

    def __getitem__(self, key):
        return getattr(self, key)


def _minimal_payload(cfg: dict) -> dict:
    payload: dict = {}
    for section in cfg.get('sections') or []:
        for field in section.get('fields') or []:
            ftype = field.get('type')
            if ftype == 'yes_no':
                payload[field['key']] = 'No'
            elif ftype == 'dropdown' and field.get('options'):
                payload[field['key']] = field['options'][0]
            elif ftype == 'multi_checkbox':
                payload[field['key']] = []
            elif ftype in ('text', 'long_text'):
                payload[field['key']] = ''
    payload.setdefault('indication_detail', 'Smoke test indication')
    return payload


def main() -> None:
    for key in ALL_KEYS:
        cfg = get_config(key)
        assert cfg['label'], key
        assert cfg.get('sections'), f'{key} has no sections'
        assert cfg['table'], key
        assert key in PROCEDURE_REGISTRY, key

        payload = _minimal_payload(cfg)
        row = _Row()
        row.payload_json = __import__('json').dumps(payload)
        note = generate_procedure_note(key, row)
        assert isinstance(note, str) and len(note) > 0, f'empty note for {key}'

    td = tempfile.mkdtemp()
    db_path = os.path.join(td, 'adv_smoke.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        CREATE TABLE appointment(
            id INTEGER PRIMARY KEY, patient_name TEXT, mrn TEXT, gender TEXT,
            age INT, appointment_date TEXT, procedure_type TEXT,
            on_admission_hb TEXT, platelet TEXT, inr TEXT
        );
        CREATE TABLE endoscopist(id INTEGER PRIMARY KEY, full_name TEXT, is_active INT);
        INSERT INTO endoscopist VALUES (1, 'Dr Test', 1);
        """
    )
    ensure_all_schemas(conn)

    for key in ALL_KEYS:
        cfg = get_config(key)
        proc = cfg['procedure_type']
        conn.execute(
            "INSERT INTO appointment (patient_name, mrn, gender, age, appointment_date, procedure_type) "
            "VALUES (?, 'SMK1', 'M', 50, '2026-08-01', ?)",
            (f'Test {key}', proc),
        )
        appt_id = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
        report, created = get_or_create(conn, key, appt_id, 'admin')
        assert created or report, key
        payload = _minimal_payload(cfg)
        save_report(conn, key, report['id'], {'clinical': payload, 'endoscopist_id': 1})
        conn.commit()
        updated = conn.execute(f"SELECT * FROM {cfg['table']} WHERE id = ?", (report['id'],)).fetchone()
        assert updated, key
        note = generate_procedure_note(key, updated)
        assert note.strip(), f'post-save note empty: {key}'

    print(f'Advanced procedures smoke test passed ({len(ALL_KEYS)} modules)')


if __name__ == '__main__':
    main()
