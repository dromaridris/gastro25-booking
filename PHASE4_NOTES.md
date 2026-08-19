# PHASE4_NOTES — Documentation & Clinical Records

## Status
**Complete**.

## Principle
Documents **consume EBS only** — no independent clinical reasoning.

## Document types implemented
`hpi`, `chief_complaint`, `relevant_pmh`, `medications`, `allergies`, `exam_notes`, `ix_summary`, `assessment_narrative`, `plan_narrative`, `soap`, `admission`, `progress`, `procedure`, `consultation`, `discharge_summary`, `referral_letter`, `follow_up_note`, `patient_journey`

## Features
- Auto draft from EBS
- Manual edit → new version
- Version history (`ckp_document_version`)
- Audit trail (`ckp_document_audit`)
- Regen after EBS changes (fingerprint)
- Structured JSON + narrative body sync
- Physician finalize (`status=final`)

## Entry points
- `/clinical-encounter/<session_id>/documents`
- `/ckp/documents/<id>`

## Smoke
18 types generated + edit/finalize in smoke script.
