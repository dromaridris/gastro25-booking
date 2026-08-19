"""Research enrollment lifecycle — withdraw, duplicate MRN, draft block."""

import os
import sqlite3
import tempfile

from gi_platform.research_service import (
    enrollment_exists,
    enroll_patient,
    registry_ready_for_enrollment,
    withdraw_enrollment,
)

fd, path = tempfile.mkstemp(suffix='.db')
os.close(fd)
db = sqlite3.connect(path)
db.row_factory = sqlite3.Row
db.executescript(
    """
    CREATE TABLE gi_research_registry (
        id INTEGER PRIMARY KEY, code TEXT, title TEXT, status TEXT,
        lead_user_id INT, team_user_ids TEXT, hod_status TEXT
    );
    CREATE TABLE gi_research_enrollment (
        id INTEGER PRIMARY KEY, registry_id INT, ward_patient_id INT, appointment_id INT,
        mrn TEXT, payload_json TEXT DEFAULT '{}', enrolled_by INT, responsible_user_id INT,
        status TEXT DEFAULT 'active', enrolled_at TEXT
    );
    """
)
db.execute(
    "INSERT INTO gi_research_registry (id, code, title, status, hod_status) "
    "VALUES (1, 'A', 'Active', 'active', 'approved')"
)
db.execute(
    "INSERT INTO gi_research_registry (id, code, title, status, hod_status) "
    "VALUES (2, 'D', 'Draft', 'draft', 'pending_approval')"
)
reg_active = db.execute('SELECT * FROM gi_research_registry WHERE id=1').fetchone()
reg_draft = db.execute('SELECT * FROM gi_research_registry WHERE id=2').fetchone()
assert registry_ready_for_enrollment(reg_active)
assert not registry_ready_for_enrollment(reg_draft)

eid = enroll_patient(db, 1, mrn='X1', enrolled_by=1)
assert enrollment_exists(db, 1, mrn='X1')
assert withdraw_enrollment(db, eid)
row = db.execute('SELECT status FROM gi_research_enrollment WHERE id=?', (eid,)).fetchone()
assert row['status'] == 'withdrawn'
assert not enrollment_exists(db, 1, mrn='X1')
print('Research lifecycle tests passed')
