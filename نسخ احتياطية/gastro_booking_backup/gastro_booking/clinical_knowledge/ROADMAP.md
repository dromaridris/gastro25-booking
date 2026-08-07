# ROADMAP V1 — Clinical Intelligence Platform

## Decision (locked)

1. Build a **Clinical Intelligence Platform**; GI is Module #1 only.
2. Finish **Phases 1–3 as JSON knowledge** before any programming.
3. **Phase 4** is the first code: History Engine = Complaint → Load Template → Ask Questions → Save Answers.
4. Prefer few large Cursor prompts that emit complete JSON packs, not micro-edits.

## Phase summaries

| Phase | Name | Status |
|------:|------|--------|
| 1 | Clinical Dictionary | Done |
| 2 | History Templates (Bates) | Done |
| 3 | Universal Question Library | Done |
| 4 | History Engine | **Done** — `clinical_intelligence/` |
| 5 | Physical Examination Engine | **Done** |
| 6 | Reasoning / Differential (data-driven) | **Done** |
| 7 | Investigation Engine (+ interpretation) | **Done** |
| 8 | Management Engine | **Done** (no Rx) |
| 9 | Scoring | **Done** |
| 10 | Procedure engine | **Done** (indications/prep/risks) |
| 11 | Knowledge Importer + Evidence versioning | **Done** |
| 12 | AI assist (optional, non-authoritative) | **Done** |
| 13 | Research engine | **Done** |
| 14 | Education / teach mode | **Done** |
| 15–16 | Integration / STATUS | **Done** — see `clinical_intelligence/STATUS.md` |

## Seed status (Phases 1–3)

| Deliverable | Location | Seed |
|-------------|----------|------|
| Dictionary packs (13 types) | `dictionary/` | Active + DX suspects for reasoning |
| Question library | `questions/library.json` | `Q000001`… (~92) |
| History templates | `templates/history/` | 11 complaints |
| Exam / rules | `templates/exam/`, `rules/` | abdominal_pain depth |
| Evidence | `evidence/registry.json` | knowledge_version 1.4.0 |
| Schemas | `schemas/` | dictionary / question / history_template |
| Manifest | `manifest.json` | phase 1–16 |

## Runtime

Package: **`clinical_intelligence/`**  
UI: **`/clinical-intel/`**  
Detail: **`clinical_intelligence/STATUS.md`**
