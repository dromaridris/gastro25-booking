"""Additive SQLite schema for integrated GI branches — never drops Gastro25 tables."""

from __future__ import annotations

import sqlite3


GI_SCHEMA_VERSION = 2


def init_gi_schema_db(db) -> None:
    """Create GI integration tables if missing. Accepts sqlite3 connection."""
    cur = db.cursor()

    cur.executescript("""
        CREATE TABLE IF NOT EXISTS gi_meta (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS gi_knowledge_object (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            slug TEXT UNIQUE NOT NULL,
            title TEXT NOT NULL,
            object_type TEXT NOT NULL DEFAULT 'concept',
            status TEXT NOT NULL DEFAULT 'draft',
            specialty TEXT DEFAULT 'gastroenterology',
            summary TEXT,
            body_json TEXT,
            tags_json TEXT DEFAULT '[]',
            created_by INTEGER,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now')),
            published_at TEXT
        );

        CREATE TABLE IF NOT EXISTS gi_knowledge_link (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_id INTEGER NOT NULL,
            target_id INTEGER NOT NULL,
            link_type TEXT NOT NULL,
            weight REAL DEFAULT 1.0,
            metadata_json TEXT,
            FOREIGN KEY (source_id) REFERENCES gi_knowledge_object(id),
            FOREIGN KEY (target_id) REFERENCES gi_knowledge_object(id)
        );

        CREATE TABLE IF NOT EXISTS gi_knowledge_activation (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            object_id INTEGER NOT NULL,
            requested_by INTEGER,
            status TEXT NOT NULL DEFAULT 'pending',
            notes TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            resolved_at TEXT,
            FOREIGN KEY (object_id) REFERENCES gi_knowledge_object(id)
        );

        CREATE TABLE IF NOT EXISTS gi_research_registry (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            title TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'draft',
            pi_name TEXT,
            description TEXT,
            inclusion_json TEXT DEFAULT '{}',
            created_by INTEGER,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS gi_research_variable (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            registry_id INTEGER NOT NULL,
            code TEXT,
            name TEXT NOT NULL,
            var_type TEXT NOT NULL DEFAULT 'text',
            source_type TEXT,
            sort_order INTEGER DEFAULT 0,
            required INTEGER NOT NULL DEFAULT 0,
            options_json TEXT,
            FOREIGN KEY (registry_id) REFERENCES gi_research_registry(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS gi_research_enrollment (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            registry_id INTEGER NOT NULL,
            ward_patient_id INTEGER,
            appointment_id INTEGER,
            mrn TEXT,
            payload_json TEXT DEFAULT '{}',
            enrolled_by INTEGER,
            enrolled_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (registry_id) REFERENCES gi_research_registry(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS gi_history_session (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ward_patient_id INTEGER,
            appointment_id INTEGER,
            mrn TEXT,
            status TEXT NOT NULL DEFAULT 'open',
            chief_complaint TEXT,
            complaint_code TEXT,
            created_by INTEGER,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS gi_history_answer (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            question_key TEXT NOT NULL,
            answer_text TEXT,
            answer_json TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (session_id) REFERENCES gi_history_session(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS gi_history_narrative (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL UNIQUE,
            narrative_text TEXT NOT NULL,
            sections_json TEXT,
            generated_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (session_id) REFERENCES gi_history_session(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS gi_medication_entry (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER,
            ward_patient_id INTEGER,
            drug_name TEXT NOT NULL,
            dose TEXT,
            frequency TEXT,
            route TEXT,
            notes TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (session_id) REFERENCES gi_history_session(id) ON DELETE SET NULL
        );

        CREATE TABLE IF NOT EXISTS gi_ai_session (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ward_patient_id INTEGER,
            session_type TEXT NOT NULL DEFAULT 'clinical_ai',
            status TEXT NOT NULL DEFAULT 'open',
            created_by INTEGER,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS gi_ai_request_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            prompt_text TEXT NOT NULL,
            response_text TEXT,
            provider TEXT DEFAULT 'stub',
            tokens_in INTEGER DEFAULT 0,
            tokens_out INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (session_id) REFERENCES gi_ai_session(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS gi_cds_assessment (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER,
            ward_patient_id INTEGER,
            context_json TEXT NOT NULL,
            result_json TEXT NOT NULL,
            created_by INTEGER,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (session_id) REFERENCES gi_history_session(id) ON DELETE SET NULL
        );

        CREATE TABLE IF NOT EXISTS gi_investigation_suggestion (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER,
            name TEXT NOT NULL,
            rationale TEXT,
            priority TEXT DEFAULT 'routine',
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (session_id) REFERENCES gi_history_session(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS gi_investigation_order (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            ward_patient_id INTEGER,
            order_type TEXT NOT NULL,
            item_code TEXT,
            item_name TEXT NOT NULL,
            custom_note TEXT,
            status TEXT NOT NULL DEFAULT 'pending',
            assigned_role TEXT DEFAULT 'house_officer',
            created_by INTEGER,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (session_id) REFERENCES gi_history_session(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS gi_clinical_score_result (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER,
            score_name TEXT NOT NULL,
            score_value REAL,
            interpretation TEXT,
            inputs_json TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (session_id) REFERENCES gi_history_session(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS gi_import_job (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_type TEXT NOT NULL,
            filename TEXT,
            status TEXT NOT NULL DEFAULT 'queued',
            summary_json TEXT,
            error_text TEXT,
            created_by INTEGER,
            created_at TEXT DEFAULT (datetime('now')),
            finished_at TEXT
        );

        CREATE TABLE IF NOT EXISTS gi_workforce_task (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ward_patient_id INTEGER NOT NULL,
            task_type TEXT NOT NULL,
            assigned_role TEXT,
            assigned_user_id INTEGER,
            status TEXT NOT NULL DEFAULT 'pending',
            title TEXT NOT NULL,
            notes TEXT,
            created_by INTEGER,
            created_at TEXT DEFAULT (datetime('now')),
            completed_at TEXT,
            FOREIGN KEY (ward_patient_id) REFERENCES ward_patient(id)
        );

        CREATE INDEX IF NOT EXISTS idx_gi_knowledge_status ON gi_knowledge_object(status);
        CREATE INDEX IF NOT EXISTS idx_gi_knowledge_type ON gi_knowledge_object(object_type);
        CREATE INDEX IF NOT EXISTS idx_gi_research_status ON gi_research_registry(status);
        CREATE INDEX IF NOT EXISTS idx_gi_history_patient ON gi_history_session(ward_patient_id);
        CREATE INDEX IF NOT EXISTS idx_gi_ai_patient ON gi_ai_session(ward_patient_id);

        CREATE TABLE IF NOT EXISTS gi_patient_identity (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mrn TEXT NOT NULL UNIQUE,
            patient_name TEXT,
            ward_patient_id INTEGER,
            appointment_id INTEGER,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS gi_audit_event (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action TEXT NOT NULL,
            entity_type TEXT NOT NULL,
            entity_id TEXT,
            user_id INTEGER,
            details_json TEXT DEFAULT '{}',
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS gi_knowledge_provenance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            object_id INTEGER NOT NULL,
            source_type TEXT NOT NULL DEFAULT 'manual',
            source_filename TEXT,
            import_job_id INTEGER,
            author TEXT,
            grade_level TEXT,
            notes TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (object_id) REFERENCES gi_knowledge_object(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS ward_discharge_summary (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ward_patient_id INTEGER NOT NULL,
            admission_id INTEGER,
            summary_text TEXT NOT NULL,
            follow_up_plan TEXT,
            discharged_by INTEGER,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (ward_patient_id) REFERENCES ward_patient(id)
        );

        CREATE INDEX IF NOT EXISTS idx_gi_audit_entity ON gi_audit_event(entity_type, entity_id);
        CREATE INDEX IF NOT EXISTS idx_gi_patient_mrn ON gi_patient_identity(mrn);

        CREATE TABLE IF NOT EXISTS gi_portfolio_entry (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            ward_patient_id INTEGER,
            session_id INTEGER,
            activity_type TEXT NOT NULL,
            title TEXT NOT NULL,
            details_json TEXT DEFAULT '{}',
            verified INTEGER NOT NULL DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS gi_management_plan (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            ward_patient_id INTEGER,
            plan_text TEXT NOT NULL,
            approval_status TEXT NOT NULL DEFAULT 'pending_registrar',
            created_by INTEGER,
            approved_by INTEGER,
            approved_at TEXT,
            rejection_note TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (session_id) REFERENCES gi_history_session(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_gi_portfolio_user ON gi_portfolio_entry(user_id);
        CREATE INDEX IF NOT EXISTS idx_gi_plan_status ON gi_management_plan(approval_status);

        CREATE TABLE IF NOT EXISTS gi_user_permission (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            permission_code TEXT NOT NULL,
            granted_by INTEGER,
            granted_at TEXT DEFAULT (datetime('now')),
            UNIQUE(user_id, permission_code)
        );

        CREATE TABLE IF NOT EXISTS gi_logbook_evaluation (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            portfolio_entry_id INTEGER NOT NULL,
            evaluator_id INTEGER NOT NULL,
            competency_domain TEXT NOT NULL,
            score INTEGER NOT NULL CHECK(score BETWEEN 1 AND 5),
            note TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (portfolio_entry_id) REFERENCES gi_portfolio_entry(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS gi_duty_roster_period (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            roster_type TEXT NOT NULL,
            year_month TEXT NOT NULL,
            title TEXT,
            status TEXT NOT NULL DEFAULT 'draft',
            created_by INTEGER,
            published_by INTEGER,
            published_at TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            UNIQUE(roster_type, year_month)
        );

        CREATE TABLE IF NOT EXISTS gi_duty_roster_shift (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            period_id INTEGER NOT NULL,
            roster_date TEXT NOT NULL,
            shift_type TEXT NOT NULL DEFAULT 'on_call',
            notes TEXT,
            FOREIGN KEY (period_id) REFERENCES gi_duty_roster_period(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS gi_duty_roster_assignment (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            shift_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            FOREIGN KEY (shift_id) REFERENCES gi_duty_roster_shift(id) ON DELETE CASCADE,
            UNIQUE(shift_id, user_id)
        );

        CREATE TABLE IF NOT EXISTS gi_attendance_record (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            attendance_date TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'absent',
            activity_count INTEGER NOT NULL DEFAULT 0,
            computed_at TEXT DEFAULT (datetime('now')),
            UNIQUE(user_id, attendance_date)
        );

        CREATE TABLE IF NOT EXISTS gi_attendance_adjustment (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            adjustment_date TEXT NOT NULL,
            adjustment_type TEXT NOT NULL DEFAULT 'leave',
            hours REAL NOT NULL DEFAULT 8,
            notes TEXT,
            approved_by_id INTEGER,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS gi_user_notification (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            body TEXT,
            link_url TEXT,
            is_read INTEGER NOT NULL DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS gi_training_assignment (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            assignment_type TEXT NOT NULL,
            source_module TEXT NOT NULL,
            source_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            details TEXT,
            session_date TEXT,
            training_route TEXT,
            status TEXT NOT NULL DEFAULT 'pending',
            assigned_by_id INTEGER,
            created_at TEXT DEFAULT (datetime('now')),
            completed_at TEXT,
            FOREIGN KEY (user_id) REFERENCES user(id)
        );

        CREATE TABLE IF NOT EXISTS gi_gov_incident (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            incident_date TEXT NOT NULL,
            category TEXT NOT NULL,
            severity TEXT NOT NULL,
            description TEXT NOT NULL,
            mrn TEXT,
            patient_name TEXT,
            root_cause TEXT,
            corrective_action TEXT,
            preventive_action TEXT,
            status TEXT NOT NULL DEFAULT 'open',
            reported_by_id INTEGER,
            reviewer_id INTEGER,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS gi_gov_mm_case (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_summary TEXT NOT NULL,
            mrn TEXT,
            patient_name TEXT,
            presentation_date TEXT,
            discussion_notes TEXT,
            lessons_learned TEXT,
            recommendations TEXT,
            follow_up_actions TEXT,
            status TEXT NOT NULL DEFAULT 'scheduled',
            presenter_id INTEGER,
            chair_id INTEGER,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS gi_gov_audit (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            objective TEXT NOT NULL,
            methodology TEXT,
            inclusion_criteria TEXT,
            status TEXT NOT NULL DEFAULT 'planned',
            investigator_id INTEGER,
            findings_summary TEXT,
            timeline_start TEXT,
            timeline_end TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS gi_gov_document (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            document_type TEXT NOT NULL DEFAULT 'sop',
            version TEXT NOT NULL DEFAULT '1.0',
            status TEXT NOT NULL DEFAULT 'draft',
            content_summary TEXT,
            approval_date TEXT,
            expiry_date TEXT,
            approved_by_id INTEGER,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS gi_gov_document_ack (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            acknowledged_at TEXT DEFAULT (datetime('now')),
            UNIQUE(document_id, user_id),
            FOREIGN KEY (document_id) REFERENCES gi_gov_document(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS gi_gov_checklist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            checklist_type TEXT NOT NULL,
            reference_type TEXT,
            reference_id INTEGER,
            is_complete INTEGER NOT NULL DEFAULT 0,
            items_json TEXT DEFAULT '[]',
            completed_by_id INTEGER,
            completed_at TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS gi_journey_event (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ward_patient_id INTEGER,
            appointment_id INTEGER,
            mrn TEXT,
            patient_name TEXT,
            event_type TEXT NOT NULL,
            title TEXT NOT NULL,
            details_json TEXT DEFAULT '{}',
            event_at TEXT DEFAULT (datetime('now')),
            created_by INTEGER,
            source_module TEXT,
            source_id INTEGER
        );

        CREATE TABLE IF NOT EXISTS gi_lab_result (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ward_patient_id INTEGER,
            session_id INTEGER,
            order_id INTEGER,
            mrn TEXT,
            test_name TEXT NOT NULL,
            result_value TEXT,
            result_unit TEXT,
            recorded_by INTEGER,
            recorded_at TEXT DEFAULT (datetime('now'))
        );

        CREATE INDEX IF NOT EXISTS idx_gi_journey_mrn ON gi_journey_event(mrn);
        CREATE INDEX IF NOT EXISTS idx_gi_journey_wp ON gi_journey_event(ward_patient_id);
        CREATE INDEX IF NOT EXISTS idx_gi_attendance_user ON gi_attendance_record(user_id, attendance_date);
        CREATE INDEX IF NOT EXISTS idx_gi_roster_period ON gi_duty_roster_period(roster_type, year_month);
    """)

    cur.execute(
        "INSERT OR IGNORE INTO gi_meta (key, value) VALUES ('schema_version', ?)",
        (str(GI_SCHEMA_VERSION),),
    )
    db.commit()

    _apply_gi_alter_migrations(cur, db)
    _seed_knowledge_if_empty(cur, db)


def _apply_gi_alter_migrations(cur: sqlite3.Cursor, db) -> None:
    cols = {r[1] for r in cur.execute("PRAGMA table_info(gi_history_session)").fetchall()}
    if 'complaint_code' not in cols:
        cur.execute("ALTER TABLE gi_history_session ADD COLUMN complaint_code TEXT")
    if 'examination_text' not in cols:
        cur.execute("ALTER TABLE gi_history_session ADD COLUMN examination_text TEXT DEFAULT ''")
    narr_cols = {r[1] for r in cur.execute("PRAGMA table_info(gi_history_narrative)").fetchall()}
    if narr_cols and 'sections_json' not in narr_cols:
        cur.execute("ALTER TABLE gi_history_narrative ADD COLUMN sections_json TEXT")
    var_cols = {r[1] for r in cur.execute("PRAGMA table_info(gi_research_variable)").fetchall()}
    for col, ddl in (
        ('code', 'TEXT'), ('source_type', 'TEXT'), ('sort_order', 'INTEGER DEFAULT 0'),
        ('approval_status', "TEXT DEFAULT 'approved'"),
        ('proposed_by', 'INTEGER'),
        ('review_note', 'TEXT'),
    ):
        if col not in var_cols:
            cur.execute(f"ALTER TABLE gi_research_variable ADD COLUMN {col} {ddl}")
    ko_cols = {r[1] for r in cur.execute("PRAGMA table_info(gi_knowledge_object)").fetchall()}
    for col, ddl in (
        ('stable_id', 'TEXT'), ('version_no', 'INTEGER DEFAULT 1'),
        ('supersedes_id', 'INTEGER'), ('provenance_json', 'TEXT'),
    ):
        if col not in ko_cols:
            cur.execute(f"ALTER TABLE gi_knowledge_object ADD COLUMN {col} {ddl}")
    inv_cols = {r[1] for r in cur.execute("PRAGMA table_info(gi_investigation_order)").fetchall()}
    for col, ddl in (
        ('approval_status', "TEXT DEFAULT 'pending_registrar'"),
        ('approved_by', 'INTEGER'),
        ('approved_at', 'TEXT'),
        ('rejection_note', 'TEXT'),
    ):
        if col not in inv_cols:
            cur.execute(f"ALTER TABLE gi_investigation_order ADD COLUMN {col} {ddl}")
    port_cols = {r[1] for r in cur.execute("PRAGMA table_info(gi_portfolio_entry)").fetchall()}
    for col, ddl in (
        ('mrn', 'TEXT'),
        ('patient_name', 'TEXT'),
        ('source_module', 'TEXT'),
        ('source_type', 'TEXT'),
        ('source_id', 'INTEGER'),
        ('appointment_id', 'INTEGER'),
    ):
        if col not in port_cols:
            cur.execute(f"ALTER TABLE gi_portfolio_entry ADD COLUMN {col} {ddl}")
    sess_cols = {r[1] for r in cur.execute("PRAGMA table_info(gi_history_session)").fetchall()}
    if 'final_diagnosis' not in sess_cols:
        cur.execute("ALTER TABLE gi_history_session ADD COLUMN final_diagnosis TEXT DEFAULT ''")
    if 'encounter_state_json' not in sess_cols:
        cur.execute("ALTER TABLE gi_history_session ADD COLUMN encounter_state_json TEXT DEFAULT '{}'")

    ans_cols = {r[1] for r in cur.execute("PRAGMA table_info(gi_history_answer)").fetchall()}
    if 'symptom_id' not in ans_cols:
        cur.execute("ALTER TABLE gi_history_answer ADD COLUMN symptom_id INTEGER REFERENCES gi_history_session_symptom(id) ON DELETE CASCADE")
    inv_cols = {r[1] for r in cur.execute("PRAGMA table_info(gi_investigation_order)").fetchall()}
    for col, ddl in (
        ('scheduled_date', 'TEXT'),
        ('scheduled_time', 'TEXT'),
        ('appointment_id', 'INTEGER'),
    ):
        if col not in inv_cols:
            cur.execute(f"ALTER TABLE gi_investigation_order ADD COLUMN {col} {ddl}")
    adm_cols = {r[1] for r in cur.execute("PRAGMA table_info(ward_admission)").fetchall()}
    if adm_cols and 'discharge_outcome' not in adm_cols:
        cur.execute("ALTER TABLE ward_admission ADD COLUMN discharge_outcome TEXT")

    mm_cols = {r[1] for r in cur.execute("PRAGMA table_info(gi_gov_mm_case)").fetchall()}
    for col, ddl in (
        ('is_important', 'INTEGER NOT NULL DEFAULT 0'),
        ('training_route', 'TEXT'),
        ('assigned_usernames', 'TEXT'),
        ('presenter_usernames', 'TEXT'),
    ):
        if col not in mm_cols:
            cur.execute(f"ALTER TABLE gi_gov_mm_case ADD COLUMN {col} {ddl}")

    cur.execute("""
        CREATE TABLE IF NOT EXISTS gi_gov_journal_club (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            article_reference TEXT,
            session_date TEXT,
            assigned_usernames TEXT,
            presenter_usernames TEXT,
            training_route TEXT,
            is_important INTEGER NOT NULL DEFAULT 0,
            notes TEXT,
            status TEXT NOT NULL DEFAULT 'scheduled',
            created_by_id INTEGER,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS gi_training_assignment (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            assignment_type TEXT NOT NULL,
            source_module TEXT NOT NULL,
            source_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            details TEXT,
            session_date TEXT,
            training_route TEXT,
            status TEXT NOT NULL DEFAULT 'pending',
            assigned_by_id INTEGER,
            created_at TEXT DEFAULT (datetime('now')),
            completed_at TEXT,
            FOREIGN KEY (user_id) REFERENCES user(id)
        )
    """)

    reg_cols = {r[1] for r in cur.execute("PRAGMA table_info(gi_research_registry)").fetchall()}
    for col, ddl in (
        ('lead_user_id', 'INTEGER'),
        ('team_user_ids', 'TEXT'),
        ('hod_status', "TEXT DEFAULT 'draft'"),
        ('hod_review_note', 'TEXT'),
        ('assigned_by_hod_id', 'INTEGER'),
    ):
        if col not in reg_cols:
            cur.execute(f"ALTER TABLE gi_research_registry ADD COLUMN {col} {ddl}")

    enr_cols = {r[1] for r in cur.execute("PRAGMA table_info(gi_research_enrollment)").fetchall()}
    if 'responsible_user_id' not in enr_cols:
        cur.execute("ALTER TABLE gi_research_enrollment ADD COLUMN responsible_user_id INTEGER")
    if 'status' not in enr_cols:
        cur.execute(
            "ALTER TABLE gi_research_enrollment ADD COLUMN status TEXT NOT NULL DEFAULT 'active'"
        )

    cur.execute("""
        CREATE TABLE IF NOT EXISTS gi_login_promo_image (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            stored_filename TEXT NOT NULL,
            original_filename TEXT,
            label TEXT,
            link_url TEXT,
            is_active INTEGER NOT NULL DEFAULT 1,
            uploaded_by INTEGER,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)

    lab_cols = {r[1] for r in cur.execute("PRAGMA table_info(gi_lab_result)").fetchall()}
    for col, ddl in (
        ('test_code', 'TEXT'),
        ('reference_range', 'TEXT'),
        ('result_date', 'TEXT'),
        ('status', "TEXT DEFAULT 'completed'"),
        ('comments', 'TEXT'),
        ('attachment_path', 'TEXT'),
    ):
        if col not in lab_cols:
            cur.execute(f"ALTER TABLE gi_lab_result ADD COLUMN {col} {ddl}")

    inv_cols2 = {r[1] for r in cur.execute("PRAGMA table_info(gi_investigation_order)").fetchall()}
    if 'category' not in inv_cols2:
        cur.execute("ALTER TABLE gi_investigation_order ADD COLUMN category TEXT")

    score_cols = {r[1] for r in cur.execute("PRAGMA table_info(gi_clinical_score_result)").fetchall()}
    for col, ddl in (
        ('ward_patient_id', 'INTEGER'),
        ('score_code', 'TEXT'),
        ('auto_calculated', 'INTEGER DEFAULT 0'),
        ('updated_at', 'TEXT'),
    ):
        if col not in score_cols:
            cur.execute(f"ALTER TABLE gi_clinical_score_result ADD COLUMN {col} {ddl}")

    cur.execute("""
        CREATE TABLE IF NOT EXISTS gi_history_template (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            disease_code TEXT NOT NULL UNIQUE,
            disease_name TEXT NOT NULL,
            symptoms_json TEXT DEFAULT '[]',
            red_flags_json TEXT DEFAULT '[]',
            risk_factors_json TEXT DEFAULT '[]',
            positive_findings_json TEXT DEFAULT '[]',
            negative_findings_json TEXT DEFAULT '[]',
            exclusions_json TEXT DEFAULT '[]',
            created_by INTEGER,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS gi_history_template_question (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            template_id INTEGER NOT NULL,
            question_key TEXT NOT NULL,
            prompt TEXT NOT NULL,
            answer_type TEXT NOT NULL DEFAULT 'text',
            choices_json TEXT DEFAULT '[]',
            sort_order INTEGER DEFAULT 0,
            is_red_flag INTEGER DEFAULT 0,
            is_exclusion INTEGER DEFAULT 0,
            FOREIGN KEY (template_id) REFERENCES gi_history_template(id) ON DELETE CASCADE
        )
    """)
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_gi_lab_result_patient ON gi_lab_result(ward_patient_id)
    """)
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_gi_score_patient ON gi_clinical_score_result(ward_patient_id)
    """)

    _seed_default_history_templates(cur)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS gi_registry_diagnosis (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            disease_code TEXT NOT NULL UNIQUE,
            disease_name TEXT NOT NULL,
            match_terms_json TEXT DEFAULT '[]',
            icon TEXT DEFAULT '🩺',
            is_active INTEGER NOT NULL DEFAULT 1,
            created_by INTEGER,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)

    cur.executescript("""
        CREATE TABLE IF NOT EXISTS gi_endoscopy_room (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            room_type TEXT NOT NULL DEFAULT 'general',
            sort_order INTEGER DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'available',
            status_notes TEXT DEFAULT '',
            current_appointment_id INTEGER,
            is_active INTEGER NOT NULL DEFAULT 1,
            created_by INTEGER,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS gi_endoscope (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scope_code TEXT NOT NULL UNIQUE,
            serial_number TEXT DEFAULT '',
            model TEXT DEFAULT '',
            manufacturer TEXT DEFAULT '',
            scope_type TEXT NOT NULL DEFAULT 'gastroscope',
            status TEXT NOT NULL DEFAULT 'available',
            location TEXT DEFAULT '',
            assigned_room_id INTEGER,
            last_maintenance_at TEXT,
            next_maintenance_at TEXT,
            is_active INTEGER NOT NULL DEFAULT 1,
            created_by INTEGER,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS gi_scope_reprocessing_cycle (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scope_id INTEGER NOT NULL,
            started_at TEXT NOT NULL,
            completed_at TEXT,
            current_step TEXT,
            status TEXT NOT NULL DEFAULT 'in_progress',
            started_by_id INTEGER,
            FOREIGN KEY (scope_id) REFERENCES gi_endoscope(id)
        );

        CREATE TABLE IF NOT EXISTS gi_scope_reprocessing_step (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cycle_id INTEGER NOT NULL,
            step_code TEXT NOT NULL,
            completed_at TEXT,
            completed_by_id INTEGER,
            notes TEXT DEFAULT '',
            FOREIGN KEY (cycle_id) REFERENCES gi_scope_reprocessing_cycle(id)
        );

        CREATE TABLE IF NOT EXISTS gi_consumable_item (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            category TEXT NOT NULL,
            current_stock INTEGER NOT NULL DEFAULT 0,
            minimum_stock INTEGER NOT NULL DEFAULT 0,
            unit TEXT NOT NULL DEFAULT 'each',
            is_archived INTEGER NOT NULL DEFAULT 0,
            created_by INTEGER,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS gi_consumable_movement (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            consumable_id INTEGER NOT NULL,
            movement_type TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            appointment_id INTEGER,
            notes TEXT DEFAULT '',
            recorded_by_id INTEGER,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (consumable_id) REFERENCES gi_consumable_item(id)
        );

        CREATE TABLE IF NOT EXISTS gi_waiting_list_entry (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_name TEXT NOT NULL,
            mrn TEXT DEFAULT '',
            procedure_type TEXT NOT NULL,
            priority TEXT NOT NULL DEFAULT 'routine',
            consultant_name TEXT DEFAULT '',
            listed_at TEXT NOT NULL,
            scheduled_date TEXT,
            status TEXT NOT NULL DEFAULT 'active',
            appointment_id INTEGER,
            is_archived INTEGER NOT NULL DEFAULT 0,
            created_by INTEGER,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS gi_dept_ops_roster (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            roster_date TEXT NOT NULL,
            shift_type TEXT NOT NULL DEFAULT 'day',
            is_on_call INTEGER NOT NULL DEFAULT 0,
            notes TEXT DEFAULT '',
            created_by INTEGER,
            created_at TEXT DEFAULT (datetime('now')),
            UNIQUE(user_id, roster_date),
            FOREIGN KEY (user_id) REFERENCES user(id)
        );

        CREATE TABLE IF NOT EXISTS gi_dept_announcement (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            body TEXT NOT NULL,
            category TEXT NOT NULL DEFAULT 'notice',
            priority TEXT NOT NULL DEFAULT 'normal',
            expires_at TEXT,
            is_archived INTEGER NOT NULL DEFAULT 0,
            published_by_id INTEGER,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS gi_dept_message (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id INTEGER NOT NULL,
            recipient_id INTEGER,
            message_scope TEXT NOT NULL DEFAULT 'direct',
            subject TEXT NOT NULL,
            body TEXT NOT NULL,
            read_at TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (sender_id) REFERENCES user(id)
        );

        CREATE INDEX IF NOT EXISTS idx_gi_waiting_list_status ON gi_waiting_list_entry(status);
        CREATE INDEX IF NOT EXISTS idx_gi_scope_status ON gi_endoscope(status);
    """)

    ai_sess_cols = {r[1] for r in cur.execute("PRAGMA table_info(gi_ai_session)").fetchall()}
    for col, ddl in (
        ('session_uuid', 'TEXT'),
        ('history_session_id', 'INTEGER'),
        ('prompt_type', 'TEXT'),
        ('provider_key', "TEXT DEFAULT 'stub'"),
        ('model_name', 'TEXT'),
        ('execution_duration_ms', 'INTEGER'),
        ('token_usage_json', 'TEXT'),
        ('response_metadata_json', 'TEXT'),
        ('prompt_text', 'TEXT'),
        ('response_text', 'TEXT'),
    ):
        if col not in ai_sess_cols:
            cur.execute(f"ALTER TABLE gi_ai_session ADD COLUMN {col} {ddl}")

    ai_log_cols = {r[1] for r in cur.execute("PRAGMA table_info(gi_ai_request_log)").fetchall()}
    for col, ddl in (
        ('prompt_type', 'TEXT'),
        ('execution_duration_ms', 'INTEGER'),
        ('parsed_response_json', 'TEXT'),
    ):
        if col not in ai_log_cols:
            cur.execute(f"ALTER TABLE gi_ai_request_log ADD COLUMN {col} {ddl}")

    cur.execute("""
        CREATE TABLE IF NOT EXISTS gi_clinical_ai_audit (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_uuid TEXT NOT NULL,
            user_id INTEGER NOT NULL,
            ward_patient_id INTEGER,
            provider_key TEXT NOT NULL,
            model_name TEXT,
            prompt_type TEXT NOT NULL,
            execution_duration_ms INTEGER,
            token_usage_json TEXT,
            status TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_gi_clinical_ai_audit_uuid
        ON gi_clinical_ai_audit(session_uuid)
    """)
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_gi_ai_session_uuid ON gi_ai_session(session_uuid)
    """)

    cur.executescript("""
        CREATE TABLE IF NOT EXISTS gi_guided_history_question (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question_id TEXT NOT NULL UNIQUE,
            question_text TEXT NOT NULL,
            category TEXT NOT NULL,
            clinical_purpose TEXT,
            question_type TEXT NOT NULL DEFAULT 'boolean',
            answer_options_json TEXT,
            is_required INTEGER NOT NULL DEFAULT 0,
            priority INTEGER NOT NULL DEFAULT 100,
            conditional_rules_json TEXT,
            knowledge_topic_key TEXT,
            knowledge_stable_id TEXT,
            version INTEGER NOT NULL DEFAULT 1,
            status TEXT NOT NULL DEFAULT 'active',
            specialty_code TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS gi_guided_history_question_rule (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            complaint_code TEXT NOT NULL,
            question_id TEXT NOT NULL,
            sort_order INTEGER NOT NULL DEFAULT 100,
            activation_rules_json TEXT,
            specialty_code TEXT,
            UNIQUE(complaint_code, question_id)
        );

        CREATE TABLE IF NOT EXISTS gi_guided_history_session (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            history_session_id INTEGER,
            ward_patient_id INTEGER,
            chief_complaint TEXT,
            normalized_complaint TEXT,
            complaint_code TEXT,
            status TEXT NOT NULL DEFAULT 'questioning',
            ai_session_uuid TEXT,
            presented_question_ids_json TEXT,
            created_by INTEGER,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now')),
            UNIQUE(history_session_id)
        );

        CREATE TABLE IF NOT EXISTS gi_guided_history_answer (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            history_session_id INTEGER,
            ward_patient_id INTEGER,
            question_id TEXT NOT NULL,
            response_value TEXT NOT NULL,
            response_display TEXT,
            answered_at TEXT DEFAULT (datetime('now')),
            answered_by INTEGER,
            UNIQUE(session_id, question_id),
            FOREIGN KEY (session_id) REFERENCES gi_guided_history_session(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS gi_guided_history_draft (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'draft',
            sections_json TEXT NOT NULL,
            source_answer_ids_json TEXT,
            ai_session_uuid TEXT,
            physician_edited_text TEXT,
            missing_information_json TEXT,
            structured_findings_json TEXT,
            learning_notes_json TEXT,
            created_by INTEGER,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (session_id) REFERENCES gi_guided_history_session(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_gh_session_patient ON gi_guided_history_session(ward_patient_id);
        CREATE INDEX IF NOT EXISTS idx_gh_session_history ON gi_guided_history_session(history_session_id);
        CREATE INDEX IF NOT EXISTS idx_gh_rule_complaint ON gi_guided_history_question_rule(complaint_code);
    """)

    cur.executescript("""
        CREATE TABLE IF NOT EXISTS gi_diagnosis_rule (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            complaint_code TEXT NOT NULL,
            diagnosis_name TEXT NOT NULL,
            category TEXT NOT NULL,
            base_priority INTEGER NOT NULL DEFAULT 100,
            base_confidence REAL NOT NULL DEFAULT 0.5,
            inclusion_reason TEXT,
            supporting_patterns_json TEXT,
            missing_patterns_json TEXT,
            contradicting_patterns_json TEXT,
            knowledge_topic_key TEXT,
            knowledge_stable_id TEXT,
            specialty_code TEXT,
            version INTEGER NOT NULL DEFAULT 1,
            status TEXT NOT NULL DEFAULT 'active',
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS gi_clinical_assessment_run (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            history_session_id INTEGER NOT NULL,
            ward_patient_id INTEGER,
            guided_history_session_id INTEGER,
            ai_session_uuid TEXT,
            provider_key TEXT,
            model_name TEXT,
            status TEXT NOT NULL DEFAULT 'generated',
            knowledge_sources_json TEXT,
            clinical_context_json TEXT,
            created_by INTEGER,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS gi_diagnosis_suggestion (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            assessment_run_id INTEGER NOT NULL,
            history_session_id INTEGER NOT NULL,
            ward_patient_id INTEGER,
            diagnosis_name TEXT NOT NULL,
            category TEXT NOT NULL,
            priority_rank INTEGER NOT NULL DEFAULT 100,
            supporting_findings_json TEXT,
            missing_information_json TEXT,
            contradicting_findings_json TEXT,
            inclusion_reason TEXT,
            confidence_indicator TEXT NOT NULL DEFAULT 'medium',
            knowledge_references_json TEXT,
            clinical_findings_used_json TEXT,
            ai_session_uuid TEXT,
            status TEXT NOT NULL DEFAULT 'suggested',
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (assessment_run_id) REFERENCES gi_clinical_assessment_run(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS gi_physician_diagnosis_decision (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            history_session_id INTEGER NOT NULL,
            ward_patient_id INTEGER,
            assessment_run_id INTEGER,
            suggestion_id INTEGER,
            diagnosis_name TEXT NOT NULL,
            original_suggestion_name TEXT,
            physician_status TEXT NOT NULL,
            physician_notes TEXT,
            modified_fields_json TEXT,
            created_by INTEGER,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS gi_clinical_interpretation_run (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            history_session_id INTEGER NOT NULL,
            ward_patient_id INTEGER,
            assessment_run_id INTEGER,
            ai_session_uuid TEXT,
            provider_key TEXT,
            model_name TEXT,
            status TEXT NOT NULL DEFAULT 'generated',
            clinical_data_sources_json TEXT,
            previous_differential_snapshot_json TEXT,
            knowledge_sources_json TEXT,
            clinical_context_json TEXT,
            created_by INTEGER,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS gi_interpretation_finding (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id INTEGER NOT NULL,
            history_session_id INTEGER NOT NULL,
            ward_patient_id INTEGER,
            finding_title TEXT NOT NULL,
            source_type TEXT NOT NULL,
            source_data_json TEXT,
            explanation TEXT,
            significance TEXT,
            differential_impact TEXT,
            related_diagnosis TEXT,
            supporting_diagnoses_json TEXT,
            contradicting_diagnoses_json TEXT,
            missing_information_json TEXT,
            confidence_indicator TEXT NOT NULL DEFAULT 'medium',
            ai_session_uuid TEXT,
            status TEXT NOT NULL DEFAULT 'suggested',
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (run_id) REFERENCES gi_clinical_interpretation_run(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS gi_differential_update_record (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id INTEGER NOT NULL,
            history_session_id INTEGER NOT NULL,
            ward_patient_id INTEGER,
            diagnosis_name TEXT NOT NULL,
            previous_confidence TEXT,
            previous_category TEXT,
            update_direction TEXT NOT NULL,
            reasoning TEXT,
            related_finding_title TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (run_id) REFERENCES gi_clinical_interpretation_run(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS gi_physician_interpretation_decision (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id INTEGER,
            finding_id INTEGER,
            history_session_id INTEGER NOT NULL,
            ward_patient_id INTEGER,
            finding_title TEXT NOT NULL,
            original_finding_title TEXT,
            physician_status TEXT NOT NULL,
            physician_notes TEXT,
            created_by INTEGER,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE INDEX IF NOT EXISTS idx_gi_diagnosis_rule_complaint ON gi_diagnosis_rule(complaint_code);
        CREATE INDEX IF NOT EXISTS idx_gi_assessment_run_history ON gi_clinical_assessment_run(history_session_id);
        CREATE INDEX IF NOT EXISTS idx_gi_diagnosis_suggestion_run ON gi_diagnosis_suggestion(assessment_run_id);
        CREATE INDEX IF NOT EXISTS idx_gi_interpretation_run_history ON gi_clinical_interpretation_run(history_session_id);
        CREATE INDEX IF NOT EXISTS idx_gi_interpretation_finding_run ON gi_interpretation_finding(run_id);

        CREATE TABLE IF NOT EXISTS gi_investigation_library_entry (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            investigation_id TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            catalogue_code TEXT,
            indications_json TEXT,
            contraindications_json TEXT,
            related_diagnosis_concepts_json TEXT,
            knowledge_topic_key TEXT,
            knowledge_stable_id TEXT,
            version INTEGER NOT NULL DEFAULT 1,
            status TEXT NOT NULL DEFAULT 'active',
            specialty_code TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS gi_investigation_recommendation_rule (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            complaint_code TEXT,
            diagnosis_name TEXT,
            investigation_id TEXT NOT NULL,
            workup_group TEXT NOT NULL,
            priority TEXT NOT NULL DEFAULT 'recommended',
            reason_template TEXT,
            related_diagnosis TEXT,
            missing_info_addressed TEXT,
            sort_order INTEGER NOT NULL DEFAULT 100,
            specialty_code TEXT,
            status TEXT NOT NULL DEFAULT 'active',
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS gi_investigation_plan (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            history_session_id INTEGER NOT NULL,
            ward_patient_id INTEGER,
            assessment_run_id INTEGER,
            ai_session_uuid TEXT,
            provider_key TEXT,
            model_name TEXT,
            status TEXT NOT NULL DEFAULT 'draft',
            knowledge_sources_json TEXT,
            clinical_context_json TEXT,
            created_by INTEGER,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS gi_investigation_plan_suggestion (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plan_id INTEGER NOT NULL,
            history_session_id INTEGER NOT NULL,
            ward_patient_id INTEGER,
            investigation_id TEXT NOT NULL,
            investigation_name TEXT NOT NULL,
            category TEXT NOT NULL,
            priority TEXT NOT NULL,
            workup_group TEXT NOT NULL,
            reason TEXT,
            related_diagnosis TEXT,
            clinical_purpose TEXT,
            missing_info_addressed TEXT,
            knowledge_references_json TEXT,
            confidence_indicator TEXT NOT NULL DEFAULT 'medium',
            ai_session_uuid TEXT,
            duplicate_skipped INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'suggested',
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (plan_id) REFERENCES gi_investigation_plan(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS gi_physician_investigation_decision (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plan_id INTEGER,
            suggestion_id INTEGER,
            history_session_id INTEGER NOT NULL,
            ward_patient_id INTEGER,
            investigation_name TEXT NOT NULL,
            category TEXT,
            priority TEXT,
            physician_status TEXT NOT NULL,
            physician_reason TEXT,
            modified_fields_json TEXT,
            created_by INTEGER,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE INDEX IF NOT EXISTS idx_gi_inv_plan_history ON gi_investigation_plan(history_session_id);
        CREATE INDEX IF NOT EXISTS idx_gi_inv_plan_suggestion_plan ON gi_investigation_plan_suggestion(plan_id);
        CREATE INDEX IF NOT EXISTS idx_gi_inv_rule_complaint ON gi_investigation_recommendation_rule(complaint_code);

        CREATE TABLE IF NOT EXISTS gi_management_plan_rule (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            diagnosis_name TEXT NOT NULL,
            complaint_code TEXT,
            category TEXT NOT NULL,
            description_template TEXT NOT NULL,
            clinical_indication TEXT,
            priority TEXT NOT NULL DEFAULT 'recommended',
            knowledge_topic_key TEXT,
            knowledge_stable_id TEXT,
            guideline_reference TEXT,
            sort_order INTEGER NOT NULL DEFAULT 100,
            specialty_code TEXT,
            status TEXT NOT NULL DEFAULT 'active',
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS gi_ai_management_plan (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            history_session_id INTEGER NOT NULL,
            ward_patient_id INTEGER,
            assessment_run_id INTEGER,
            interpretation_run_id INTEGER,
            investigation_plan_id INTEGER,
            ai_session_uuid TEXT,
            provider_key TEXT,
            model_name TEXT,
            status TEXT NOT NULL DEFAULT 'draft',
            working_diagnoses_json TEXT,
            knowledge_sources_json TEXT,
            clinical_context_json TEXT,
            created_by INTEGER,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS gi_management_ai_suggestion (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plan_id INTEGER NOT NULL,
            history_session_id INTEGER NOT NULL,
            ward_patient_id INTEGER,
            suggestion_key TEXT NOT NULL,
            category TEXT NOT NULL,
            description TEXT NOT NULL,
            clinical_indication TEXT,
            related_diagnosis TEXT,
            supporting_evidence_json TEXT,
            knowledge_references_json TEXT,
            guideline_references_json TEXT,
            priority TEXT NOT NULL DEFAULT 'recommended',
            confidence_indicator TEXT NOT NULL DEFAULT 'medium',
            ai_session_uuid TEXT,
            status TEXT NOT NULL DEFAULT 'suggested',
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (plan_id) REFERENCES gi_ai_management_plan(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS gi_physician_management_decision (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plan_id INTEGER,
            suggestion_id INTEGER,
            history_session_id INTEGER NOT NULL,
            ward_patient_id INTEGER,
            category TEXT,
            description TEXT NOT NULL,
            original_description TEXT,
            physician_status TEXT NOT NULL,
            physician_notes TEXT,
            modified_fields_json TEXT,
            created_by INTEGER,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE INDEX IF NOT EXISTS idx_gi_mgmt_plan_history ON gi_ai_management_plan(history_session_id);
        CREATE INDEX IF NOT EXISTS idx_gi_mgmt_suggestion_plan ON gi_management_ai_suggestion(plan_id);
        CREATE INDEX IF NOT EXISTS idx_gi_mgmt_rule_diagnosis ON gi_management_plan_rule(diagnosis_name);

        CREATE TABLE IF NOT EXISTS gi_documentation_template (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            template_key TEXT NOT NULL UNIQUE,
            document_type TEXT NOT NULL,
            name TEXT NOT NULL,
            specialty_code TEXT,
            sections_json TEXT NOT NULL,
            required_fields_json TEXT,
            optional_fields_json TEXT,
            version INTEGER NOT NULL DEFAULT 1,
            status TEXT NOT NULL DEFAULT 'active',
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS gi_clinical_document_draft (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            history_session_id INTEGER NOT NULL,
            ward_patient_id INTEGER,
            template_id INTEGER,
            template_key TEXT NOT NULL,
            document_type TEXT NOT NULL,
            ai_session_uuid TEXT,
            provider_key TEXT,
            model_name TEXT,
            status TEXT NOT NULL DEFAULT 'draft',
            source_modules_json TEXT,
            knowledge_references_json TEXT,
            clinical_context_json TEXT,
            version INTEGER NOT NULL DEFAULT 1,
            created_by INTEGER,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS gi_document_section (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER NOT NULL,
            section_key TEXT NOT NULL,
            section_name TEXT NOT NULL,
            sort_order INTEGER NOT NULL DEFAULT 0,
            generated_content TEXT,
            physician_content TEXT,
            source_data_references_json TEXT,
            missing_information_json TEXT,
            conflicting_information_json TEXT,
            is_required INTEGER NOT NULL DEFAULT 1,
            is_complete INTEGER NOT NULL DEFAULT 0,
            approval_status TEXT NOT NULL DEFAULT 'draft',
            version INTEGER NOT NULL DEFAULT 1,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (document_id) REFERENCES gi_clinical_document_draft(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS gi_document_version_record (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER NOT NULL,
            version_number INTEGER NOT NULL,
            changed_sections_json TEXT,
            editor_id INTEGER,
            change_reason TEXT,
            snapshot_json TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (document_id) REFERENCES gi_clinical_document_draft(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS gi_physician_document_action (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER NOT NULL,
            section_id INTEGER,
            history_session_id INTEGER NOT NULL,
            ward_patient_id INTEGER,
            action_type TEXT NOT NULL,
            action_notes TEXT,
            modified_fields_json TEXT,
            created_by INTEGER,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS gi_signed_clinical_document (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            draft_id INTEGER NOT NULL UNIQUE,
            history_session_id INTEGER NOT NULL,
            ward_patient_id INTEGER,
            template_key TEXT NOT NULL,
            document_type TEXT NOT NULL,
            signed_content_json TEXT NOT NULL,
            signed_by INTEGER,
            signed_at TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE INDEX IF NOT EXISTS idx_gi_doc_draft_history ON gi_clinical_document_draft(history_session_id);
        CREATE INDEX IF NOT EXISTS idx_gi_doc_section_document ON gi_document_section(document_id);

        CREATE TABLE IF NOT EXISTS gi_follow_up_recommendation_rule (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            diagnosis_name TEXT,
            related_condition TEXT,
            interval_days INTEGER,
            interval_text TEXT,
            reason_template TEXT,
            knowledge_topic_key TEXT,
            sort_order INTEGER NOT NULL DEFAULT 100,
            specialty_code TEXT,
            status TEXT NOT NULL DEFAULT 'active',
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS gi_follow_up_plan (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            history_session_id INTEGER NOT NULL,
            ward_patient_id INTEGER,
            management_plan_id INTEGER,
            related_condition TEXT,
            responsible_user_id INTEGER,
            recommended_interval_days INTEGER,
            recommended_interval_text TEXT,
            reason TEXT,
            status TEXT NOT NULL DEFAULT 'planned',
            knowledge_references_json TEXT,
            created_by INTEGER,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS gi_journey_summary_draft (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            history_session_id INTEGER NOT NULL,
            ward_patient_id INTEGER,
            follow_up_plan_id INTEGER,
            ai_session_uuid TEXT,
            provider_key TEXT,
            model_name TEXT,
            draft_text TEXT,
            approved_text TEXT,
            status TEXT NOT NULL DEFAULT 'draft',
            knowledge_references_json TEXT,
            missing_information_json TEXT,
            created_by INTEGER,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE INDEX IF NOT EXISTS idx_gi_follow_up_plan_patient ON gi_follow_up_plan(ward_patient_id);
        CREATE INDEX IF NOT EXISTS idx_gi_journey_summary_history ON gi_journey_summary_draft(history_session_id);

        CREATE TABLE IF NOT EXISTS gi_history_session_symptom (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            complaint_code TEXT NOT NULL,
            symptom_name TEXT NOT NULL,
            onset_text TEXT DEFAULT '',
            duration_category TEXT DEFAULT '',
            is_primary INTEGER NOT NULL DEFAULT 0,
            sort_order INTEGER NOT NULL DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (session_id) REFERENCES gi_history_session(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_gi_session_symptom_session ON gi_history_session_symptom(session_id);

        CREATE TABLE IF NOT EXISTS gi_patient_document (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ward_patient_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            category TEXT NOT NULL DEFAULT 'general',
            stored_filename TEXT NOT NULL,
            original_filename TEXT,
            content_type TEXT,
            file_size INTEGER,
            notes TEXT,
            uploaded_by INTEGER,
            is_archived INTEGER NOT NULL DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_gi_patient_doc_wp ON gi_patient_document(ward_patient_id);

        CREATE TABLE IF NOT EXISTS gi_consult_request (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ward_patient_id INTEGER NOT NULL,
            specialty TEXT NOT NULL,
            clinical_question TEXT NOT NULL,
            urgency TEXT NOT NULL DEFAULT 'routine',
            status TEXT NOT NULL DEFAULT 'pending',
            requesting_user_id INTEGER,
            assigned_user_id INTEGER,
            response_notes TEXT,
            responded_at TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_gi_consult_status ON gi_consult_request(status);

        CREATE TABLE IF NOT EXISTS gi_branding_settings (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            site_name TEXT,
            slogan TEXT,
            dept_subtitle TEXT,
            primary_color TEXT DEFAULT '#A6192E',
            secondary_color TEXT DEFAULT '#1a1a2e',
            hospital_logo_filename TEXT,
            logo_filename TEXT,
            favicon_filename TEXT,
            show_hospital_logo INTEGER NOT NULL DEFAULT 1,
            show_department_logo INTEGER NOT NULL DEFAULT 1,
            updated_at TEXT,
            updated_by INTEGER
        );

        CREATE TABLE IF NOT EXISTS gi_pharma_banner (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            label TEXT NOT NULL,
            message TEXT NOT NULL,
            link_url TEXT,
            is_active INTEGER NOT NULL DEFAULT 1,
            sort_order INTEGER NOT NULL DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS gi_calendar_event (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            event_date TEXT NOT NULL,
            event_type TEXT NOT NULL DEFAULT 'general',
            description TEXT,
            link_url TEXT,
            created_by INTEGER,
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_gi_calendar_event_date ON gi_calendar_event(event_date);

        CREATE TABLE IF NOT EXISTS gi_education_activity (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            activity_type TEXT NOT NULL,
            activity_date TEXT NOT NULL,
            description TEXT,
            duration_minutes INTEGER,
            location TEXT,
            created_by INTEGER,
            is_archived INTEGER NOT NULL DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_gi_education_user ON gi_education_activity(user_id, activity_date);

        CREATE TABLE IF NOT EXISTS gi_archive_record (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            record_type TEXT NOT NULL,
            source_module TEXT NOT NULL,
            source_id INTEGER,
            title TEXT NOT NULL,
            summary TEXT,
            stored_path TEXT,
            archived_by INTEGER,
            archived_at TEXT DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_gi_archive_type ON gi_archive_record(record_type);
    """)

    brand_cols = {r[1] for r in cur.execute("PRAGMA table_info(gi_branding_settings)").fetchall()}
    if brand_cols:
        for col, ddl in (
            ('hospital_logo_filename', 'TEXT'),
            ('show_hospital_logo', 'INTEGER NOT NULL DEFAULT 1'),
            ('show_department_logo', 'INTEGER NOT NULL DEFAULT 1'),
        ):
            if col not in brand_cols:
                cur.execute(f"ALTER TABLE gi_branding_settings ADD COLUMN {col} {ddl}")

    db.commit()


def _seed_default_history_templates(cur) -> None:
    row = cur.execute('SELECT COUNT(*) AS c FROM gi_history_template').fetchone()
    if row[0] > 0:
        return
    cur.execute(
        """
        INSERT INTO gi_history_template
        (disease_code, disease_name, symptoms_json, red_flags_json, risk_factors_json)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            'upper_gi_bleed',
            'Upper GI Bleeding',
            '["Melena","Hematemesis","Coffee-ground vomitus","Dizziness","Syncope"]',
            '["Haemodynamic instability","Active haematemesis","Altered consciousness"]',
            '["NSAID use","Anticoagulation","Alcohol","Prior ulcer disease","Liver disease"]',
        ),
    )
    tid = cur.lastrowid
    questions = [
        ('melena', 'History of melena?', 'boolean', 1),
        ('hematemesis', 'History of hematemesis?', 'boolean', 2),
        ('nsaid_use', 'Recent NSAID use?', 'boolean', 3),
        ('alcohol', 'Significant alcohol use?', 'boolean', 4),
        ('prior_ulcer', 'Previous peptic ulcer disease?', 'boolean', 5),
        ('liver_disease', 'Known liver disease / cirrhosis?', 'boolean', 6),
        ('syncope', 'Syncope or presyncope?', 'boolean', 7),
        ('weight_loss', 'Unintentional weight loss?', 'boolean', 8),
    ]
    for key, prompt, atype, order in questions:
        cur.execute(
            """
            INSERT INTO gi_history_template_question
            (template_id, question_key, prompt, answer_type, sort_order, is_red_flag)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (tid, key, prompt, atype, order, 1 if key in ('syncope', 'hematemesis') else 0),
        )


def init_gi_schema(get_db) -> None:
    """Create GI tables using Flask request DB connection."""
    init_gi_schema_db(get_db())


def _seed_knowledge_if_empty(cur: sqlite3.Cursor, db) -> None:
    cur.execute("SELECT COUNT(*) AS c FROM gi_knowledge_object")
    if cur.fetchone()['c'] > 0:
        return

    seeds = [
        ('upper-gi-bleed', 'Upper GI Bleed', 'condition', 'published',
         'Acute upper gastrointestinal bleeding workup and management.'),
        ('variceal-bleed', 'Variceal Bleed', 'condition', 'published',
         'Bleeding from esophageal or gastric varices.'),
        ('melena', 'Melena', 'symptom', 'published', 'Black tarry stools suggesting upper GI blood loss.'),
        ('rockall-score', 'Rockall Score', 'score', 'published', 'Risk stratification after upper GI bleed.'),
        ('egd-guideline', 'EGD for UGIB', 'guideline', 'published',
         'Early endoscopy within 24h for hemodynamically stable UGIB.'),
    ]
    for slug, title, obj_type, status, summary in seeds:
        cur.execute(
            """
            INSERT INTO gi_knowledge_object (slug, title, object_type, status, summary)
            VALUES (?, ?, ?, ?, ?)
            """,
            (slug, title, obj_type, status, summary),
        )

    cur.execute("SELECT id, slug FROM gi_knowledge_object")
    ids = {row['slug']: row['id'] for row in cur.fetchall()}
    links = [
        (ids['upper-gi-bleed'], ids['melena'], 'presents_with'),
        (ids['upper-gi-bleed'], ids['variceal-bleed'], 'differential'),
        (ids['upper-gi-bleed'], ids['rockall-score'], 'scored_by'),
        (ids['upper-gi-bleed'], ids['egd-guideline'], 'managed_by'),
    ]
    for src, tgt, link_type in links:
        cur.execute(
            """
            INSERT INTO gi_knowledge_link (source_id, target_id, link_type)
            VALUES (?, ?, ?)
            """,
            (src, tgt, link_type),
        )
    db.commit()
