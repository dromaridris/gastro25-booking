"""Additive SQLite schema for Clinical Intelligence encounters (ci_ prefix)."""

from __future__ import annotations

import sqlite3

CI_SCHEMA_VERSION = 2


def init_clinical_intelligence_schema(db: sqlite3.Connection) -> None:
    cur = db.cursor()
    cur.executescript(
        """
        CREATE TABLE IF NOT EXISTS ci_encounter (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            complaint_code TEXT NOT NULL,
            patient_label TEXT,
            ward_patient_id INTEGER,
            status TEXT NOT NULL DEFAULT 'draft',
            phase TEXT NOT NULL DEFAULT 'history',
            urgency_flag TEXT,
            created_by INTEGER,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now')),
            summary_json TEXT,
            notes TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_ci_encounter_status
        ON ci_encounter(status, updated_at);

        CREATE TABLE IF NOT EXISTS ci_history_answer (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            encounter_id INTEGER NOT NULL REFERENCES ci_encounter(id) ON DELETE CASCADE,
            question_id TEXT NOT NULL,
            dedupe_key TEXT,
            answer_text TEXT,
            answer_json TEXT,
            section_key TEXT,
            skipped INTEGER NOT NULL DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now')),
            UNIQUE(encounter_id, question_id)
        );

        CREATE INDEX IF NOT EXISTS idx_ci_history_encounter
        ON ci_history_answer(encounter_id);

        CREATE TABLE IF NOT EXISTS ci_exam_finding (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            encounter_id INTEGER NOT NULL REFERENCES ci_encounter(id) ON DELETE CASCADE,
            system_key TEXT,
            sign_code TEXT,
            status TEXT NOT NULL DEFAULT 'not_examined',
            note TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now')),
            UNIQUE(encounter_id, sign_code)
        );

        CREATE INDEX IF NOT EXISTS idx_ci_exam_encounter
        ON ci_exam_finding(encounter_id);

        CREATE TABLE IF NOT EXISTS ci_encounter_draft (
            encounter_id INTEGER PRIMARY KEY REFERENCES ci_encounter(id) ON DELETE CASCADE,
            draft_json TEXT NOT NULL DEFAULT '{}',
            updated_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS ci_ix_result (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            encounter_id INTEGER NOT NULL REFERENCES ci_encounter(id) ON DELETE CASCADE,
            investigation_code TEXT NOT NULL,
            result_label TEXT NOT NULL,
            note TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now')),
            UNIQUE(encounter_id, investigation_code)
        );

        CREATE INDEX IF NOT EXISTS idx_ci_ix_encounter
        ON ci_ix_result(encounter_id);

        CREATE TABLE IF NOT EXISTS ci_research_item (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            encounter_id INTEGER,
            kind TEXT NOT NULL DEFAULT 'hypothesis',
            title TEXT NOT NULL,
            hypothesis TEXT,
            payload_json TEXT,
            status TEXT NOT NULL DEFAULT 'open',
            created_by INTEGER,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS ci_knowledge_event (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT NOT NULL,
            payload_json TEXT,
            created_by INTEGER,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS ci_ai_assist_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            encounter_id INTEGER,
            mode TEXT,
            payload_json TEXT,
            created_by INTEGER,
            created_at TEXT DEFAULT (datetime('now'))
        );
        """
    )
    db.commit()
