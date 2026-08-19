# Clinical Intelligence — STATUS (Phases 1–16)

Last updated: 2026-08-04

## History migration (2026-08-04)

**Canonical structured history = this module** (JSON knowledge + History Engine).  
Legacy ward / Guided History AI / History Templates remain for inpatient documentation & compatibility but are labeled **legacy** in nav/UI.  
Details: [`HISTORY_MIGRATION.md`](HISTORY_MIGRATION.md).

| Rule | Choice |
|------|--------|
| Source of truth for Bates Q&A | `clinical_knowledge/` + `ci_history_answer` |
| Ward multi-symptom CDS interview | Kept on `gi_history_*` — separate schema, no dual-write |
| Guided History AI | Deprecated in UI (routes kept) |
| Ward deep-link | `/clinical-intel/new?ward_patient_id=&suggest_complaint=` |

## Completion matrix

| Phase / prompt | Name | Status | Entry point |
|---------------:|------|--------|-------------|
| 1–3 | Dictionary / templates / Q library | **Done** (knowledge) | `clinical_knowledge/` |
| 4 | History Engine | **Done** | Flowchart UI (stages + branch arms + trail + coach) at `/clinical-intel/<id>/history` |
| 5 | Physical Examination Engine | **Done** (`abdominal_pain`) | `/clinical-intel/<id>/exam` |
| 6 | Reasoning Engine | **Done** | Consult + `reasoning_engine.py` |
| 7 | Investigation framework | **Done** | Consult / IX page |
| 8 | Management framework | **Done** (no drugs) | Consult |
| — | Consultation glue | **Done** | `/clinical-intel/<id>/consult` |
| 9 | Investigation **interpretation** | **Done** | `/clinical-intel/<id>/investigations` |
| 10 | Scoring engine | **Done** | Consult (`scoring_engine.py`) |
| 11 | Procedure engine | **Done** | IX/Consult (`procedure_engine.py`) |
| 12 | Knowledge Importer | **Done** | `/clinical-intel/knowledge` + CLI |
| 13 | Evidence / versioning | **Done** | `evidence/registry.json` + reload |
| 14 | AI assist layer | **Done** (optional, gated) | Consult AI panel |
| 15 | Research engine | **Done** | `/clinical-intel/<id>/research` |
| 16 | Education engine | **Done** | `/clinical-intel/<id>/teach` |
| — | GI overlay | **Done** (thin) | Endoscopy booking hints |
| — | Final integration | **Done** | bootstrap + schema + nav + smoke |
| — | History cleanup vs legacy | **Done** | `HISTORY_MIGRATION.md` + ward bridge |

## How to open

1. Log in → **Clinical → Clinical Intelligence** (`/clinical-intel/`).
2. Start **Abdominal pain** → History → Exam → IX → Consult / Teach / Research.
3. From a ward patient: Clinical workflow → **Clinical Intelligence history** (links `ward_patient_id`).
4. Knowledge admin (admin/hod/specialist): `/clinical-intel/knowledge`.
5. CLI: `python -m clinical_intelligence.cli validate|version|reload|import …`

## Env vars (AI — optional)

| Variable | Purpose |
|----------|---------|
| `CI_AI_ENABLED` | `true` to allow live AI assist |
| `OPENAI_API_KEY` or `CI_OPENAI_API_KEY` | API key (graceful offline fallback if missing) |
| `CI_AI_MODEL` / `OPENAI_MODEL` | Model name (default `gpt-4o-mini`) |
| `CLINICAL_KNOWLEDGE_ROOT` | Override knowledge root path |

Without a key, AI assist uses **offline rule-based** next-question summary — never crashes, never claims diagnostic authority.

## Honest limits (not blockers)

- Exam / reasoning / scoring / interpretation / education / procedure **packs** are fully wired for **`CC_abdominal_pain`**; other complaints have history templates and use engines when packs exist (graceful empty otherwise).
- Procedure engine suggests indications/prep/risks; it does **not** replace EGD/colonoscopy report modules.
- AI must never be sole diagnostic authority (enforced in code + UI disclaimer).
- Ward patient link stores `ward_patient_id` on `ci_encounter`; answers stay in `ci_*` only (no auto-sync to `gi_history_answer`).

## Smoke

```bash
python test_ci_smoke.py
python -m clinical_intelligence.cli validate
```
