"""Additive SQLite schema for Clinical Knowledge Platform (ckp_ prefix)."""

from __future__ import annotations

import sqlite3

CKP_SCHEMA_VERSION = 1


def init_ckp_schema(db: sqlite3.Connection) -> None:
    cur = db.cursor()
    cur.executescript(
        """
        CREATE TABLE IF NOT EXISTS ckp_domain (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL UNIQUE,
            label TEXT NOT NULL,
            scope_note TEXT,
            status TEXT NOT NULL DEFAULT 'active',
            revision INTEGER NOT NULL DEFAULT 1,
            body_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS ckp_knowledge_release (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL UNIQUE,
            label TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'draft',
            notes TEXT,
            published_at TEXT,
            created_by INTEGER,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS ckp_entity (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL UNIQUE,
            entity_type TEXT NOT NULL,
            label TEXT NOT NULL,
            domain_id INTEGER REFERENCES ckp_domain(id),
            lifecycle TEXT NOT NULL DEFAULT 'draft',
            revision INTEGER NOT NULL DEFAULT 1,
            synonyms_json TEXT NOT NULL DEFAULT '[]',
            body_json TEXT NOT NULL DEFAULT '{}',
            superseded_by_code TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );

        CREATE INDEX IF NOT EXISTS idx_ckp_entity_type
        ON ckp_entity(entity_type, lifecycle);
        CREATE INDEX IF NOT EXISTS idx_ckp_entity_domain
        ON ckp_entity(domain_id);

        CREATE TABLE IF NOT EXISTS ckp_entity_version (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entity_id INTEGER NOT NULL REFERENCES ckp_entity(id) ON DELETE CASCADE,
            revision INTEGER NOT NULL,
            snapshot_json TEXT NOT NULL,
            changed_by INTEGER,
            change_note TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            UNIQUE(entity_id, revision)
        );

        CREATE TABLE IF NOT EXISTS ckp_relationship (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rel_type TEXT NOT NULL,
            source_code TEXT NOT NULL,
            target_code TEXT NOT NULL,
            strength TEXT,
            context_json TEXT NOT NULL DEFAULT '{}',
            effect_json TEXT NOT NULL DEFAULT '{}',
            lifecycle TEXT NOT NULL DEFAULT 'draft',
            revision INTEGER NOT NULL DEFAULT 1,
            guideline_assertion_code TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now')),
            UNIQUE(rel_type, source_code, target_code)
        );

        CREATE INDEX IF NOT EXISTS idx_ckp_rel_source
        ON ckp_relationship(source_code, lifecycle);
        CREATE INDEX IF NOT EXISTS idx_ckp_rel_target
        ON ckp_relationship(target_code, lifecycle);
        CREATE INDEX IF NOT EXISTS idx_ckp_rel_type
        ON ckp_relationship(rel_type, lifecycle);

        CREATE TABLE IF NOT EXISTS ckp_relationship_version (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            relationship_id INTEGER NOT NULL REFERENCES ckp_relationship(id) ON DELETE CASCADE,
            revision INTEGER NOT NULL,
            snapshot_json TEXT NOT NULL,
            changed_by INTEGER,
            change_note TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            UNIQUE(relationship_id, revision)
        );

        CREATE TABLE IF NOT EXISTS ckp_guideline_work (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL UNIQUE,
            society TEXT NOT NULL,
            title TEXT NOT NULL,
            year INTEGER,
            edition TEXT,
            status TEXT NOT NULL DEFAULT 'active',
            scope_note TEXT,
            body_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS ckp_guideline_assertion (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL UNIQUE,
            work_code TEXT NOT NULL,
            statement TEXT NOT NULL,
            strength TEXT,
            direction TEXT,
            evidence_grade TEXT,
            applies_to_json TEXT NOT NULL DEFAULT '[]',
            lifecycle TEXT NOT NULL DEFAULT 'draft',
            revision INTEGER NOT NULL DEFAULT 1,
            supersedes_code TEXT,
            body_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS ckp_release_member (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            release_id INTEGER NOT NULL REFERENCES ckp_knowledge_release(id) ON DELETE CASCADE,
            member_kind TEXT NOT NULL,
            member_code TEXT NOT NULL,
            member_revision INTEGER NOT NULL,
            UNIQUE(release_id, member_kind, member_code)
        );

        CREATE TABLE IF NOT EXISTS ckp_audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action TEXT NOT NULL,
            object_kind TEXT NOT NULL,
            object_code TEXT,
            detail_json TEXT NOT NULL DEFAULT '{}',
            actor_id INTEGER,
            created_at TEXT DEFAULT (datetime('now'))
        );

        -- Phase 2: reasoning sessions pin a knowledge release
        CREATE TABLE IF NOT EXISTS cre_session (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            release_id INTEGER NOT NULL REFERENCES ckp_knowledge_release(id),
            patient_label TEXT,
            status TEXT NOT NULL DEFAULT 'active',
            ebs_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );

        CREATE INDEX IF NOT EXISTS idx_cre_session_release
        ON cre_session(release_id, status);

        -- Phase 4: clinical documentation (EBS-consuming drafts)
        CREATE TABLE IF NOT EXISTS ckp_document (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER REFERENCES cre_session(id),
            patient_key TEXT,
            doc_type TEXT NOT NULL,
            title TEXT,
            status TEXT NOT NULL DEFAULT 'draft',
            body_text TEXT NOT NULL DEFAULT '',
            structured_json TEXT NOT NULL DEFAULT '{}',
            ebs_fingerprint TEXT,
            version INTEGER NOT NULL DEFAULT 1,
            authored_by INTEGER,
            finalized_by INTEGER,
            finalized_at TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_ckp_document_session
        ON ckp_document(session_id, doc_type);
        CREATE INDEX IF NOT EXISTS idx_ckp_document_patient
        ON ckp_document(patient_key, doc_type);

        CREATE TABLE IF NOT EXISTS ckp_document_version (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER NOT NULL REFERENCES ckp_document(id) ON DELETE CASCADE,
            version INTEGER NOT NULL,
            body_text TEXT NOT NULL,
            structured_json TEXT NOT NULL DEFAULT '{}',
            change_note TEXT,
            changed_by INTEGER,
            created_at TEXT DEFAULT (datetime('now')),
            UNIQUE(document_id, version)
        );

        CREATE TABLE IF NOT EXISTS ckp_document_audit (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER NOT NULL,
            action TEXT NOT NULL,
            detail_json TEXT NOT NULL DEFAULT '{}',
            actor_id INTEGER,
            created_at TEXT DEFAULT (datetime('now'))
        );

        -- Phase 5: CDS advisory alerts (persisted snapshots)
        CREATE TABLE IF NOT EXISTS ckp_cds_alert (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER REFERENCES cre_session(id),
            alert_kind TEXT NOT NULL,
            severity TEXT NOT NULL DEFAULT 'info',
            title TEXT NOT NULL,
            explanation TEXT,
            supporting_json TEXT NOT NULL DEFAULT '[]',
            contradictory_json TEXT NOT NULL DEFAULT '[]',
            guideline_source TEXT,
            confidence TEXT,
            status TEXT NOT NULL DEFAULT 'active',
            body_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_ckp_cds_session
        ON ckp_cds_alert(session_id, status);

        -- Phase 6: longitudinal clinical memory
        CREATE TABLE IF NOT EXISTS ckp_longitudinal_memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_key TEXT NOT NULL UNIQUE,
            summary_json TEXT NOT NULL DEFAULT '{}',
            timelines_json TEXT NOT NULL DEFAULT '{}',
            registries_json TEXT NOT NULL DEFAULT '[]',
            risk_json TEXT NOT NULL DEFAULT '{}',
            baseline_json TEXT NOT NULL DEFAULT '{}',
            updated_at TEXT DEFAULT (datetime('now')),
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS ckp_longitudinal_event (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_key TEXT NOT NULL,
            session_id INTEGER,
            event_kind TEXT NOT NULL,
            event_code TEXT,
            label TEXT,
            polarity TEXT,
            value TEXT,
            occurred_at TEXT,
            body_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_ckp_long_event_patient
        ON ckp_longitudinal_event(patient_key, event_kind);

        CREATE TABLE IF NOT EXISTS ckp_encounter_compare (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_key TEXT NOT NULL,
            current_session_id INTEGER NOT NULL,
            prior_session_id INTEGER,
            delta_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT DEFAULT (datetime('now'))
        );

        -- Phase 7: research & learning platform
        CREATE TABLE IF NOT EXISTS ckp_research_registry (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL UNIQUE,
            label TEXT NOT NULL,
            description TEXT,
            version INTEGER NOT NULL DEFAULT 1,
            status TEXT NOT NULL DEFAULT 'active',
            variables_json TEXT NOT NULL DEFAULT '[]',
            inclusion_json TEXT NOT NULL DEFAULT '{}',
            exclusion_json TEXT NOT NULL DEFAULT '{}',
            created_by INTEGER,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS ckp_research_cohort (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            registry_id INTEGER NOT NULL REFERENCES ckp_research_registry(id) ON DELETE CASCADE,
            code TEXT NOT NULL,
            label TEXT NOT NULL,
            criteria_json TEXT NOT NULL DEFAULT '{}',
            member_count INTEGER NOT NULL DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now')),
            UNIQUE(registry_id, code)
        );

        CREATE TABLE IF NOT EXISTS ckp_research_member (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cohort_id INTEGER NOT NULL REFERENCES ckp_research_cohort(id) ON DELETE CASCADE,
            patient_key TEXT NOT NULL,
            extracted_json TEXT NOT NULL DEFAULT '{}',
            outcome_json TEXT NOT NULL DEFAULT '{}',
            deid_token TEXT,
            enrolled_at TEXT DEFAULT (datetime('now')),
            UNIQUE(cohort_id, patient_key)
        );

        CREATE TABLE IF NOT EXISTS ckp_research_study (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL UNIQUE,
            title TEXT NOT NULL,
            registry_id INTEGER REFERENCES ckp_research_registry(id),
            design_json TEXT NOT NULL DEFAULT '{}',
            status TEXT NOT NULL DEFAULT 'draft',
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS ckp_research_export (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            study_id INTEGER,
            registry_id INTEGER,
            export_kind TEXT NOT NULL,
            path_or_payload TEXT,
            deidentified INTEGER NOT NULL DEFAULT 1,
            audit_json TEXT NOT NULL DEFAULT '{}',
            created_by INTEGER,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS ckp_research_audit (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action TEXT NOT NULL,
            object_kind TEXT,
            object_id INTEGER,
            detail_json TEXT NOT NULL DEFAULT '{}',
            actor_id INTEGER,
            created_at TEXT DEFAULT (datetime('now'))
        );

        -- Phase 8: enterprise foundations
        CREATE TABLE IF NOT EXISTS ckp_tenant (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL UNIQUE,
            label TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'active',
            config_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS ckp_department (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id INTEGER NOT NULL REFERENCES ckp_tenant(id) ON DELETE CASCADE,
            code TEXT NOT NULL,
            label TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'active',
            UNIQUE(tenant_id, code)
        );

        CREATE TABLE IF NOT EXISTS ckp_rbac_permission (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL UNIQUE,
            label TEXT NOT NULL,
            scope TEXT NOT NULL DEFAULT 'tenant'
        );

        CREATE TABLE IF NOT EXISTS ckp_rbac_role_perm (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            role_code TEXT NOT NULL,
            permission_code TEXT NOT NULL,
            UNIQUE(role_code, permission_code)
        );

        CREATE TABLE IF NOT EXISTS ckp_integration_endpoint (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id INTEGER REFERENCES ckp_tenant(id),
            system_kind TEXT NOT NULL,
            code TEXT NOT NULL,
            label TEXT NOT NULL,
            adapter TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'stub',
            config_json TEXT NOT NULL DEFAULT '{}',
            health_json TEXT NOT NULL DEFAULT '{}',
            last_checked_at TEXT,
            UNIQUE(tenant_id, code)
        );

        CREATE TABLE IF NOT EXISTS ckp_notification (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id INTEGER,
            channel TEXT NOT NULL DEFAULT 'in_app',
            recipient TEXT,
            title TEXT NOT NULL,
            body TEXT,
            status TEXT NOT NULL DEFAULT 'queued',
            body_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT DEFAULT (datetime('now')),
            sent_at TEXT
        );

        CREATE TABLE IF NOT EXISTS ckp_job_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_type TEXT NOT NULL,
            payload_json TEXT NOT NULL DEFAULT '{}',
            status TEXT NOT NULL DEFAULT 'queued',
            attempts INTEGER NOT NULL DEFAULT 0,
            last_error TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS ckp_search_index (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            object_kind TEXT NOT NULL,
            object_id TEXT NOT NULL,
            tenant_id INTEGER,
            title TEXT,
            body TEXT,
            tokens TEXT,
            updated_at TEXT DEFAULT (datetime('now')),
            UNIQUE(object_kind, object_id)
        );

        CREATE TABLE IF NOT EXISTS ckp_enterprise_audit (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id INTEGER,
            actor_id INTEGER,
            action TEXT NOT NULL,
            object_kind TEXT,
            object_id TEXT,
            detail_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS ckp_i18n_string (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT NOT NULL,
            locale TEXT NOT NULL,
            value TEXT NOT NULL,
            UNIQUE(key, locale)
        );
        """
    )
    db.commit()
