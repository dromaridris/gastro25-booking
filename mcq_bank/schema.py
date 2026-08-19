"""Additive SQLite schema for the MCQ question bank module.

Deliberately isolated from gi_platform: this module has nothing to do with
the clinical history-taking / decision-support system that already lives
there. All tables are prefixed mcqbank_ to make that separation obvious at
a glance in the DB browser too.
"""
from __future__ import annotations

import sqlite3


MCQ_BANK_SCHEMA_VERSION = 2


def init_mcq_bank_schema(db) -> None:
    """Create mcq_bank tables if missing. Accepts a sqlite3 connection."""
    cur = db.cursor()

    cur.executescript("""
        CREATE TABLE IF NOT EXISTS mcqbank_book (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            slug TEXT UNIQUE NOT NULL,
            source_filename TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS mcqbank_chapter (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            book_id INTEGER NOT NULL REFERENCES mcqbank_book(id) ON DELETE CASCADE,
            number INTEGER NOT NULL,
            title TEXT NOT NULL,
            topic TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            UNIQUE(book_id, number)
        );

        -- Generic content item: content_type + payload_json is a deliberate
        -- flexible starting point (agreed architecture decision). High-volume
        -- types can graduate to dedicated tables later as a pure storage-layer
        -- migration, because all reads/writes go through mcq_bank/services.py,
        -- never raw dict access scattered through the codebase.
        CREATE TABLE IF NOT EXISTS mcqbank_content_item (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            book_id INTEGER NOT NULL REFERENCES mcqbank_book(id) ON DELETE CASCADE,
            chapter_id INTEGER NOT NULL REFERENCES mcqbank_chapter(id) ON DELETE CASCADE,
            content_type TEXT NOT NULL DEFAULT 'mcq',
            item_number INTEGER,
            payload_json TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending_review',
            confidence_flag TEXT NOT NULL DEFAULT 'high',
            review_flags_json TEXT NOT NULL DEFAULT '[]',
            review_evidence_json TEXT,
            source_location_json TEXT,
            raw_extracted_text TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );

        CREATE INDEX IF NOT EXISTS idx_mcqbank_content_scope
        ON mcqbank_content_item(book_id, chapter_id, content_type, status);

        CREATE TABLE IF NOT EXISTS mcqbank_extraction_job (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            book_id INTEGER NOT NULL REFERENCES mcqbank_book(id) ON DELETE CASCADE,
            content_type TEXT NOT NULL DEFAULT 'mcq',
            status TEXT NOT NULL DEFAULT 'queued',
            total_units INTEGER NOT NULL DEFAULT 0,
            processed_units INTEGER NOT NULL DEFAULT 0,
            current_step TEXT,
            error_message TEXT,
            started_at TEXT,
            finished_at TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );

        -- Student solving progress. scope_key examples: 'book:3', 'chapter:14'.
        CREATE TABLE IF NOT EXISTS mcqbank_user_cycle (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES user(id) ON DELETE CASCADE,
            scope_key TEXT NOT NULL,
            cycle_number INTEGER NOT NULL DEFAULT 1,
            started_at TEXT DEFAULT (datetime('now')),
            completed_at TEXT,
            UNIQUE(user_id, scope_key, cycle_number)
        );

        CREATE TABLE IF NOT EXISTS mcqbank_user_progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES user(id) ON DELETE CASCADE,
            content_item_id INTEGER NOT NULL REFERENCES mcqbank_content_item(id) ON DELETE CASCADE,
            scope_key TEXT NOT NULL,
            cycle_number INTEGER NOT NULL DEFAULT 1,
            status TEXT NOT NULL DEFAULT 'unseen',
            selected_option TEXT,
            is_correct INTEGER,
            answered_at TEXT,
            UNIQUE(user_id, content_item_id, scope_key, cycle_number)
        );

        CREATE INDEX IF NOT EXISTS idx_mcqbank_progress_lookup
        ON mcqbank_user_progress(user_id, scope_key, cycle_number, status);

        -- Quick quizzes: HOD/admin/specialist/registrar generates an N-question
        -- quiz and assigns it to specific users. Assignment + "My Tasks" surface
        -- is handled via the EXISTING gi_training_assignment + notification
        -- tables (see services.py: assign_quiz_to_users), not duplicated here -
        -- this table just tracks the quiz's own question set and per-user result.
        CREATE TABLE IF NOT EXISTS mcqbank_quiz (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            book_id INTEGER REFERENCES mcqbank_book(id) ON DELETE SET NULL,
            chapter_id INTEGER REFERENCES mcqbank_chapter(id) ON DELETE SET NULL,
            question_count INTEGER NOT NULL DEFAULT 20,
            created_by_id INTEGER REFERENCES user(id),
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS mcqbank_quiz_item (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            quiz_id INTEGER NOT NULL REFERENCES mcqbank_quiz(id) ON DELETE CASCADE,
            content_item_id INTEGER NOT NULL REFERENCES mcqbank_content_item(id) ON DELETE CASCADE,
            position INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS mcqbank_quiz_assignment (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            quiz_id INTEGER NOT NULL REFERENCES mcqbank_quiz(id) ON DELETE CASCADE,
            user_id INTEGER NOT NULL REFERENCES user(id) ON DELETE CASCADE,
            training_assignment_id INTEGER,
            status TEXT NOT NULL DEFAULT 'pending',
            score_correct INTEGER,
            score_total INTEGER,
            completed_at TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            UNIQUE(quiz_id, user_id)
        );

        -- Per-user daily practice goal (optional). Progress resets each
        -- calendar day via daily_solved_date; disabling hides the feature.
        CREATE TABLE IF NOT EXISTS mcqbank_user_settings (
            user_id INTEGER PRIMARY KEY REFERENCES user(id) ON DELETE CASCADE,
            daily_target_enabled INTEGER NOT NULL DEFAULT 0,
            daily_target_count INTEGER NOT NULL DEFAULT 50,
            daily_solved_count INTEGER NOT NULL DEFAULT 0,
            daily_solved_date TEXT,
            updated_at TEXT DEFAULT (datetime('now'))
        );
    """)
    db.commit()
