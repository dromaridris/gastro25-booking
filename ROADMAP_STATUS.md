# ROADMAP_STATUS — Phases 1–8

Updated: 2026-08-04

| Phase | Name | Status | Primary entry |
|------:|------|--------|---------------|
| 1 | Knowledge Foundation | **DONE** | `/ckp/knowledge/` |
| 2 | Clinical Reasoning Engine | **DONE** | (engine behind encounters) |
| 3 | Clinical Workflow Integration | **DONE** | `/clinical-encounter/` |
| 4 | Documentation & Clinical Records | **DONE** | `/clinical-encounter/<id>/documents` |
| 5 | Clinical Decision Support | **DONE** | `/clinical-encounter/<id>/cds` |
| 6 | Longitudinal Clinical Intelligence | **DONE** | `/ckp/longitudinal/` |
| 7 | Research & Learning Platform | **DONE** | `/ckp/research/` |
| 8 | Enterprise Platform & Ecosystem | **DONE** (foundations) | `/ckp/enterprise/` |

## Smoke test (all phases)
```bash
python scripts/smoke_ckp_phases.py
```
Last run: **ALL PHASE SMOKES PASSED**.

## Notes index
- `PHASE1_NOTES.md` … `PHASE8_NOTES.md`
- `FINAL_PLATFORM_ARCHITECTURE.md`

## Parallel legacy systems (not replaced)
- Ward / booking / MCQ / GI platform / Clinical Intelligence history JSON path

## Next recommended (post-roadmap)
1. Bind ward MRN to CKP `patient_key`
2. Curate real guideline Domain Packs (replace demo assertions)
3. Wire one live adapter (e.g. FHIR read Patient) in a pilot hospital
4. Physician UX polish + Arabic UI toggle using `ckp_i18n_string`
