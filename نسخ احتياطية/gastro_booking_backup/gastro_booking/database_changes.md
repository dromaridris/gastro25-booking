# Database Changes — GI → Gastro25 Migration

**Policy:** Additive only. No existing tables dropped or overwritten.

## New tables

| Table | Purpose |
|-------|---------|
| `ward` | Ward definition (default: Gastroenterology Ward 25) |
| `ward_bed` | Beds 1–30 (regular) + unlimited `Extra N` rows |
| `ward_patient` | Inpatient identity (MRN, demographics) |
| `ward_admission` | Active/historical bed occupancy |
| `ward_movement` | Admit / transfer / discharge audit trail |
| `ward_clinical_note` | Progress, consultant, follow-up notes (Gastro25-native until GI adapter) |

## Seed data

On first run after migration:

- Ward slug `gastro-25` with **30 regular beds** (`Bed 1` … `Bed 30`)
- Extra beds created only via **Add Extra Bed** (not pre-seeded)

## Unchanged tables

All pre-existing tables remain, including:

- `user`, `appointment`, `holiday`, `settings`, `endoscopist`
- `ercp_report`, `ercp_report_image`, `ercp_followup`, `ercp_research`
- `dilatation_report`, `dilatation_report_image`, `dilatation_followup`, `dilatation_research`

## Migration mechanism

`ward/schema.py` → `init_ward_schema()` called from `migration_bootstrap.register_migration_extensions()` using `CREATE TABLE IF NOT EXISTS`.

No Alembic / Flask-Migrate (consistent with existing Gastro25 `init_db()` pattern).

## GI database models

GastroIntelligence PostgreSQL/SQLAlchemy models under `gi_import/source/` are **not** auto-migrated into SQLite. They require a separate adapter phase (see `unresolved_conflicts.md`).
