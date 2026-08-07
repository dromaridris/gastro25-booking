# PHASE1_NOTES — Clinical Knowledge Foundation

## Status
**Complete** (wired into app schema registry + seed + validation + authoring home).

## What exists
- Package `clinical_knowledge_platform/`
- Tables: `ckp_domain`, `ckp_entity` (+ versions), `ckp_relationship` (+ versions), `ckp_guideline_work`, `ckp_guideline_assertion`, `ckp_knowledge_release`, `ckp_release_member`, `ckp_audit_log`
- Repository API: upsert domain/entity/relationship/guideline, publish release, `graph_for_release`
- Validation: type/orphan/supersedes checks (`validation.py`)
- Demo Domain Pack #1: Gastroenterology (~8+ diseases, symptoms, questions, signs, Ix, pathways) + Cardiology stub domain (proves specialty neutrality)
- UI: `/ckp/knowledge/` + seed button

## Architecture rule
Engine has **no** specialty hardcoding. GI is **content only**.

## Smoke
`python scripts/smoke_ckp_phases.py` — Phase 1 section.

## Remaining for later knowledge work
- Author real guideline packs from curated society documents (not PDF dump)
- Richer branching criteria entities
- Multi-release promotion workflow UI
