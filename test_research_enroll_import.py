"""Research enrollment auto-import — booking, EGD, and colonoscopy payloads."""

import json
import os
import sqlite3
import tempfile

from gi_platform.research_service import auto_import_enrollment_data, enroll_patient, get_enrollment

fd, path = tempfile.mkstemp(suffix='.db')
os.close(fd)
db = sqlite3.connect(path)
db.row_factory = sqlite3.Row
db.executescript(
    """
    CREATE TABLE gi_research_registry (
        id INTEGER PRIMARY KEY, code TEXT, title TEXT, description TEXT, pi_name TEXT,
        created_by INT, status TEXT, lead_user_id INT, team_user_ids TEXT,
        assigned_by_hod_id INT, hod_status TEXT, hod_review_note TEXT, updated_at TEXT
    );
    CREATE TABLE gi_research_variable (
        id INTEGER PRIMARY KEY, registry_id INT, name TEXT, var_type TEXT, required INT,
        options_json TEXT, code TEXT, source_type TEXT, sort_order INT,
        approval_status TEXT, proposed_by INT, review_note TEXT
    );
    CREATE TABLE gi_research_enrollment (
        id INTEGER PRIMARY KEY, registry_id INT, ward_patient_id INT, appointment_id INT,
        mrn TEXT, payload_json TEXT, enrolled_by INT, responsible_user_id INT,
        status TEXT DEFAULT 'active', enrolled_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE appointment (
        id INTEGER PRIMARY KEY, patient_name TEXT, gender TEXT, age INT, phone TEXT, mrn TEXT,
        clinical_notes TEXT, on_admission_hb TEXT, platelet TEXT, inr TEXT,
        total_bilirubin TEXT, ggt TEXT, alp TEXT, tlc TEXT, comorbs_etiology TEXT,
        referral TEXT, procedure_type TEXT, appointment_date TEXT,
        is_bleeding INT, is_override INT, no_show INT,
        booked_by_username TEXT, booked_by_role TEXT, created_at TEXT
    );
    CREATE TABLE ward_patient (
        id INTEGER PRIMARY KEY, patient_name TEXT, mrn TEXT, age INT, gender TEXT, appointment_id INT
    );
    CREATE TABLE upper_gi_v2_report (
        id INTEGER PRIMARY KEY, appointment_id INT UNIQUE, payload_json TEXT,
        impression TEXT, procedure_note TEXT
    );
    CREATE TABLE upper_gi_research (
        id INTEGER PRIMARY KEY, report_id INT UNIQUE, d2_reached TEXT, intervention_peg TEXT,
        sclerotherapy_performed TEXT, updated_at TEXT
    );
    CREATE TABLE colonoscopy_v2_report (
        id INTEGER PRIMARY KEY, appointment_id INT UNIQUE, payload_json TEXT,
        impression TEXT, procedure_note TEXT
    );
    CREATE TABLE colonoscopy_research (
        id INTEGER PRIMARY KEY, report_id INT UNIQUE, caecum_reached TEXT,
        polypectomy_performed TEXT, polyps_resected_count TEXT, updated_at TEXT
    );
    """
)
db.execute(
    "INSERT INTO gi_research_registry (id, code, title, status) VALUES (5, 'T', 'Test', 'active')"
)
db.execute(
    "INSERT INTO gi_research_variable (registry_id, name, var_type, code, source_type, approval_status) "
    "VALUES (5, 'HB', 'text', 'hb', 'hb', 'approved'),"
    "(5, 'PEG', 'text', 'intervention_peg', 'intervention_peg', 'approved'),"
    "(5, 'Polypectomy', 'text', 'polypectomy_performed', 'polypectomy_performed', 'approved')"
)
db.execute(
    """
    INSERT INTO appointment (
        id, patient_name, gender, age, phone, mrn, procedure_type, appointment_date,
        on_admission_hb, is_bleeding, is_override, no_show, booked_by_username,
        booked_by_role, created_at
    ) VALUES (1, 'Ali', 'M', 40, '', 'MRN123', 'peg_tube', '2026-01-01', '12.5',
              0, 0, 0, 'a', 'admin', 'now')
    """
)
db.execute(
    "INSERT INTO upper_gi_v2_report (id, appointment_id, payload_json) "
    "VALUES (10, 1, '{\"intervention_peg\":\"yes\",\"d2_reached\":\"yes\"}')"
)
db.execute(
    "INSERT INTO upper_gi_research (report_id, d2_reached, intervention_peg, updated_at) "
    "VALUES (10, 'yes', 'yes', 'now')"
)
db.execute(
    """
    INSERT INTO appointment (
        id, patient_name, gender, age, phone, mrn, procedure_type, appointment_date,
        on_admission_hb, is_bleeding, is_override, no_show, booked_by_username,
        booked_by_role, created_at
    ) VALUES (2, 'Sara', 'F', 55, '', 'MRN456', 'polypectomy', '2026-01-02', '11.0',
              0, 0, 0, 'a', 'admin', 'now')
    """
)
db.execute(
    "INSERT INTO colonoscopy_v2_report (id, appointment_id, payload_json) "
    "VALUES (20, 2, '{\"polypectomy_performed\":\"yes\",\"polyps_resected_count\":\"2\"}')"
)
db.execute(
    "INSERT INTO colonoscopy_research (report_id, caecum_reached, polypectomy_performed, "
    "polyps_resected_count, updated_at) VALUES (20, 'yes', 'yes', '2', 'now')"
)

eid = enroll_patient(db, 5, mrn='MRN123', appointment_id=1, enrolled_by=1)
auto_import_enrollment_data(db, eid)
payload = json.loads(get_enrollment(db, eid)['payload_json'])
assert payload.get('hb') == '12.5', payload
assert payload.get('intervention_peg') == 'yes', payload

eid2 = enroll_patient(db, 5, mrn='MRN456', appointment_id=2, enrolled_by=1)
auto_import_enrollment_data(db, eid2)
payload2 = json.loads(get_enrollment(db, eid2)['payload_json'])
assert payload2.get('polypectomy_performed') == 'yes', payload2

print('research enroll auto-import OK (booking + EGD + COL)')
