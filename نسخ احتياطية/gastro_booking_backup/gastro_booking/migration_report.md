# GastroIntelligence → Gastro25 Migration Report

**Date:** 2026-07-29  
**Primary application:** Gastro25 (`gastro_booking/`)  
**Source:** GastroIntelligence (`gi_import/source/`)

## Summary

Gastro25 remains the single integrated Flask application. Booking, authentication, users, roles, and **all ERCP functionality** were preserved. New capabilities were added by **extension only**:

1. **GI module import tree** copied into `gi_import/source/` for reuse/adaptation.
2. **Ward module** added (SQLite) — bed board, admission, transfer, discharge, clinical notes shell.
3. **Booking / Ward** primary navigation entry points in `base.html`.
4. **Extended procedure labels** for non-ERCP endoscopy templates in booking.
5. **Additive database tables** for ward management (`ward_*`).

## ERCP protection

No ERCP routes, templates, print layouts, registry queries, or ERCP-specific constants were edited.  
`app.py` ERCP regions (lines ~88–3467 in the pre-migration file) are unchanged.  
Only the **bootstrap footer** of `app.py` was extended to register the ward integration.

## Backup

Pre-migration backup created at:

`backups/migration_20260729/`

Contains: `app.py`, `base.html`, `root_app.py`, `gastro_booking.db` (snapshot).

## Architecture after migration

```
gastro_booking/
├── app.py                 # existing monolith + bootstrap hook
├── migration_bootstrap.py # registers ward + extended procedures
├── procedure_extensions.py
├── ward/                  # new inpatient module (SQLite)
├── gi_integration/        # GI module catalog + workflow map
├── gi_import/source/    # copied GastroIntelligence code (reference/runtime adapter TBD)
└── templates/ward/        # ward UI
```

## What works now

| Area | Status |
|------|--------|
| Booking (existing) | Unchanged behaviour |
| ERCP module | Unchanged |
| Dilatation module | Unchanged |
| Ward dashboard | Bed 1–30 seeded, extra beds on demand |
| Ward admit / discharge / transfer | Working (SQLite) |
| Ward patient clinical shell | Section map to imported GI modules |
| Extended booking procedure names | Labels + special-procedure booking path |
| Full GI SQLAlchemy stack inside Ward | **Not yet wired** (see unresolved_conflicts.md) |

## Next integration phase (not in this migration)

- SQLite/Flask-session adapter for GI services (currently PostgreSQL/SQLAlchemy)
- Encounter-linked ward patient ↔ GI clinical_history workflow
- Knowledge library live provider inside ward patient page
- Procedure report templates for imported endoscopy types (non-ERCP)
