# History systems — migration decision

**Date:** 2026-08-04 (updated same day — unified ward workflow UI)  
**Decision:** Clinical Intelligence (`clinical_intelligence/` + `clinical_knowledge/templates/history/`) is the **canonical** structured history path going forward.

Answers are **not** dual-written between CI and legacy ward schemas.

**Ward UI (2026-08-04):** Clinical workflow presents **one spine** — History → Examination → Investigations → Summary → Plan. Laboratory, scores, narrative draft, differential/IX/management AI, and journey tools are nested **inside** those steps. Guided History AI is under Legacy/advanced only.

---

## Inventory

### NEW — Clinical Intelligence (canonical)

| Surface | Path / route | Storage |
|---------|----------------|---------|
| History Engine | `clinical_intelligence/history_engine.py` | — |
| Templates | `clinical_knowledge/templates/history/*.json` | files |
| Q library | `clinical_knowledge/questions/library.json` | files |
| Branching | `clinical_knowledge/rules/history_branching/` | files |
| UI | `/clinical-intel/<id>/history` | `ci_history_answer` |
| Encounter | `/clinical-intel/new` | `ci_encounter` (optional `ward_patient_id`) |
| Knowledge admin | `/clinical-intel/knowledge` | JSON import |

### OLD — still needed for ward / documentation (kept, bounded)

| Surface | Path / route | Storage | Role after decision |
|---------|----------------|---------|---------------------|
| Ward clinical workflow | `/ward/patient/<id>/clinical` | `gi_history_session`, `gi_history_answer` | Multi-symptom adaptive Qs for CDS, exam text, summary, plan, labs — **not** the Bates SOE |
| Catalogue adaptive engine | `gi_platform/catalogue_runtime.py`, `decision_support/engines/adaptive_history_engine.py` | KL objects + `gi_history_answer` | Feeds ward workflow only |
| Narrative / print | `narrative_engine`, `history_print.html` | `gi_history_narrative` | Documentation |

### OLD — legacy parallel interview / admin (deprecated in UI, code kept)

| Surface | Path / route | Storage | Role after decision |
|---------|----------------|---------|---------------------|
| Guided History AI | `/clinical-history-ai/...` | `gi_guided_history_*` | **Legacy** — banner + nav demoted; prefer CI |
| History AI Training | `/admin/history-ai-training` | guided Qs + rules | **Legacy** admin |
| Disease History Templates | `/admin/history-templates` | `gi_history_template*` | **Legacy** admin |
| Import source (unwired) | `gi_import/source/modules/clinical_history*` | N/A | Reference only — not registered as live Flask routes |

### Untouched (out of scope)

ERCP / booking / MCQ / endoscopy reports / unit ops — no change.

---

## Conflicts found

1. **Three question engines** for “history”:
   - CI JSON History Engine (`CC_*` packs)
   - Ward catalogue adaptive questions (`hist.*` → `gi_history_answer`)
   - Guided History AI (`gi_guided_history_answer`)
2. **Two template admin UIs**: CI knowledge JSON vs `gi_history_template` / History AI Training — clinicians could edit the wrong source.
3. **Nav** offered “Clinical Intelligence”, “History AI Training”, and “History Templates” without saying which is authoritative.
4. **No dual-write bug** between `ci_*` and `gi_*` (separate tables) — conflict was **UX / clinical logic**, not silent overwrite. Guided AI *does* sync approved drafts into ward narrative summary (legacy path only).

---

## Decision (implemented)

| Rule | Action |
|------|--------|
| Canonical structured history | Clinical Intelligence |
| Ward workflow | Keep for inpatient CDS/docs; banner points to CI; primary CTA = CI History |
| Guided History AI | Keep routes for compatibility; label **legacy**; demote in workflow nav |
| History Templates / AI Training | Keep routes; label **legacy** in nav + pages |
| Answer sync | **None** between `ci_history_answer` and `gi_history_answer` / guided answers |
| Ward → CI bridge | `ci_new_encounter?ward_patient_id=&suggest_complaint=` + complaint map in `modules/history_bridge.py` |

---

## How clinicians should choose

1. **Structured Bates-style interview / teaching / CI consult** → Clinical → **Clinical Intelligence**
2. **Ward patient chart** (labs, plan, registrar approvals, multi-symptom CDS) → ward **Clinical workflow**; use CI link for structured history when needed
3. **Legacy guided AI narrative** → only if you intentionally need the old draft/approve flow

---

## Follow-ups

- Port remaining `hist.*` complaints into `CC_*` JSON packs
- ~~Optional one-way export of CI summary text into ward narrative (explicit user action)~~ **Done** — `POST /clinical-intel/<id>/export-to-ward` via `history_bridge.export_ci_summary_to_ward` (Consult UI). No silent dual-write of answers.
- Eventually freeze writes to History AI Training once CI packs cover all ward complaints

**Done (phase 7):** Legacy History AI Training + History Templates writes are frozen by default
(`GASTRO_ALLOW_LEGACY_HISTORY_WRITES=1` emergency override). See `PHASES_7_8_NOTES.md`.

### Policy reminder (clinicians)

| System | Role |
|--------|------|
| **Clinical Intelligence** | Canonical Bates-structured history / teaching / consult |
| **Ward clinical workflow** | Operational inpatient chart (CDS adaptive Qs, labs, plan, approvals) |
| **Export CI → Ward** | Explicit action when consult highlights should appear in ward HPI/notes |
