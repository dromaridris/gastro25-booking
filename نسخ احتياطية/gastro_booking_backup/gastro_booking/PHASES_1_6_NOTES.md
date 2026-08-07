# Admit→Discharge phases 1–6 — what shipped

Date: 2026-08-04  
Scope: top audit recommendations for `gastro_booking` ward journey.

---

## Phase 1 — Discharge gate + checklist

**Shipped**
- Hard gate on `POST /ward/discharge`: routine discharge blocked without a `ward_discharge_summary`.
- Override path: LAMA / DOR / expired **or** explicit override checkbox, both require `override_reason`.
- Checklist wired to real data: discharge summary, `gi_history_session.final_diagnosis`, `gi_management_plan.approval_status == approved`.
- Shown on ward bed board + discharge modal + patient page.
- JSON helper: `GET /ward/patient/<id>/discharge-checklist`.

**Files:** `ward/services.py`, `ward/routes.py`, `templates/ward/dashboard.html`, `templates/ward/patient.html`

**Manual test**
1. Admit a patient; open Discharge without summary → Confirm disabled / server rejects.
2. Save discharge summary on patient page → discharge succeeds.
3. Without summary, choose LAMA + reason → discharge succeeds; movement note includes override.

---

## Phase 2 — CI → Ward one-way export

**Shipped**
- Explicit `POST /clinical-intel/<id>/export-to-ward` (HPI / note / both).
- `history_bridge.export_ci_summary_to_ward` merges consultation documentation into ward narrative (`hpi` + `ci_export`) and/or `ward_clinical_note` type `ci_export`.
- No answer dual-write (`ci_*` remains canonical Bates).
- UI copy on CI new/consult + ward clinical workflow + `HISTORY_MIGRATION.md`.

**Files:** `clinical_intelligence/modules/history_bridge.py`, `clinical_intelligence/routes.py`, `templates/clinical_intelligence/consult.html`, `templates/clinical_intelligence/new.html`, `templates/gi/clinical_workflow.html`, `clinical_intelligence/HISTORY_MIGRATION.md`

**Manual test**
1. From ward workflow open CI History (linked `ward_patient_id`).
2. Answer a few questions → Consult → **Export CI → Ward**.
3. Confirm ward patient note / clinical workflow HPI contains export block.

---

## Phase 3 — AI `alert()` → in-page review UI

**Shipped**
- Replaced alert-only AI toolbar results with `#ai-review-panel` Accept/Dismiss list.
- Accept inserts into diagnosis / examination / plan / summary fields when present; user still saves the form to persist.

**Files:** `templates/gi/clinical_workflow.html`

**Manual test**
1. Open clinical workflow with a session.
2. Click Differential AI / Management AI / etc.
3. Review panel appears; Accept fills a field; Dismiss hides item. No `alert()` for results.

---

## Phase 4 — Expand CI reasoning + investigation packs

**Shipped** starter packs (symptom CCs only) for:
`hematemesis`, `melena`, `hematochezia`, `jaundice`, `diarrhea`, `vomiting`, `abdominal_distention`, plus `heartburn`, `constipation`, `dysphagia`.
- Manifest revision bumped; reasoning + investigation lists updated (11 each including abdominal_pain).
- Generator: `scripts/generate_ci_starter_rule_packs.py`.

**Files:** `clinical_knowledge/rules/reasoning/*.json`, `clinical_knowledge/rules/investigation/*.json`, `clinical_knowledge/manifest.json`, `scripts/generate_ci_starter_rule_packs.py`

**Manual test**
1. New CI encounter with `CC_hematemesis` (or jaundice/diarrhea…).
2. Answer enough history → Consult shows patterns / IX suggestions beyond abdominal pain only.

---

## Phase 5 — Transfer UI

**Shipped**
- Transfer button on ward top bar + per-occupied-bed **Move**.
- Modal: from occupied bed → to available/reserved bed; client validation + existing `POST /ward/transfer` server checks.

**Files:** `templates/ward/dashboard.html` (uses existing `ward/routes.py` transfer)

**Manual test**
1. With one occupied + one free bed, open Transfer, select from/to, confirm.
2. Source becomes cleaning; destination occupied.

---

## Phase 6 — Booking ↔ Ward identity link

**Shipped**
- Admit requires MRN **or** skip reason.
- Patient hub banner + `POST /ward/patient/<id>/mrn` to save/link `gi_patient_identity`.
- Linked booking appointments by MRN on ward patient page (`patient_identity_service.list_appointments_for_ward_patient`).

**Files:** `ward/routes.py`, `templates/ward/dashboard.html`, `templates/ward/patient.html`, `gi_platform/patient_identity_service.py`

**Manual test**
1. Admit without MRN and without skip reason → blocked.
2. Admit with MRN that exists on an `appointment` row → patient page lists appointments.
3. Add MRN later via patient form → appointments appear after refresh.

---

## Smoke checks run

- Discharge gate unit asserts (block / LAMA+reason / override).
- Ward routes import.
- CI reasoning/investigation engines load all 10 new packs.
- Question IDs referenced in new reasoning packs resolve in `questions/library.json`.
- Export highlight builder smoke.
