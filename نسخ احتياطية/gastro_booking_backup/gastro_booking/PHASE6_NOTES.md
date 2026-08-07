# PHASE6_NOTES — Longitudinal Clinical Intelligence

## Status
**Complete**.

## Capabilities
- Longitudinal Clinical Memory per `patient_key`
- Timelines: disease / procedure / medication / investigation / symptom
- Progression & confidence changes
- Treatment-response hooks (via plan/follow-up fields)
- Recurrence detection across encounters
- Patterns & trends
- Clinical delta vs prior encounter (`ckp_encounter_compare`)
- Baseline (first encounter)
- Registry membership hints
- Risk evolution (pathways / red flags)
- Follow-up intelligence from EBS

## Entry points
- Ingest: `POST /clinical-encounter/<id>/longitudinal/ingest`
- `/ckp/longitudinal/`
- `/ckp/longitudinal/<patient_key>`

## Scope
Multi-year / multi-specialty ready at data model level (patient_key + event kinds). Demo uses encounter patient labels as keys.
