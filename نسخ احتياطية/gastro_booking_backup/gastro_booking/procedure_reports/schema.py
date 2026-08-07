"""Procedure report tables — Upper GI, Colonoscopy (Phase 8). Additive only."""

from __future__ import annotations


def init_procedure_report_schema(db) -> None:
    db.executescript("""
        CREATE TABLE IF NOT EXISTS upper_gi_report (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            appointment_id INTEGER NOT NULL UNIQUE,
            report_number TEXT,
            status TEXT NOT NULL DEFAULT 'draft',
            indication TEXT DEFAULT '',
            procedure_detail TEXT DEFAULT '',
            findings_text TEXT DEFAULT '',
            impression TEXT DEFAULT '',
            recommendations TEXT DEFAULT '',
            complications TEXT DEFAULT '',
            endoscopist_id INTEGER,
            procedure_note TEXT DEFAULT '',
            created_by TEXT,
            created_at TEXT,
            updated_at TEXT,
            finalized_by TEXT,
            finalized_at TEXT,
            unlocked_by TEXT,
            unlocked_at TEXT
        );

        CREATE TABLE IF NOT EXISTS colonoscopy_report (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            appointment_id INTEGER NOT NULL UNIQUE,
            report_number TEXT,
            status TEXT NOT NULL DEFAULT 'draft',
            indication TEXT DEFAULT '',
            procedure_detail TEXT DEFAULT '',
            prep_quality TEXT DEFAULT '',
            caecum_reached TEXT DEFAULT '',
            findings_text TEXT DEFAULT '',
            impression TEXT DEFAULT '',
            recommendations TEXT DEFAULT '',
            complications TEXT DEFAULT '',
            endoscopist_id INTEGER,
            procedure_note TEXT DEFAULT '',
            created_by TEXT,
            created_at TEXT,
            updated_at TEXT,
            finalized_by TEXT,
            finalized_at TEXT,
            unlocked_by TEXT,
            unlocked_at TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_upper_gi_appt ON upper_gi_report(appointment_id);
        CREATE INDEX IF NOT EXISTS idx_colonoscopy_appt ON colonoscopy_report(appointment_id);
    """)
    db.commit()
