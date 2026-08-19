# Unresolved Conflicts & Pending Integration

## 1. GastroIntelligence runtime stack (major)

**Conflict:** GI modules expect Flask-SQLAlchemy, PostgreSQL-oriented models, `permission_engine`, and blueprint factory wiring. Gastro25 uses SQLite + session auth + monolithic `app.py`.

**Status:** Source copied to `gi_import/source/` but **not executed in-process** yet.

**Resolution path:** Build `gi_integration/sqlite_adapter.py` (or optional PostgreSQL sidecar) without modifying ERCP.

---

## 2. Duplicate booking / patient systems

**Conflict:** GI has `patients`, `appointments`, `encounters` modules separate from Gastro25 `appointment` table.

**Status:** Gastro25 booking remains authoritative. Ward uses `ward_patient` until bi-directional sync is defined.

**Resolution path:** MRN-based linking; do not replace Gastro25 booking APIs.

---

## 3. Authentication & permissions

**Conflict:** GI uses RBAC permission codes (`inpatient:view`, `knowledge_library:edit`, …). Gastro25 uses 6 role strings.

**Status:** Ward routes use existing Gastro25 `@roles_required(...)`.

**Resolution path:** Map GI permissions → Gastro25 roles in adapter layer.

---

## 4. Branding / navigation

**Conflict:** GI `base.html` + Bootstrap 5 design system vs Gastro25 crimson topbar.

**Status:** Gastro25 branding kept. Ward templates extend Gastro25 `base.html` only.

**Resolution path:** No GI branding import (per requirements).

---

## 5. Clinical workflow depth in Ward patient page

**Conflict:** User requirement lists full History Builder, AI assistant, knowledge search, etc.

**Status:** Ward patient page shows **workflow section map** + native clinical notes. GI modules not yet invoked.

**Resolution path:** Phase 2 — mount GI services per section behind feature flags.

---

## 6. Non-ERCP procedure templates

**Conflict:** 16 new procedure types added as booking labels; report templates not yet built (ERCP/dilatation patterns exist).

**Status:** `procedure_extensions.py` extends labels + special-procedure booking validation only.

**Resolution path:** Add report modules mirroring dilatation pattern (excluding ERCP files).

---

## 7. Root `app.py` launcher vs `gastro_booking/app.py`

**Conflict:** Two entry points; `GASTRO_DATA_DIR` must point to `gastro_booking/` for production data.

**Status:** Fixed locally — launcher sets `GASTRO_DATA_DIR` to `gastro_booking/`.

---

## 8. Git / deployment

**Conflict:** Partial commit (print templates only) on remote; migration files uncommitted.

**Status:** Migration deliverables are local until next deploy push.

---

## ERCP verification

No byte-level ERCP file changes in this migration. If deployment requires proof, diff `backups/migration_20260729/` ERCP templates against current tree.
