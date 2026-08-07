"""SQLite schema for advanced endoscopy reports (EUS, Capsule, …)."""

from __future__ import annotations

_REPORT_DDL = """
CREATE TABLE IF NOT EXISTS {table} (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    appointment_id INTEGER NOT NULL UNIQUE REFERENCES appointment(id),
    status TEXT NOT NULL DEFAULT 'draft',
    created_by TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT '',
    updated_at TEXT NOT NULL DEFAULT '',
    finalized_by TEXT NOT NULL DEFAULT '',
    finalized_at TEXT NOT NULL DEFAULT '',
    unlocked_by TEXT NOT NULL DEFAULT '',
    unlocked_at TEXT NOT NULL DEFAULT '',
    endoscopist_id INTEGER REFERENCES endoscopist(id),
    anesthesiologist TEXT NOT NULL DEFAULT '',
    technician TEXT NOT NULL DEFAULT '',
    assistants TEXT NOT NULL DEFAULT '',
    sedation TEXT NOT NULL DEFAULT '',
    payload_json TEXT NOT NULL DEFAULT '{{}}',
    procedure_note TEXT NOT NULL DEFAULT '',
    impression TEXT NOT NULL DEFAULT '',
    clinical_plan TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS {image_table} (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    report_id INTEGER NOT NULL REFERENCES {table}(id) ON DELETE CASCADE,
    slot INTEGER NOT NULL,
    filename TEXT NOT NULL,
    uploaded_by TEXT NOT NULL DEFAULT '',
    uploaded_at TEXT NOT NULL DEFAULT '',
    UNIQUE(report_id, slot)
);
"""


def _ensure_report_tables(dbconn, cfg: dict) -> None:
    table = cfg['table']
    image_table = cfg['image_table']
    if table in ('eus_report', 'capsule_report'):
        return
    existing = {row['name'] for row in dbconn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()}
    if table not in existing:
        dbconn.executescript(_REPORT_DDL.format(table=table, image_table=image_table))
    if cfg.get('has_anesthesiologist'):
        cols = {row['name'] for row in dbconn.execute(f'PRAGMA table_info({table})').fetchall()}
        if 'anesthesiologist' not in cols:
            dbconn.execute(
                f"ALTER TABLE {table} ADD COLUMN anesthesiologist TEXT NOT NULL DEFAULT ''"
            )
    elif table not in ('capsule_report',):
        cols = {row['name'] for row in dbconn.execute(f'PRAGMA table_info({table})').fetchall()}
        if 'anesthesiologist' in cols:
            pass
        elif 'sedation' not in cols:
            dbconn.execute(f"ALTER TABLE {table} ADD COLUMN sedation TEXT NOT NULL DEFAULT ''")


def init_advanced_report_schema(dbconn) -> None:
    dbconn.executescript(
        """
        CREATE TABLE IF NOT EXISTS eus_report (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            appointment_id INTEGER NOT NULL UNIQUE REFERENCES appointment(id),
            status TEXT NOT NULL DEFAULT 'draft',
            created_by TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL DEFAULT '',
            updated_at TEXT NOT NULL DEFAULT '',
            finalized_by TEXT NOT NULL DEFAULT '',
            finalized_at TEXT NOT NULL DEFAULT '',
            unlocked_by TEXT NOT NULL DEFAULT '',
            unlocked_at TEXT NOT NULL DEFAULT '',
            endoscopist_id INTEGER REFERENCES endoscopist(id),
            anesthesiologist TEXT NOT NULL DEFAULT '',
            technician TEXT NOT NULL DEFAULT '',
            assistants TEXT NOT NULL DEFAULT '',
            sedation TEXT NOT NULL DEFAULT '',
            payload_json TEXT NOT NULL DEFAULT '{}',
            procedure_note TEXT NOT NULL DEFAULT '',
            impression TEXT NOT NULL DEFAULT '',
            clinical_plan TEXT NOT NULL DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS eus_report_image (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_id INTEGER NOT NULL REFERENCES eus_report(id) ON DELETE CASCADE,
            slot INTEGER NOT NULL,
            filename TEXT NOT NULL,
            uploaded_by TEXT NOT NULL DEFAULT '',
            uploaded_at TEXT NOT NULL DEFAULT '',
            UNIQUE(report_id, slot)
        );

        CREATE TABLE IF NOT EXISTS capsule_report (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            appointment_id INTEGER NOT NULL UNIQUE REFERENCES appointment(id),
            status TEXT NOT NULL DEFAULT 'draft',
            created_by TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL DEFAULT '',
            updated_at TEXT NOT NULL DEFAULT '',
            finalized_by TEXT NOT NULL DEFAULT '',
            finalized_at TEXT NOT NULL DEFAULT '',
            unlocked_by TEXT NOT NULL DEFAULT '',
            unlocked_at TEXT NOT NULL DEFAULT '',
            endoscopist_id INTEGER REFERENCES endoscopist(id),
            technician TEXT NOT NULL DEFAULT '',
            assistants TEXT NOT NULL DEFAULT '',
            payload_json TEXT NOT NULL DEFAULT '{}',
            procedure_note TEXT NOT NULL DEFAULT '',
            impression TEXT NOT NULL DEFAULT '',
            clinical_plan TEXT NOT NULL DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS capsule_report_image (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_id INTEGER NOT NULL REFERENCES capsule_report(id) ON DELETE CASCADE,
            slot INTEGER NOT NULL,
            filename TEXT NOT NULL,
            uploaded_by TEXT NOT NULL DEFAULT '',
            uploaded_at TEXT NOT NULL DEFAULT '',
            UNIQUE(report_id, slot)
        );
        """
    )
    existing_eus_cols = {row['name'] for row in dbconn.execute('PRAGMA table_info(eus_report)').fetchall()}
    if 'anesthesiologist' not in existing_eus_cols:
        dbconn.execute("ALTER TABLE eus_report ADD COLUMN anesthesiologist TEXT NOT NULL DEFAULT ''")

    from advanced_reports.configs import PROCEDURE_REGISTRY
    for cfg in PROCEDURE_REGISTRY.values():
        _ensure_report_tables(dbconn, cfg)
    dbconn.commit()
