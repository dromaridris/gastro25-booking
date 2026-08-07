# Symptom inventory → ontology mapping

Source: user list + Bates Common or Concerning Symptoms (esp. Ch.4, 8–9, 11).

## Became CC packs (33)

| CC | Covers (examples) |
|----|-------------------|
| `CC_abdominal_pain` | belly/epigastric/colicky pain; biliary/pancreatic patterns via questions |
| `CC_abdominal_distention` | bloating, swelling, ascites-as-word, mass sensation |
| `CC_heartburn` | acid regurgitation synonym |
| `CC_dysphagia` | odynophagia/globus via questions |
| `CC_vomiting` | nausea; bilious/feculent via vomitus character Q |
| `CC_hematemesis` | coffee-ground vomiting |
| `CC_melena` | black tarry stools |
| `CC_hematochezia` | rectal bleeding, blood in stool |
| `CC_diarrhea` / `CC_constipation` | change in bowel habits (directional) |
| `CC_anorexia` | loss of appetite, early satiety, postprandial fullness |
| `CC_food_intolerance` | meal-triggered symptom pattern |
| `CC_anal_pain` | anal itch, discharge, prolapse/swelling, painful defecation |
| `CC_fecal_incontinence` | stool leakage |
| `CC_jaundice` | yellowing |
| `CC_pruritus` | itching (incl. cholestatic pathway later) |
| `CC_flank_pain` | loin/side pain |
| `CC_dysuria` | frequency, urgency, hesitancy, weak stream, retention sensation |
| `CC_hematuria` | blood in urine |
| `CC_weight_loss` / `CC_weight_gain` | Bates weight change |
| `CC_fever` | chills, night sweats as synonyms/associated |
| `CC_fatigue` | malaise/low energy; clarify vs true weakness |
| `CC_chest_pain` | pleuritic features via Q |
| `CC_dyspnea` | orthopnea, PND via Q |
| `CC_cough` | sputum |
| `CC_hemoptysis` | coughing blood (≠ hematemesis) |
| `CC_palpitations` | racing/fluttering heart |
| `CC_edema` | leg/ankle swelling |
| `CC_syncope` | fainting, LOC |
| `CC_dizziness` | vertigo vs lightheadedness via Q |
| `CC_headache` | head pain |
| `CC_back_pain` | back/neck pain entry |

## Became synonyms (not separate CCs)

Coffee-ground vomiting → hematemesis; BRBPR/blood in stool → hematochezia; ascites (patient word) → abdominal_distention; GERD/reflux disease words → heartburn; orthopnea/PND words → dyspnea; chills/night sweats → fever; LOC/blackout → syncope; etc. (see each template `synonyms[]`).

## Became associated / red-flag questions

Tenesmus, steatorrhea, mucus/pus, straining, incomplete evacuation, belching, flatulence, hiccups, borborygmi, early satiety, obstipation (failure to pass stool/flatus), claudication, cyanosis/cold extremities, snoring/sleep apnea clues, polyuria/polydipsia, easy bruising/bleeding, ENT/eye/skin/mood screens (`Q000121`–`Q000186`).

## Deferred as thin standalone CCs

Isolated ENT (hearing loss, tinnitus, sore throat…), eye (photophobia, floaters…), detailed MSK/neuro deficit lists, and most pure psych items — captured as associated text questions for ROS depth, not 80 extra empty packs. Promote when a clinic pathway needs them.
