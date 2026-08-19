"""Smoke test for structured EGD module."""

from advanced_reports.configs import get_config
from advanced_reports.print_metadata import build_egd_metadata_rows, build_unified_print_rows
from egd_reports.narrative import generate_upper_gi_note
import sqlite3
import os
import tempfile

cfg = get_config('upper_gi_v2')
assert cfg['label']
assert cfg.get('print_layout') == 'sidebar_images'
assert any(s['id'] == 'variceal' for s in cfg['sections'])
assert any(s['id'] == 'sclerotherapy' for s in cfg['sections'])

payload = {
    'refer_to': 'GI-ward',
    'chief_complaints': 'Haematemesis and melaena (DCLD/HCV)',
    'sedation_regimen': 'Inj midazolam 2 mg + inj nalbuphine 2 mg',
    'indication_category': ['GI bleeding / anaemia'],
    'indication_detail': 'DCLD/HCV',
    'scope_type': 'GIF-HQ190',
    'd2_reached': 'Yes',
    'oesophagus_normal': 'No',
    'oesophagus_findings': ['Varices', 'Hiatus hernia'],
    'hill_grade': 'Grade III',
    'ge_junction_detail': '38 cm',
    'variceal_banding_performed': 'Yes',
    'evbl_session': '3rd session',
    'bands_placed': '6',
    'hemostasis_achieved_banding': 'Yes',
    'red_wale_markings': 'Yes',
    'variceal_grade': 'Large',
    'sclerotherapy_performed': 'Yes',
    'sclerotherapy_session': '1st session',
    'sclerotherapy_agent': 'Histoacryl 1 cc',
    'sclerotherapy_diluent': 'Inj Lipiodol 0.5 cc',
    'sclerotherapy_site': 'Fundal varix IGV-I',
    'sclerotherapy_hemostasis': 'Yes',
    'stomach_fundus_findings': ['Portal hypertensive gastropathy', 'Fundal varix (IGV)'],
    'stomach_body_findings': ['Portal hypertensive gastropathy'],
    'stomach_antrum_findings': ['Portal hypertensive gastropathy', 'Ulcer'],
    'stomach_antrum_detail': 'Multiple Forrest class III ulcers',
    'duodenum_d1_findings': ['Duodenopathy'],
    'duodenum_d2_findings': ['Duodenopathy'],
    'diagnosis_list': ['Oesophageal varices', 'Gastric / fundal varix', 'Portal hypertensive gastropathy'],
    'clinical_plan': 'Repeat EGD ± EVBL after 3 weeks',
    'intervention_biopsy': 'No',
}


class _Row:
    impression = ''
    clinical_plan = ''
    assistants = 'Dr. Imran Khan'
    sedation = ''


note = generate_upper_gi_note(payload, _Row())
assert 'Oesophagus:' in note
assert 'Fundus:' in note
assert 'Biopsy:' in note
assert 'Refer:' not in note
assert 'Sedation:' not in note
assert 'Complaints:' not in note
assert 'Diagnosis:' not in note
assert 'Advice:' not in note
assert 'Indication category:' not in note
assert 'PROCEDURE DETAILS' not in note

meta = build_egd_metadata_rows(payload, _Row())
meta_labels = {label for label, _ in meta}
assert 'Sedation' not in meta_labels
assert 'Indication' in meta_labels
assert 'D2 reached' in meta_labels

from advanced_reports.note_generators import generate_structured_note
structured = generate_structured_note(cfg, payload, _Row())
assert 'PROCEDURE DETAILS' not in structured
assert 'Refer:' not in structured
assert 'Oesophagus:' in structured
print('EGD smoke test passed')
print('--- sample note ---')
print(note)

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
    INSERT INTO appointment VALUES (1,'Test','MRN1','M',45,'2026-08-01','upper_gi');
    """
)
from db_schema_registry import ensure_all_schemas

ensure_all_schemas(conn)
tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
assert 'upper_gi_v2_report' in tables
assert 'upper_gi_research' in tables
assert 'upper_gi_followup' in tables
