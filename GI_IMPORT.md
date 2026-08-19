# gi_import — reference / import source only

**Status:** kept on disk for schemas, vocabulary seeds, and future porting.  
**Not** a live Flask application module.

## Runtime (live)

| Layer | Role |
|-------|------|
| `gi_platform/` | Live services, adapters, clinical AI context builders |
| `gi_routes/` | Live Flask route registration |
| `clinical_intelligence/` + `clinical_knowledge/` | Canonical Bates history / CI |
| `advanced_reports/` | May **read** JSON schemas / vocab from under `gi_import/source/...` as data files |

## Rules

1. Do **not** register `gi_import` blueprints or routes on the Gastro25 app.
2. Do **not** delete `gi_import/` without explicit approval (future asset — see `SITE_AUDIT.md`).
3. Prefer copying or adapting needed pieces into `gi_platform` / `clinical_knowledge` rather than importing runtime write paths from `gi_import/source/modules/`.
4. Accidental `from gi_import...` of Flask routes / SQLAlchemy app models must not be wired into startup.

## Confirmed (phases 7–8)

- `app.py` does not import or register `gi_import` routes.
- `gi_routes/__init__.py` registers only live `gi_*` modules.
- Read-only schema/vocab loaders under `advanced_reports/` are intentional data access, not live import admin.

See also: `SITE_AUDIT.md`, `gi_registry/AI_MIGRATION_INVENTORY.md`.
