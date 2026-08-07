"""Chronic diarrhoea intelligence bundle — exemplar differential-driven interview.

Configuration data consumed by seed; engines read from DB after seeding.
Future: same structure loaded from Knowledge Library documents.
"""

import json

# Additional diagnoses for chronic diarrhoea differential
DIARRHEA_DIAGNOSES = [
    ("dx.celiac_disease", "Celiac disease", "gi", "kl.celiac.overview"),
    ("dx.microscopic_colitis", "Microscopic colitis", "gi", "kl.microscopic_colitis"),
    ("dx.chronic_infection", "Chronic gastrointestinal infection", "gi", "kl.chronic_gi_infection"),
    ("dx.pancreatic_insufficiency", "Exocrine pancreatic insufficiency", "gi", "kl.pancreatic_insufficiency"),
    ("dx.bile_acid_diarrhea", "Bile acid malabsorption", "gi", "kl.bile_acid_diarrhea"),
    ("dx.endocrine_diarrhea", "Endocrine cause of diarrhoea", "gi", "kl.endocrine_diarrhea"),
    ("dx.drug_induced_diarrhea", "Drug-induced diarrhoea", "gi", "kl.drug_induced_diarrhea"),
]

# (code, prompt, section, answer_type, choices, is_exclusion, help, purpose)
DIARRHEA_QUESTIONS = [
    ("q.diar.duration", "Symptom duration", "presenting", "choice",
     ["acute_less_than_2_weeks", "persistent_2_to_4_weeks", "chronic_more_than_4_weeks"], False,
     "Chronic diarrhoea warrants structural and malabsorptive workup", "contextual"),
    ("q.diar.chronic_watery", "Chronic watery diarrhoea without blood?", "presenting", "boolean", None, False,
     None, "supports"),
    ("q.diar.steatorrhea", "Greasy, bulky, foul-smelling stools (steatorrhoea)?", "presenting", "boolean", None, False,
     "Suggests malabsorption or pancreatic insufficiency", "supports"),
    ("q.diar.post_chole", "History of cholecystectomy?", "presenting", "boolean", None, False,
     "Risk factor for bile acid diarrhoea", "risk_factor"),
    ("q.diar.recent_antibiotics", "Recent antibiotic course?", "presenting", "boolean", None, False,
     "Consider C. difficile and chronic dysbiosis", "risk_factor"),
    ("q.diar.metformin", "Taking metformin?", "drugs", "boolean", None, False,
     "Common cause of drug-induced diarrhoea", "risk_factor"),
    ("q.diar.gluten", "Symptoms improve off gluten?", "presenting", "boolean", None, False,
     "Celiac screen if suspected", "supports"),
    ("q.diar.iron_deficiency", "Known iron deficiency anaemia?", "exclusion", "boolean", None, True,
     "Celiac disease association", "supports"),
    ("q.diar.age_over_50", "Age 50 years or older?", "risk", "boolean", None, False,
     "Microscopic colitis more common in older adults", "risk_factor"),
    ("q.diar.thyroid_symptoms", "Hyperthyroid symptoms (palpitations, weight loss, heat intolerance)?", "presenting", "boolean", None, False,
     None, "supports"),
    ("q.diar.travel_endemic", "Travel to endemic area or untreated water exposure?", "presenting", "boolean", None, False,
     "Chronic parasitic infection", "risk_factor"),
    ("q.diar.abdominal_pain_severe", "Severe persistent abdominal pain?", "alarm", "boolean", None, True,
     "Red flag — exclude serious pathology", "alarm"),
    ("q.diar.anemia", "Known anaemia?", "exclusion", "boolean", None, True,
     "Alarm feature — organic disease", "alarm"),
]

DIARRHEA_PRIORS = [
    ("hist.diarrhea", "dx.ibs", 1.0),
    ("hist.diarrhea", "dx.ibd", 1.0),
    ("hist.diarrhea", "dx.celiac_disease", 0.8),
    ("hist.diarrhea", "dx.microscopic_colitis", 0.7),
    ("hist.diarrhea", "dx.chronic_infection", 0.6),
    ("hist.diarrhea", "dx.pancreatic_insufficiency", 0.5),
    ("hist.diarrhea", "dx.bile_acid_diarrhea", 0.5),
    ("hist.diarrhea", "dx.endocrine_diarrhea", 0.4),
    ("hist.diarrhea", "dx.drug_induced_diarrhea", 0.6),
]

DIARRHEA_WEIGHT_RULES = [
    ("hist.diarrhea", "q.diar.nocturnal", "yes", "dx.ibd", 3.0),
    ("hist.diarrhea", "q.diar.nocturnal", "no", "dx.ibs", 2.0),
    ("hist.diarrhea", "q.diar.blood", "yes", "dx.ibd", 3.5),
    ("hist.diarrhea", "q.diar.blood", "no", "dx.ibs", 0.5),
    ("hist.diarrhea", "q.diar.weight_loss", "yes", "dx.ibd", 2.5),
    ("hist.diarrhea", "q.diar.weight_loss", "yes", "dx.celiac_disease", 1.5),
    ("hist.diarrhea", "q.diar.fever", "yes", "dx.ibd", 2.0),
    ("hist.diarrhea", "q.diar.fever", "yes", "dx.chronic_infection", 2.0),
    ("hist.diarrhea", "q.diar.family_ibd", "yes", "dx.ibd", 2.0),
    ("hist.diarrhea", "q.diar.steatorrhea", "yes", "dx.pancreatic_insufficiency", 3.5),
    ("hist.diarrhea", "q.diar.steatorrhea", "yes", "dx.celiac_disease", 1.5),
    ("hist.diarrhea", "q.diar.post_chole", "yes", "dx.bile_acid_diarrhea", 3.0),
    ("hist.diarrhea", "q.diar.recent_antibiotics", "yes", "dx.chronic_infection", 2.5),
    ("hist.diarrhea", "q.diar.metformin", "yes", "dx.drug_induced_diarrhea", 3.0),
    ("hist.diarrhea", "q.diar.gluten", "yes", "dx.celiac_disease", 3.0),
    ("hist.diarrhea", "q.diar.iron_deficiency", "yes", "dx.celiac_disease", 2.5),
    ("hist.diarrhea", "q.diar.age_over_50", "yes", "dx.microscopic_colitis", 2.0),
    ("hist.diarrhea", "q.diar.thyroid_symptoms", "yes", "dx.endocrine_diarrhea", 3.0),
    ("hist.diarrhea", "q.diar.travel_endemic", "yes", "dx.chronic_infection", 2.5),
    ("hist.diarrhea", "q.diar.anemia", "yes", "dx.ibd", 2.0),
    ("hist.diarrhea", "q.diar.anemia", "yes", "dx.celiac_disease", 1.5),
    ("hist.diarrhea", "q.diar.duration", "chronic_more_than_4_weeks", "dx.ibs", -0.5),
]

DIARRHEA_INVESTIGATIONS_BASELINE = [
    ("hist.diarrhea", "lab.cbc", "CBC — anaemia and inflammation"),
    ("hist.diarrhea", "lab.crp", "CRP / inflammatory markers"),
    ("hist.diarrhea", "lab.calprotectin", "Faecal calprotectin — IBD vs functional"),
    ("hist.diarrhea", "lab.ttiga", "Coeliac serology (tTG-IgA)"),
    ("hist.diarrhea", "lab.tsh", "TSH — exclude hyperthyroidism"),
]

DIARRHEA_INVESTIGATIONS_ADVANCED = [
    ("dx.ibd", "proc.colonoscopy", "Colonoscopy with biopsies if calprotectin elevated or alarm features"),
    ("dx.celiac_disease", "proc.egd", "Duodenal biopsies if serology positive"),
    ("dx.microscopic_colitis", "proc.colonoscopy", "Colonoscopy — biopsies required even if macroscopically normal"),
    ("dx.pancreatic_insufficiency", "lab.fecal_elastase", "Faecal elastase — pancreatic insufficiency"),
    ("dx.bile_acid_diarrhea", "lab.sehcats", "SeHCAT or therapeutic trial of bile acid sequestrant"),
    ("dx.chronic_infection", "lab.stool_ova_parasites", "Stool O&P, culture, C. difficile toxin"),
    ("dx.drug_induced_diarrhea", "lab.none", "Review medication list — trial off suspected agent"),
]

# Question rules: (question_code, sort, purpose, priority, parent_q, parent_a, activation_json, targets_json, rationale)
DIARRHEA_RULES = [
    ("q.diar.duration", 10, "contextual", 2.0, None, None, None, None, "Establishes acute vs chronic framework"),
    ("q.diar.frequency", 20, "contextual", 1.0, None, None, None, None, None),
    ("q.diar.blood", 30, "alarm", 2.5, None, None, None, json.dumps(["dx.ibd"]), "Blood excludes pure functional diagnosis"),
    ("q.diar.nocturnal", 40, "excludes", 3.0, None, None, None, json.dumps(["dx.ibs", "dx.ibd"]), "Nocturnal symptoms argue against IBS"),
    ("q.diar.weight_loss", 50, "alarm", 2.5, None, None, None, json.dumps(["dx.ibd", "dx.celiac_disease"]), None),
    ("q.diar.fever", 60, "alarm", 2.0, None, None, None, json.dumps(["dx.ibd", "dx.chronic_infection"]), None),
    ("q.diar.family_ibd", 70, "risk_factor", 1.5, None, None, None, json.dumps(["dx.ibd"]), None),
    ("q.diar.chronic_watery", 80, "supports", 1.5,
     "q.diar.duration", "chronic_more_than_4_weeks", None, json.dumps(["dx.ibs", "dx.microscopic_colitis"]), None),
    ("q.diar.steatorrhea", 90, "supports", 2.5,
     "q.diar.duration", "chronic_more_than_4_weeks", None, json.dumps(["dx.pancreatic_insufficiency", "dx.celiac_disease"]), None),
    ("q.diar.post_chole", 100, "risk_factor", 2.0,
     "q.diar.duration", "chronic_more_than_4_weeks", None, json.dumps(["dx.bile_acid_diarrhea"]), None),
    ("q.diar.metformin", 110, "risk_factor", 2.0, None, None, None, json.dumps(["dx.drug_induced_diarrhea"]), None),
    ("q.diar.recent_antibiotics", 120, "risk_factor", 2.0, None, None, None, json.dumps(["dx.chronic_infection"]), None),
    ("q.diar.gluten", 130, "supports", 2.0,
     "q.diar.duration", "chronic_more_than_4_weeks", None, json.dumps(["dx.celiac_disease"]), None),
    ("q.diar.iron_deficiency", 140, "supports", 2.0, None, None, None, json.dumps(["dx.celiac_disease"]), None),
    ("q.diar.age_over_50", 150, "risk_factor", 1.5,
     "q.diar.duration", "chronic_more_than_4_weeks", None, json.dumps(["dx.microscopic_colitis"]), None),
    ("q.diar.thyroid_symptoms", 160, "supports", 2.0, None, None, None, json.dumps(["dx.endocrine_diarrhea"]), None),
    ("q.diar.travel_endemic", 170, "risk_factor", 1.5, None, None, None, json.dumps(["dx.chronic_infection"]), None),
    ("q.diar.anemia", 180, "alarm", 2.5, None, None, None, json.dumps(["dx.ibd", "dx.celiac_disease"]), None),
    ("q.diar.abdominal_pain_severe", 190, "alarm", 2.0, None, None, None, None, None),
    ("q.common.pmh", 200, "contextual", 0.5, None, None, None, None, None),
    ("q.common.drugs", 210, "contextual", 1.0, None, None, None, None, None),
    ("q.common.allergy", 220, "contextual", 0.3, None, None, None, None, None),
    ("q.common.family", 230, "contextual", 0.5, None, None, None, None, None),
]

DIARRHEA_MANAGEMENT = [
    (
        "dx.celiac_disease",
        "Celiac disease — immune-mediated enteropathy triggered by gluten.",
        "Strict lifelong gluten-free diet; dietitian referral; screen for nutritional deficiencies; consider DEXA.",
        "Marsh classification on histology.",
        "Refractory symptoms, weight loss, alarm features.",
        "Gastroenterology follow-up; repeat serology if adherence uncertain.",
        "kl.celiac.overview",
    ),
    (
        "dx.microscopic_colitis",
        "Microscopic colitis — chronic watery diarrhoea with macroscopically normal colon.",
        "Confirm with colonic biopsies; budesonide first line; assess for bile acid diarrhoea overlap.",
        "No single activity score — track stool frequency.",
        "Weight loss, blood in stool — reconsider IBD.",
        "Repeat colonoscopy if treatment failure.",
        "kl.microscopic_colitis",
    ),
]

DIARRHEA_BUNDLE = {
    "complaint_code": "hist.diarrhea",
    "diagnoses": DIARRHEA_DIAGNOSES,
    "questions": DIARRHEA_QUESTIONS,
    "rules": DIARRHEA_RULES,
    "priors": DIARRHEA_PRIORS,
    "weight_rules": DIARRHEA_WEIGHT_RULES,
    "baseline_investigations": DIARRHEA_INVESTIGATIONS_BASELINE,
    "advanced_investigations": DIARRHEA_INVESTIGATIONS_ADVANCED,
    "management": DIARRHEA_MANAGEMENT,
}
