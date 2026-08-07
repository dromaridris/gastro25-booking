# UNIFIED_ENCOUNTER_NOTES

## Goal
Ward **Clinical Workflow** is the only physician surface. Canonical structured history / CI History Engine capabilities are merged into that path — not a competing CI history app.

Specialty-agnostic workflow; GI is the first domain pack via knowledge/seeds only.

**Decision-based interview** (not chatbot): see [DECISION_BASED_HISTORY.md](DECISION_BASED_HISTORY.md).

## Modes
| Label | Code | Entry |
|-------|------|-------|
| **New Diagnostic Encounter** | `diagnostic` | Undiagnosed → diagnosis |
| **Known Disease Follow-up / New Problem** | `known_disease` | Known disease(s) + current clinical problem |

## Stages (diagnostic)
1. **Chief complaints** — multi-select catalogue
2. **Characterization** — per complaint in turn: ODPARA (+ SOCRATES if pain) from `CHARACTERIZATION_BANKS` seeds — choice / multi_choice / boolean / numeric / date; free text only via Other (specify)
3. **Initial reasoning** — differential with confidence (CKP CRE when available, else enriched CDS + `gi_diagnosis_rule` priors); never empty after characterization
4. **Discriminating questions** — info-gain / exclusion-oriented structured widgets; differential updates each answer
5. **History summary** — existing `generate_history_note` narrative (style unchanged)
6. **Examination** — system checklists + “Other findings”
7. **Investigations** — suggested tests as checklists
8. **Plan** — existing plan/approval path

Known-disease mode inserts **Known disease(s)** → **Current clinical problem** before characterization, then the same later stages.

## Key files
| Path | Role |
|------|------|
| `gi_platform/unified_encounter/` | State machine, characterization, discrimination, differential enrichment, exam/Ix |
| `gi_platform/unified_encounter/seeds.py` | Known diseases, current problems, characterization banks, diagnosis priors, exam shells |
| `templates/gi/_decision_question.html` | Structured answer widgets |
| `gi_routes/clinical.py` | `ue_*` POST actions on `/ward/patient/<id>/clinical` |
| `templates/gi/clinical_workflow.html` | Staged UI |
| `gi_history_session.encounter_state_json` | Persisted mode/stage/checklists |
| `DECISION_BASED_HISTORY.md` | Decision-interview contract |

## Architecture rules
- Workflow UI does **not** invent diagnoses — CRE / CDS / diagnosis-rule knowledge does
- No GI hardcoding in engine logic; GI examples live in seeds / catalogue / CKP demo KB
- Competing CI “Structured interview” CTA removed from the main workflow path
- “Why this question?” coaching retained on characterization and discriminating questions
- Narrative generator unchanged in prose style
- Engine never defaults to free-text when structured options exist

## How to test (UI)
1. Open a ward patient → **Open clinical workflow**
2. Choose **New Diagnostic Encounter**
3. Multi-select complaints (e.g. Abdominal pain + Vomiting) → Start characterization
4. Answer ODPARA / SOCRATES structured widgets for each complaint in turn (radios, checkboxes, numeric/date as offered)
5. Confirm **Initial differential** is populated → continue
6. Answer discriminating questions; watch differential update
7. **Generate History narrative** → Examination checklist → Investigation checklist → Summary/Plan

Known-disease path:
1. Choose **Known Disease Follow-up / New Problem**
2. Select e.g. Cirrhosis → Current problem Hematemesis (+ Ascites)
3. Characterize → differential → same later stages

## Smoke
```bash
python test_unified_encounter_smoke.py
```
