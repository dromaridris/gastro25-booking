# PHASE3_NOTES — Clinical Workflow Integration

## Status
**Complete**.

## Five channels only
History → Examination → Investigations → Summary → Plan

Assessment is **not** a page; it is continuous EBS (sidebar differential + stopping + explainability).

## Encounter Controller
`clinical_knowledge_platform/workflow/controller.py`
- Sole mutation path for encounter state
- Methods: intake, answer_question, record_exam, order_investigation, record_result, summary/plan edits, regen_narrative, set_channel
- Every mutation persists EBS (autosave-compatible)

## UI
- `/clinical-encounter/` — home + start
- `/clinical-encounter/<id>?channel=…` — workspace
- Autosave JSON: `POST /clinical-encounter/<id>/autosave`
- Explainability panel on every channel
- **No** “Run AI” buttons
- Links out to Documents / CDS / Longitudinal ingest

## Diagram (logical)

```
Patient channel inputs
        │
        ▼
 EncounterController
        │
        ├─► ClinicalReasoningEngine (KG release)
        │         │
        │         ▼
        └──── EBS (persisted) ──► Summary / Plan / Docs / CDS / Longitudinal
```

## Validation
Smoke Phase 3 passed (5-channel session + narrative + plan edits).

## Remaining for Phase 4 (done separately)
Documentation module consumes EBS drafts — see PHASE4_NOTES.md.
