# PHASE2_NOTES — Clinical Reasoning Engine

## Status
**Complete**.

## Components
- `reasoning/ebs.py` — Encounter Belief State (continuous assessment object)
- `reasoning/engine.py` — ClinicalReasoningEngine
  - Symptom intake (synonym/code/label resolve)
  - Hypothesis generation from `suggests` edges
  - Finding updates with epistemic edge scoring
  - Section question planning from `priority_section_for` / `contains_question`
  - Red flags / pathway activation
  - Exam priorities, Ix & management recommendations
  - Differential ranking + stopping criteria
  - Narrative draft (template from EBS, not invented medicine)
  - Explainability log on every major step

## Contract
CRE consumes **published KG snapshot only**. No medical constants in code beyond strength ordinals for edge labels.

## Session persistence
`cre_session.ebs_json` pinned to `release_id`.

## Smoke
Covered in `scripts/smoke_ckp_phases.py` (intake → answer → exam → Ix → narrative).
