# History symptom model (Bates-aligned)

## Rule (applies to EVERY system)

**Chief complaint = patient symptom.** Never put a syndrome or diagnosis in the complaint picker.

The bleeding examples below illustrate the *logic* — the same logic applies to abdomen, chest, urine, neuro, etc.

| Not a chief complaint | Symptom complaints / where it lives |
|----------------------|-------------------------------------|
| UGIB / upper GI bleed | `CC_hematemesis`, `CC_melena`, sometimes `CC_hematochezia` |
| LGIB / lower GI bleed | `CC_hematochezia` (± melena) |
| GERD / reflux disease | `CC_heartburn` (+ regurgitation as synonym/associated) |
| Ascites / portal hypertension | `CC_abdominal_distention` (+ exam) |
| Cholecystitis / pancreatitis | `CC_abdominal_pain` (character/location questions) |
| Peptic ulcer disease | pain/bleed **symptoms** first (`CC_abdominal_pain`, `CC_hematemesis`, …) |
| Bowel obstruction | `CC_vomiting` / `CC_abdominal_distention` / `CC_abdominal_pain` + obstipation red flags |
| UTI / pyelonephritis | `CC_dysuria`, `CC_flank_pain`, `CC_hematuria`, `CC_fever` |
| Bladder cancer | never a CC — may follow `CC_hematuria` work-up |
| Heart failure | `CC_dyspnea`, `CC_edema`, plus orthopnea/PND questions — not `CC_heart_failure` |
| Asthma / COPD | `CC_cough`, `CC_dyspnea`, `CC_wheeze` questions |
| Stroke / seizure | neuro **symptoms** (`CC_syncope`, `CC_dizziness`, deficit red flags) — not disease CCs |
| IBS / IBD as labels | bowel **symptoms** (`CC_diarrhea`, `CC_constipation`, incontinence, blood) |
| Depression / anemia as visit label | `CC_fatigue`, `CC_weight_loss`, mood associated Qs |

## How the user's long inventory was mapped

1. **CC packs** — primary complaints that deserve their own Bates-style template (see `packs/complaints/_index.json`).
2. **synonyms[]** — near-duplicates of a CC (e.g. coffee-ground vomiting → hematemesis; rectal bleeding → hematochezia; ascites word → abdominal_distention).
3. **Associated / red-flag questions** — important but usually not a standalone visit reason (tenesmus, steatorrhea, mucus/pus, early satiety, orthopnea, PND, claudication, etc.).
4. **Deferred as own CC** — rare isolated ENT/eye/derm/psych items stay as associated text questions for now (`Q000180`–`Q000183`, `Q000181`, `Q000182`) rather than dozens of thin packs. Promote later if clinics need them.

## Bates sources

- Ch.4 constitutional: fatigue, fever/chills/night sweats, weight change, pain
- Ch.8–9 thorax/CV: chest pain, dyspnea/orthopnea/PND, cough, wheeze, palpitations, edema, syncope
- Ch.11 abdomen: GI + urinary concerning symptoms (pain, heartburn, nausea/vomiting/blood, anorexia/early satiety, dysphagia/odynophagia, bowel change, diarrhea, constipation, jaundice, dysuria, hematuria, flank pain, …)

## Drop-in deploy

Replace the whole `clinical_knowledge/` folder (or set `CLINICAL_KNOWLEDGE_ROOT`), then clear CI knowledge cache / restart the app.

See also: `SYMPTOM_INVENTORY_MAP.md` for the full user-list → CC / synonym / associated-Q mapping.
