"""Central database schema registry — every reporting module registers here.

All module tables are created automatically at startup and verified before
the first HTTP request.  New modules MUST call register_schema_module() and
will not run queries against tables that have not been ensured.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from typing import Any

InitFn = Callable[[sqlite3.Connection], None]

_MODULES: dict[str, dict[str, Any]] = {}
_BOOTSTRAPPED = False


def register_schema_module(
    name: str,
    init_fn: InitFn,
    *,
    after: frozenset[str] | set[str] | None = None,
    required_tables: frozenset[str] | set[str] | None = None,
) -> None:
    """Register a schema initializer.  Call at import time from each module."""
    if name in _MODULES:
        raise ValueError(f'Schema module already registered: {name!r}')
    _MODULES[name] = {
        'init': init_fn,
        'after': frozenset(after or ()),
        'required_tables': frozenset(required_tables or ()),
    }


def _bootstrap_registry() -> None:
    global _BOOTSTRAPPED
    if _BOOTSTRAPPED:
        return
    from ward.schema import init_ward_schema
    from procedure_reports.schema import init_procedure_report_schema
    from advanced_reports.schema import init_advanced_report_schema
    from egd_reports.schema import init_egd_schema
    from colonoscopy_reports.schema import init_colonoscopy_schema
    from gi_platform.schema import init_gi_schema_db
    from mcq_bank.schema import init_mcq_bank_schema
    from clinical_intelligence.schema import init_clinical_intelligence_schema
    from clinical_knowledge_platform.schema import init_ckp_schema

    register_schema_module('ward', init_ward_schema)
    register_schema_module('procedure_reports', init_procedure_report_schema)
    register_schema_module(
        'advanced_reports',
        init_advanced_report_schema,
        after={'procedure_reports'},
    )
    register_schema_module(
        'egd_reports',
        init_egd_schema,
        after={'advanced_reports'},
        required_tables={
            'upper_gi_v2_report',
            'upper_gi_research',
            'upper_gi_followup',
        },
    )
    register_schema_module(
        'colonoscopy_reports',
        init_colonoscopy_schema,
        after={'advanced_reports'},
        required_tables={
            'colonoscopy_v2_report',
            'colonoscopy_research',
            'colonoscopy_followup',
        },
    )
    register_schema_module(
        'gi_platform',
        init_gi_schema_db,
        after={'ward'},
    )
    register_schema_module(
        'mcq_bank',
        init_mcq_bank_schema,
        after={'gi_platform'},
    )
    register_schema_module(
        'clinical_intelligence',
        init_clinical_intelligence_schema,
        after={'ward'},
        required_tables={
            'ci_encounter',
            'ci_history_answer',
            'ci_exam_finding',
            'ci_encounter_draft',
            'ci_ix_result',
            'ci_research_item',
            'ci_knowledge_event',
            'ci_ai_assist_log',
        },
    )
    register_schema_module(
        'clinical_knowledge_platform',
        init_ckp_schema,
        after={'ward'},
        required_tables={
            'ckp_domain',
            'ckp_entity',
            'ckp_relationship',
            'ckp_knowledge_release',
            'cre_session',
            'ckp_document',
            'ckp_cds_alert',
            'ckp_longitudinal_memory',
            'ckp_research_registry',
            'ckp_tenant',
            'ckp_integration_endpoint',
        },
    )
    _BOOTSTRAPPED = True


def _table_exists(dbconn: sqlite3.Connection, table: str) -> bool:
    row = dbconn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=? LIMIT 1",
        (table,),
    ).fetchone()
    return row is not None


def _verify_module_tables(dbconn: sqlite3.Connection, name: str) -> None:
    spec = _MODULES[name]
    missing = [t for t in spec['required_tables'] if not _table_exists(dbconn, t)]
    if missing:
        raise RuntimeError(
            f'Schema module {name!r} initialized but missing table(s): {", ".join(missing)}'
        )


def ensure_all_schemas(dbconn: sqlite3.Connection) -> None:
    """Run every registered schema initializer in dependency order (idempotent)."""
    _bootstrap_registry()
    dbconn.execute('PRAGMA foreign_keys = ON')
    done: set[str] = set()
    pending = set(_MODULES.keys())

    while pending:
        progress = False
        for name in list(pending):
            spec = _MODULES[name]
            if not spec['after'] <= done:
                continue
            spec['init'](dbconn)
            if spec['required_tables']:
                _verify_module_tables(dbconn, name)
            done.add(name)
            pending.discard(name)
            progress = True
        if not progress:
            blocked = ', '.join(sorted(pending))
            raise RuntimeError(f'Schema registry deadlock — unresolved modules: {blocked}')

    dbconn.commit()


def ensure_module_schema(dbconn: sqlite3.Connection, module_name: str) -> None:
    """Ensure one module and all of its dependencies (idempotent)."""
    _bootstrap_registry()
    dbconn.execute('PRAGMA foreign_keys = ON')
    if module_name not in _MODULES:
        raise KeyError(f'Unknown schema module: {module_name!r}')

    to_run: list[str] = []
    visiting: set[str] = set()

    def _collect(name: str) -> None:
        if name in visiting:
            return
        visiting.add(name)
        for dep in _MODULES[name]['after']:
            _collect(dep)
        if name not in to_run:
            to_run.append(name)

    _collect(module_name)
    for name in to_run:
        spec = _MODULES[name]
        spec['init'](dbconn)
        if spec['required_tables']:
            _verify_module_tables(dbconn, name)
    dbconn.commit()


def ensure_all_schemas_for_path(db_path: str) -> None:
    """Standalone ensure using a fresh connection (startup / scripts)."""
    dbconn = sqlite3.connect(db_path)
    dbconn.row_factory = sqlite3.Row
    try:
        ensure_all_schemas(dbconn)
    finally:
        dbconn.close()


def install_schema_guard(app, get_db) -> None:
    """Flask before_request hook — guarantees schemas before any route runs."""
    @app.before_request
    def _ensure_module_schemas_before_request():
        if app.config.get('_MODULE_SCHEMAS_READY'):
            return
        dbconn = get_db()
        ensure_all_schemas(dbconn)
        app.config['_MODULE_SCHEMAS_READY'] = True
