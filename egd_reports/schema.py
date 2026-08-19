"""SQLite schema for EGD follow-up and research tables."""

from __future__ import annotations

_FOLLOWUP_DDL = """
CREATE TABLE IF NOT EXISTS upper_gi_followup (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    report_id INTEGER NOT NULL REFERENCES upper_gi_v2_report(id) ON DELETE CASCADE,
    followup_date TEXT NOT NULL DEFAULT '',
    clinical_notes TEXT NOT NULL DEFAULT '',
    histopathology_result TEXT NOT NULL DEFAULT '',
    lab_results TEXT NOT NULL DEFAULT '',
    imaging_results TEXT NOT NULL DEFAULT '',
    clinical_status TEXT NOT NULL DEFAULT '',
    outcome TEXT NOT NULL DEFAULT '',
    management_plan TEXT NOT NULL DEFAULT '',
    free_notes TEXT NOT NULL DEFAULT '',
    created_by TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT '',
    updated_by TEXT NOT NULL DEFAULT '',
    updated_at TEXT NOT NULL DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_upper_gi_followup_report ON upper_gi_followup(report_id);

CREATE TABLE IF NOT EXISTS upper_gi_research (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    report_id INTEGER NOT NULL UNIQUE REFERENCES upper_gi_v2_report(id) ON DELETE CASCADE,
    indication_summary TEXT NOT NULL DEFAULT '',
    urgency TEXT NOT NULL DEFAULT '',
    asa_class TEXT NOT NULL DEFAULT '',
    d2_reached TEXT NOT NULL DEFAULT '',
    retroflexion_performed TEXT NOT NULL DEFAULT '',
    procedure_duration_min TEXT NOT NULL DEFAULT '',
    variceal_banding_performed TEXT NOT NULL DEFAULT '',
    bands_placed TEXT NOT NULL DEFAULT '',
    variceal_grade TEXT NOT NULL DEFAULT '',
    active_bleeding_at_banding TEXT NOT NULL DEFAULT '',
    hemostasis_achieved_banding TEXT NOT NULL DEFAULT '',
    hemostasis_performed TEXT NOT NULL DEFAULT '',
    forrest_classification TEXT NOT NULL DEFAULT '',
    hemostasis_success TEXT NOT NULL DEFAULT '',
    immediate_complication TEXT NOT NULL DEFAULT '',
    complication_types TEXT NOT NULL DEFAULT '',
    procedure_completed TEXT NOT NULL DEFAULT '',
    surveillance_interval TEXT NOT NULL DEFAULT '',
    follow_up_procedure TEXT NOT NULL DEFAULT '',
    sclerotherapy_performed TEXT NOT NULL DEFAULT '',
    intervention_peg TEXT NOT NULL DEFAULT '',
    intervention_polypectomy TEXT NOT NULL DEFAULT '',
    intervention_dilatation TEXT NOT NULL DEFAULT '',
    intervention_emr_esd TEXT NOT NULL DEFAULT '',
    other_interventions_detail TEXT NOT NULL DEFAULT '',
    updated_at TEXT NOT NULL DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_upper_gi_research_report ON upper_gi_research(report_id);
"""


def _ensure_parent_report_table(dbconn) -> None:
    """Parent table must exist before follow-up / research FK tables."""
    from advanced_reports.configs import PROCEDURE_REGISTRY
    from advanced_reports.schema import _ensure_report_tables

    cfg = PROCEDURE_REGISTRY.get('upper_gi_v2')
    if cfg:
        _ensure_report_tables(dbconn, cfg)
        return
    exists = dbconn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='upper_gi_v2_report' LIMIT 1"
    ).fetchone()
    if not exists:
        raise RuntimeError(
            'Cannot initialize EGD schema: upper_gi_v2_report is missing and '
            'upper_gi_v2 is not registered in PROCEDURE_REGISTRY'
        )


def init_egd_schema(dbconn) -> None:
    """Create EGD structured-report satellite tables (always idempotent)."""
    _ensure_parent_report_table(dbconn)
    dbconn.executescript(_FOLLOWUP_DDL)
    _migrate_egd_research_columns(dbconn)


def _migrate_egd_research_columns(dbconn) -> None:
    cols = {r[1] for r in dbconn.execute("PRAGMA table_info(upper_gi_research)").fetchall()}
    for col, ddl in (
        ('sclerotherapy_performed', "TEXT NOT NULL DEFAULT ''"),
        ('intervention_peg', "TEXT NOT NULL DEFAULT ''"),
        ('intervention_polypectomy', "TEXT NOT NULL DEFAULT ''"),
        ('intervention_dilatation', "TEXT NOT NULL DEFAULT ''"),
        ('intervention_emr_esd', "TEXT NOT NULL DEFAULT ''"),
        ('other_interventions_detail', "TEXT NOT NULL DEFAULT ''"),
    ):
        if col not in cols:
            dbconn.execute(f'ALTER TABLE upper_gi_research ADD COLUMN {col} {ddl}')
