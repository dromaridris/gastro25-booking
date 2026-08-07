# PHASE5_NOTES — Clinical Decision Support (CDS)

## Status
**Complete** (advisory layer).

## Principle
Advisory only. Specialty-agnostic code. Recommendations derived from EBS + KG edges — **never invent medicine**.

## Alert kinds
- differential_explanation
- investigation_recommendation
- ix_interpretation_hook
- guideline_recommendation
- management_recommendation
- drug_safety / drug_interaction / dose_reminder
- preventive_reminder
- clinical_score
- order_set
- care_pathway
- red_flag
- escalation

## Every recommendation carries
supporting evidence, contradictory evidence, guideline source (when bound), confidence, explanation.

## Entry points
- `/clinical-encounter/<session_id>/cds`
- Refresh: `POST .../cds/refresh`

## Honest limits
Drug interaction/contraindication alerts appear only when KG has those edges. Demo seed has limited drug-safety graph; production needs curated drug/guideline packs.
