# Admit→Discharge phases 7–8 + lab propagation — what shipped

Date: 2026-08-04  
Scope: freeze legacy history admin writes, document `gi_import` as reference-only, auto-propagate ward lab results.

---

## Phase 7 — Freeze legacy History AI Training / Templates writes

**Shipped**
- Helper: `gi_platform/legacy_history_freeze.py` — writes frozen unless `GASTRO_ALLOW_LEGACY_HISTORY_WRITES=1|true|yes`.
- POST create/edit/delete blocked on:
  - `/admin/history-ai-training` (+ question/rule endpoints)
  - `/admin/history-templates` (+ new/edit/delete)
- GET/list/view remain available for admin/HOD/specialist (read compatibility).
- UI banners + disabled forms; point to Clinical Intelligence / `clinical_knowledge/`.
- **No** table deletes or data wipes. Guided history / `gi_history_template*` / approvals / registrar workflows untouched.
- Idempotent catalogue seeds on History AI Training GET still run (not admin template edits).

**Files:** `gi_platform/legacy_history_freeze.py`, `gi_routes/history_templates.py`, `gi_routes/history_ai_training.py`, `templates/gi/history_templates.html`, `templates/gi/history_template_edit.html`, `templates/gi/history_ai_training.html`

**Manual test**
1. As admin, open `/admin/history-templates` and `/admin/history-ai-training` — see freeze banner; write controls hidden/disabled.
2. POST create/save (e.g. curl or form) → flash freeze message; no DB change.
3. Set `GASTRO_ALLOW_LEGACY_HISTORY_WRITES=1`, restart → writes work again (emergency only).

---

## Phase 8 — gi_import as reference-only

**Shipped**
- `GI_IMPORT.md` — reference/import source; live runtime is `gi_platform` + `clinical_intelligence` + `clinical_knowledge`.
- `SITE_AUDIT.md` updated (not registered as Flask; history writes frozen note).
- Comment in `gi_routes/__init__.py` that `gi_import` must never be registered.
- Confirmed: `app.py` does not import/register `gi_import` routes. Advanced reports may still **read** schema/vocab JSON under `gi_import/` as data.

**Manual test**
1. App starts normally.
2. No `/investigations/...` routes from `gi_import/source` appear in Flask map (live lab is `/laboratory/patient/<id>`).

---

## EXTRA — Lab results auto-propagation

**Shipped**
- `gi_platform/lab_propagation.py` — single sync layer; **SoT remains `gi_lab_result`**.
- Called from `lab_service.enter_lab_result` and `patient_journey_service.record_lab_result` after commit.
- Actions on save:
  - Backfill `mrn` on result when ward patient has MRN
  - Recalculate scores (same as before)
  - Idempotent mirror into linked `ci_encounter` rows as `ward:{test_code}` IX results with note `[ward_lab auto]` — **never** overwrites clinician categorical CI IX codes
- Read-through / display:
  - Clinical workflow Investigations section shows lab results table
  - CI Investigations + Consult show ward labs; docs draft appends labs block
  - Ward patient discharge summary prefills labs block when no prior summary; lists recent labs

**Preserved:** registrar order/plan approvals, existing save posts, discharge gate, CI export, AI Accept/Dismiss, transfer, MRN linking.

**Files:** `gi_platform/lab_propagation.py`, `gi_platform/lab_service.py`, `gi_platform/patient_journey_service.py`, `gi_routes/clinical.py`, `templates/gi/clinical_workflow.html`, `clinical_intelligence/routes.py`, `templates/clinical_intelligence/investigations.html`, `templates/clinical_intelligence/consult.html`, `ward/routes.py`, `templates/ward/patient.html`

**Manual test**
1. Open Laboratory for a ward patient; enter a result (e.g. Hemoglobin).
2. Clinical workflow → Investigations: result appears in lab table without re-entry.
3. Open/create CI encounter with same `ward_patient_id` → Investigations/Consult show ward labs; `ci_ix_result` has `ward:lab.*` rows only for auto sync.
4. Enter a categorical CI result manually → still present after another lab save (not wiped).
5. Scores page / laboratory flash still reflects auto-recalc.
6. Discharge summary draft on patient page includes labs when empty.

---

## Smoke checks run

- `python test_phases_7_8_smoke.py` — freeze default ON; override env works; lab save → patient list + CI `ward:` sync; clinician `ci_ix_result` preserved; route imports OK.
- `from app import app` — starts; history-ai / history-templates / laboratory routes present; no `gi_import` Flask routes.