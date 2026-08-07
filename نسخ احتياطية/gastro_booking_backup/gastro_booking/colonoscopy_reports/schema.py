"""SQLite schema for colonoscopy follow-up and research tables."""

from __future__ import annotations

_FOLLOWUP_DDL = """
CREATE TABLE IF NOT EXISTS colonoscopy_followup (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    report_id INTEGER NOT NULL REFERENCES colonoscopy_v2_report(id) ON DELETE CASCADE,
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

CREATE INDEX IF NOT EXISTS idx_colonoscopy_followup_report ON colonoscopy_followup(report_id);

CREATE TABLE IF NOT EXISTS colonoscopy_research (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    report_id INTEGER NOT NULL UNIQUE REFERENCES colonoscopy_v2_report(id) ON DELETE CASCADE,
    indication_summary TEXT NOT NULL DEFAULT '',
    urgency TEXT NOT NULL DEFAULT '',
    asa_class TEXT NOT NULL DEFAULT '',
    caecum_reached TEXT NOT NULL DEFAULT '',
    ti_intubated TEXT NOT NULL DEFAULT '',
    withdrawal_time_min TEXT NOT NULL DEFAULT '',
    bbps_right TEXT NOT NULL DEFAULT '',
    bbps_transverse TEXT NOT NULL DEFAULT '',
    bbps_left TEXT NOT NULL DEFAULT '',
    bbps_total TEXT NOT NULL DEFAULT '',
    prep_regimen TEXT NOT NULL DEFAULT '',
    polypectomy_performed TEXT NOT NULL DEFAULT '',
    polyps_resected_count TEXT NOT NULL DEFAULT '',
    adenoma_documented TEXT NOT NULL DEFAULT '',
    immediate_complication TEXT NOT NULL DEFAULT '',
    complication_types TEXT NOT NULL DEFAULT '',
    procedure_completed TEXT NOT NULL DEFAULT '',
    surveillance_interval TEXT NOT NULL DEFAULT '',
    follow_up_procedure TEXT NOT NULL DEFAULT '',
    updated_at TEXT NOT NULL DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_colonoscopy_research_report ON colonoscopy_research(report_id);
"""


def _ensure_parent_report_table(dbconn) -> None:
    from advanced_reports.configs import PROCEDURE_REGISTRY
    from advanced_reports.schema import _ensure_report_tables

    cfg = PROCEDURE_REGISTRY.get('colonoscopy_v2')
    if cfg:
        _ensure_report_tables(dbconn, cfg)
        return
    exists = dbconn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='colonoscopy_v2_report' LIMIT 1"
    ).fetchone()
    if not exists:
        raise RuntimeError(
            'Cannot initialize colonoscopy schema: colonoscopy_v2_report is missing and '
            'colonoscopy_v2 is not registered in PROCEDURE_REGISTRY'
        )


def init_colonoscopy_schema(dbconn) -> None:
    """Create colonoscopy structured-report satellite tables (idempotent)."""
    _ensure_parent_report_table(dbconn)
    dbconn.executescript(_FOLLOWUP_DDL)
