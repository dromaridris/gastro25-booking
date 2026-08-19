# PHASE7_NOTES — Research & Learning Platform

## Status
**Complete** (independent UX; reads clinical/longitudinal data).

## Features
- Disease registries + versioning
- Cohort builder
- Variable extraction from longitudinal memory
- Study designer (inclusion/exclusion/outcomes in design_json)
- Outcome tracking fields on members
- Survival analysis **support table** (time/event/censored) — not a full stats package
- Data quality / missing data analysis
- Research dashboard
- De-identified export + audit logging
- Registry/dataset export records

## Entry points
- `/ckp/research/`
- `/ckp/research/registry/<id>`
- `/ckp/research/cohort/<id>`

## Honest limits
Not a replacement for R/SAS/SPSS. Provides governed extraction, de-id, quality, and export for external analysis / AI datasets.
