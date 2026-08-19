# Files Added — GI → Gastro25 Migration

## Integration layer

- `migration_bootstrap.py`
- `procedure_extensions.py`
- `gi_integration/__init__.py`
- `gi_integration/registry.py`

## Ward module

- `ward/__init__.py`
- `ward/schema.py`
- `ward/services.py`
- `ward/routes.py`
- `templates/ward/dashboard.html`
- `templates/ward/patient.html`

## Imported GastroIntelligence source (copied)

- `gi_import/source/modules/` — 46+ module packages (471 files)
- `gi_import/source/engines/` — permission_engine, audit_engine
- `gi_import/source/platform/` — template_context, security, productivity, qr
- `gi_import/source/core/` — base_model, route_helpers, exceptions
- `gi_import/source/ui/` — navigation, quick_actions, context

## Backup

- `backups/migration_20260729/app.py`
- `backups/migration_20260729/base.html`
- `backups/migration_20260729/root_app.py`
- `backups/migration_20260729/gastro_booking.db`

## Documentation

- `migration_report.md`
- `files_added.md`
- `files_modified.md`
- `database_changes.md`
- `unresolved_conflicts.md`
