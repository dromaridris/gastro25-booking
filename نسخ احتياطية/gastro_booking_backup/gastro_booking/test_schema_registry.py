"""Smoke test for central schema registry and EGD table creation."""

import os
import sqlite3
import tempfile

from db_schema_registry import ensure_all_schemas


def test_registry_creates_egd_tables_without_parent():
    """EGD satellite tables must be created even when only appointment exists."""
    td = tempfile.mkdtemp()
    db_path = os.path.join(td, 'registry_smoke.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        CREATE TABLE appointment(
            id INTEGER PRIMARY KEY, patient_name TEXT, mrn TEXT, gender TEXT,
            age INT, appointment_date TEXT, procedure_type TEXT
        );
        CREATE TABLE endoscopist(id INTEGER PRIMARY KEY, full_name TEXT, is_active INT);
        """
    )
    ensure_all_schemas(conn)
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert 'upper_gi_v2_report' in tables, tables
    assert 'upper_gi_research' in tables, tables
    assert 'upper_gi_followup' in tables, tables
    conn.close()
    print('Schema registry smoke test passed')


if __name__ == '__main__':
    test_registry_creates_egd_tables_without_parent()
