"""Smoke test for structured colonoscopy module."""

from advanced_reports.configs import get_config
from advanced_reports.note_generators import generate_structured_note
from advanced_reports.print_metadata import build_colonoscopy_metadata_rows, build_unified_print_rows
from advanced_reports.services import generate_procedure_note, print_procedure_fields
from colonoscopy_reports.narrative import generate_colonoscopy_note
from db_schema_registry import ensure_all_schemas
import sqlite3
import os
import tempfile

cfg = get_config('colonoscopy_v2')
assert cfg['label']
assert cfg.get('print_layout') == 'sidebar_images'
assert any(s['id'] == 'polypectomy' for s in cfg['sections'])

payload = {
    'refer_to': 'GI-ward',
    'chief_complaints': 'Change in bowel habit and rectal bleeding',
    'sedation_regimen': 'Inj midazolam 2 mg + inj nalbuphine 2 mg',
    'indication_category': ['Symptoms (bleeding, change in bowel habit, pain)'],
    'caecum_reached': 'Yes',
    'ti_intubated': 'Yes',
    'bbps_right': '2 — Minor residual staining',
    'bbps_transverse': '3 — Entire mucosa well seen',
    'bbps_left': '2 — Minor residual staining',
    'withdrawal_time_min': '9',
    'prep_regimen': 'PEG-based prep',
    'scope_type': 'Variable stiffness colonoscope',
    'ascending_normal': 'No',
    'ascending_findings': ['Polyp'],
    'ascending_detail': '6 mm sessile polyp — cold snare polypectomy, complete resection',
    'sigmoid_normal': 'Yes',
    'rectum_normal': 'Yes',
    'polypectomy_performed': 'Yes',
    'polyps_resected_count': '1',
    'polypectomy_technique': ['Cold snare'],
    'adenoma_documented': 'Yes',
    'specimens_to_histology': 'Jar A — ascending polyp',
    'diagnosis_list': ['Colonic polyp(s) — adenomatous'],
    'clinical_plan': 'Await histology. Surveillance colonoscopy per pathology and BSG guidelines.',
    'immediate_complication': 'No',
}


class _Row:
    impression = ''
    clinical_plan = ''
    assistants = 'Dr. Imran Khan'
    sedation = ''


note = generate_colonoscopy_note(payload, _Row())
assert 'Ascending colon:' in note
assert 'Polypectomy' in note
assert 'Refer:' not in note
assert 'Sedation:' not in note
assert 'Caecum reached' not in note
assert 'BBPS' not in note
assert 'Procedure:' not in note
assert 'Diagnosis:' not in note
assert 'Advice:' not in note
assert 'PROCEDURE DETAILS' not in note
assert 'Indication category:' not in note

meta = build_colonoscopy_metadata_rows(payload, _Row())
meta_labels = {label for label, _ in meta}
assert 'Sedation' not in meta_labels
assert 'Chief complaints' not in meta_labels
assert 'Indication' in meta_labels
assert 'BBPS (R / T / L)' in meta_labels

structured = generate_structured_note(cfg, payload, _Row())
assert 'PROCEDURE DETAILS' not in structured
assert 'Refer:' not in structured
assert 'Ascending colon:' in structured

r = {'payload_json': __import__('json').dumps(payload), 'impression': '', 'clinical_plan': '', 'assistants': '', 'sedation': '', 'technician': ''}

class _Appt:
    patient_name = 'Test'
    mrn = 'MRN1'
    age = 55
    gender = 'Male'
    appointment_date = '2026-07-31'
    referral = ''

unified = build_unified_print_rows('colonoscopy_v2', r, _Appt(), cfg, assistants_lines=[])
unified_labels = [label for label, _ in unified]
assert unified_labels.count('Sedation') == 1
assert unified_labels.count('Indication') == 1
assert 'Chief complaints' not in unified_labels

assert 'Refer:' not in generate_procedure_note('colonoscopy_v2', r)
assert 'Ascending colon:' in generate_procedure_note('colonoscopy_v2', r)
fields = print_procedure_fields('colonoscopy_v2', r)
assert not any(label == 'Sedation' for label, _ in fields)
assert any(label == 'Indication' for label, _ in fields)

td = tempfile.mkdtemp()
db_path = os.path.join(td, 't.db')
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
conn.executescript(
    """
    CREATE TABLE appointment(
        id INTEGER PRIMARY KEY, patient_name TEXT, mrn TEXT, gender TEXT,
        age INT, appointment_date TEXT, procedure_type TEXT
    );
    CREATE TABLE endoscopist(id INTEGER PRIMARY KEY, full_name TEXT, is_active INT);
    INSERT INTO appointment VALUES (1,'Test','MRN1','M',55,'2026-08-01','colonoscopy');
    """
)
ensure_all_schemas(conn)
tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
assert 'colonoscopy_v2_report' in tables
assert 'colonoscopy_research' in tables
assert 'colonoscopy_followup' in tables
print('Colonoscopy smoke test passed')
print('--- sample note ---')
print(note)
