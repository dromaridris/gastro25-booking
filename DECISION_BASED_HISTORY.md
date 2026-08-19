# DECISION_BASED_HISTORY.md

## Intent
Ward **Clinical Workflow** history is a **decision-based clinical interview**, not a chatbot.
Physicians click structured controls; free text is reserved for **Other (specify)** (and exam “other findings”).

## Input preference order
1. Single choice (radio; dropdown if >8 options)
2. Multi choice (checkboxes)
3. Yes / No / Unknown (boolean)
4. Numeric
5. Date
6. Free text — **only** behind Other (specify)

The engine **never defaults to free-text** when a structured alternative exists (seeds, catalogue metadata, or KB patches).

## Flow (diagnostic)
1. Multi-select chief complaints (catalogue)
2. **Per complaint, in turn:** ODPARA → if pain-like, SOCRATES → store structured answers → next complaint
3. Initial differential (CKP / CDS / diagnosis-rule priors — never empty when complaints set)
4. Discriminating MCQ / boolean / numeric (information gain); differential updates each answer
5. Generate History narrative (existing prose style)
6. Examination checklists → Investigations → Plan

Known-disease mode: Known disease(s) → Current clinical problem(s) → same characterization onward.

## Where options live (not engine hardcoding)
| Source | Role |
|--------|------|
| `gi_platform/unified_encounter/seeds.py` → `CHARACTERIZATION_BANKS`, choice catalogues, `KB_STRUCTURED_PATCHES` | ODPARA/SOCRATES banks + KB id patches |
| `clinical_knowledge/questions/library.json` | Question entities (patched for characterization items) |
| Trained / catalogue questions | Complaint-specific MCQs when already structured |
| `DISEASE_CONTEXT_QUESTIONS` | Known-disease follow-up MCQs |

## UI widgets
`templates/gi/_decision_question.html` — radio, checkbox, yes/no, dropdown, number, date, Other-specify reveal.
Used from `templates/gi/clinical_workflow.html` for characterization and discriminating stages.
“Why this question?” coaching retained.

## Verify
```bash
python test_unified_encounter_smoke.py
```
Covers: no free-text in characterization batch; multi-complaint sequential ODPARA; discriminating structured; Other-specify answer assembly; differential after characterization; Generate History; HTTP mode select.

UI path: Ward patient → Open clinical workflow → New Diagnostic Encounter → select complaints → answer structured characterization → differential → discriminating → Generate History.
