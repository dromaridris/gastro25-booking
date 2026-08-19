# Files Modified — GI → Gastro25 Migration

## Modified (intentional)

| File | Change |
|------|--------|
| `app.py` | Bootstrap footer only: calls `register_migration_extensions()` after `init_db()`. **No ERCP route/template/SQL changes.** |
| `templates/base.html` | Added primary nav links **Booking** and **Ward** at start of `mainnav`. Existing links unchanged. |
| `app.py` (repo root) | Previously changed to launcher + `GASTRO_DATA_DIR`; not part of GI migration but present in workspace. |

## Explicitly NOT modified (ERCP freeze)

- `templates/ercp_report.html`
- `templates/ercp_print.html`
- `templates/patient_ercp_overview.html`
- `templates/ercp_research_registry.html`
- `templates/_repeat_ercp_modal.html`
- ERCP sections inside `app.py` (~lines 88–3467)
- `ercp_images/` data
- ERCP tables / migrations inside `init_db()`

## Not modified in this migration

- `static/css/style.css`
- `static/js/app.js` (booking modal procedure list uses server `PROCEDURE_LABELS` — extended via `procedure_extensions.py`)
- Dilatation templates and routes
- Authentication routes
- Existing `settings`, `holiday`, `appointment` logic
