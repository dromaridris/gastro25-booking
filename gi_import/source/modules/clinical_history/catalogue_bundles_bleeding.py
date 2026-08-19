"""Upper and lower GI bleeding intelligence bundles."""

import json

from app.modules.clinical_history.catalogue_bundle_common import common_context_rules, targets

UGIB_DIAGNOSES = [
    ("dx.gastric_erosions", "Gastric erosions / gastritis bleed", "gi", "kl.ugib.gastric_erosions"),
    ("dx.dieulafoy", "Dieulafoy lesion", "gi", "kl.ugib.dieulafoy"),
]

UGIB_QUESTIONS = [
    ("q.ugib.hematemesis", "Has the patient vomited blood (hematemesis)?", "presenting", "boolean", None, False,
     "Distinguishes upper from isolated lower source when melena absent", "supports"),
    ("q.ugib.coffee_ground", "Coffee-ground vomitus?", "presenting", "boolean", None, False,
     "Suggests altered blood from upper GI source", "supports"),
    ("q.ugib.melena", "Black tarry stools (melena)?", "presenting", "boolean", None, False,
     "Typical of upper GI bleeding above ligament of Treitz", "supports"),
    ("q.ugib.amount", "Estimated volume of bleeding", "presenting", "choice",
     ["small", "moderate", "large", "massive"], False, "Guides resuscitation urgency", "alarm"),
    ("q.ugib.duration", "Duration of symptoms", "presenting", "choice",
     ["hours", "1-3_days", "more_than_3_days"], False, None, "contextual"),
    ("q.ugib.syncope", "Syncope or presyncope?", "alarm", "boolean", None, True,
     "Red flag — haemodynamic compromise", "alarm"),
    ("q.ugib.chest_pain", "Associated chest pain?", "alarm", "boolean", None, True,
     "Consider aortoenteric fistula or cardiac cause", "alarm"),
    ("q.ugib.previous_episodes", "Previous upper GI bleeding episodes?", "presenting", "boolean", None, False,
     "Variceal and peptic disease often recur", "risk_factor"),
    ("q.ugib.nsaids", "Recent NSAID or aspirin use?", "presenting", "boolean", None, False,
     "Major risk for peptic ulceration", "risk_factor"),
    ("q.ugib.alcohol", "Significant alcohol use?", "presenting", "boolean", None, False,
     "Risk for gastritis, varices, Mallory-Weiss", "risk_factor"),
    ("q.ugib.liver_disease", "Known chronic liver disease or cirrhosis?", "presenting", "boolean", None, False,
     "Variceal bleeding becomes leading diagnosis", "risk_factor"),
    ("q.ugib.anticoagulants", "Anticoagulants or antiplatelets?", "presenting", "boolean", None, False,
     "Bleeding severity and reversal planning", "risk_factor"),
    ("q.ugib.retching", "Forceful retching or vomiting before bleed?", "presenting", "boolean", None, False,
     "Mallory-Weiss tear pattern", "supports"),
    ("q.ugib.previous_endoscopy", "Previous upper GI endoscopy?", "presenting", "boolean", None, False,
     "Prior ulcer, varices, or malignancy", "contextual"),
    ("q.ugib.weight_loss", "Unintentional weight loss?", "exclusion", "boolean", None, True,
     "Alarm — exclude malignancy", "alarm"),
    ("q.ugib.dysphagia", "Dysphagia?", "exclusion", "boolean", None, True,
     "Alarm — structural oesophageal or gastric disease", "alarm"),
    ("q.ugib.anaemia_known", "Known anaemia before this episode?", "exclusion", "boolean", None, True,
     "Chronic blood loss — consider malignancy", "alarm"),
]

UGIB_PRIORS = [
    ("hist.upper_gi_bleeding", "dx.peptic_ulcer_bleed", 1.5),
    ("hist.upper_gi_bleeding", "dx.variceal_bleed", 1.0),
    ("hist.upper_gi_bleeding", "dx.mallory_weiss", 0.6),
    ("hist.upper_gi_bleeding", "dx.gastric_malignancy", 0.5),
    ("hist.upper_gi_bleeding", "dx.gastric_erosions", 0.8),
    ("hist.upper_gi_bleeding", "dx.dieulafoy", 0.3),
]

UGIB_WEIGHT_RULES = [
    ("hist.upper_gi_bleeding", "q.ugib.melena", "yes", "dx.peptic_ulcer_bleed", 2.0),
    ("hist.upper_gi_bleeding", "q.ugib.hematemesis", "yes", "dx.peptic_ulcer_bleed", 2.0),
    ("hist.upper_gi_bleeding", "q.ugib.nsaids", "yes", "dx.peptic_ulcer_bleed", 2.5),
    ("hist.upper_gi_bleeding", "q.ugib.liver_disease", "yes", "dx.variceal_bleed", 3.5),
    ("hist.upper_gi_bleeding", "q.ugib.alcohol", "yes", "dx.variceal_bleed", 1.5),
    ("hist.upper_gi_bleeding", "q.ugib.alcohol", "yes", "dx.mallory_weiss", 1.5),
    ("hist.upper_gi_bleeding", "q.ugib.coffee_ground", "yes", "dx.peptic_ulcer_bleed", 1.0),
    ("hist.upper_gi_bleeding", "q.ugib.retching", "yes", "dx.mallory_weiss", 3.0),
    ("hist.upper_gi_bleeding", "q.ugib.weight_loss", "yes", "dx.gastric_malignancy", 2.5),
    ("hist.upper_gi_bleeding", "q.ugib.dysphagia", "yes", "dx.gastric_malignancy", 2.0),
    ("hist.upper_gi_bleeding", "q.ugib.amount", "massive", "dx.variceal_bleed", 1.5),
    ("hist.upper_gi_bleeding", "q.ugib.previous_episodes", "yes", "dx.variceal_bleed", 1.5),
    ("hist.upper_gi_bleeding", "q.ugib.anticoagulants", "yes", "dx.peptic_ulcer_bleed", 1.0),
]

UGIB_RULES = [
    ("q.ugib.hematemesis", 10, "supports", 3.0, None, None, None, targets("dx.peptic_ulcer_bleed", "dx.variceal_bleed"), None),
    ("q.ugib.melena", 20, "supports", 3.0, None, None, None, targets("dx.peptic_ulcer_bleed"), None),
    ("q.ugib.amount", 30, "alarm", 3.5, None, None, None, None, "Volume drives resuscitation and timing of endoscopy"),
    ("q.ugib.syncope", 40, "alarm", 4.0, None, None, None, None, "Unstable bleeding until proven otherwise"),
    ("q.ugib.coffee_ground", 50, "supports", 2.0, None, None, None, targets("dx.peptic_ulcer_bleed"), None),
    ("q.ugib.duration", 60, "contextual", 1.0, None, None, None, None, None),
    ("q.ugib.nsaids", 70, "risk_factor", 2.5, None, None, None, targets("dx.peptic_ulcer_bleed"), None),
    ("q.ugib.liver_disease", 80, "risk_factor", 3.5, None, None, None, targets("dx.variceal_bleed"), None),
    ("q.ugib.alcohol", 90, "risk_factor", 2.0, None, None, None, targets("dx.variceal_bleed", "dx.mallory_weiss"), None),
    ("q.ugib.retching", 100, "supports", 2.5, None, None, None, targets("dx.mallory_weiss"), None),
    ("q.ugib.anticoagulants", 110, "risk_factor", 2.0, None, None, None, None, None),
    ("q.ugib.previous_episodes", 120, "risk_factor", 1.5, None, None, None, targets("dx.variceal_bleed", "dx.peptic_ulcer_bleed"), None),
    ("q.ugib.previous_endoscopy", 130, "contextual", 1.0, None, None, None, None, None),
    ("q.ugib.weight_loss", 140, "alarm", 2.5, None, None, None, targets("dx.gastric_malignancy"), None),
    ("q.ugib.dysphagia", 150, "alarm", 2.0, None, None, None, targets("dx.gastric_malignancy"), None),
    ("q.ugib.anaemia_known", 160, "alarm", 2.0, None, None, None, targets("dx.gastric_malignancy"), None),
    ("q.ugib.chest_pain", 170, "alarm", 2.5, None, None, None, None, "Consider vascular catastrophe"),
] + common_context_rules(900)

UGIB_BASELINE = [
    ("hist.upper_gi_bleeding", "lab.cbc", "CBC — anaemia and platelets"),
    ("hist.upper_gi_bleeding", "lab.lft", "LFTs — synthetic function and chronic liver disease"),
    ("hist.upper_gi_bleeding", "lab.coagulation", "Coagulation profile"),
    ("hist.upper_gi_bleeding", "lab.urea", "Urea — upper GI bleed marker"),
    ("hist.upper_gi_bleeding", "lab.group_screen", "Blood group and cross-match"),
]

UGIB_ADVANCED = [
    ("dx.peptic_ulcer_bleed", "proc.egd", "Upper GI endoscopy for diagnosis and haemostasis"),
    ("dx.variceal_bleed", "proc.egd", "Urgent upper GI endoscopy with band ligation"),
    ("dx.variceal_bleed", "img.ct_abdomen", "CT if portal vein thrombosis or alternative source suspected"),
    ("dx.gastric_malignancy", "proc.egd", "Upper GI endoscopy with biopsies"),
    ("dx.mallory_weiss", "proc.egd", "Endoscopy to confirm mucosal tear"),
    ("dx.gastric_erosions", "proc.egd", "Endoscopy — erosive gastritis or portal hypertensive gastropathy"),
]

UGIB_MANAGEMENT = [
    (
        "dx.peptic_ulcer_bleed",
        "Acute upper GI bleeding from peptic ulceration.",
        "Resuscitate ABC; IV PPI; endoscopy within 24h (sooner if unstable); review NSAIDs and anticoagulation.",
        "Glasgow-Blatchford score; Rockall score post-endoscopy.",
        "Haemodynamic instability, syncope, active hematemesis, Hb < 8 g/dL.",
        "Repeat endoscopy if re-bleed; H. pylori test and eradicate if positive.",
        "kl.ugib.peptic_ulcer",
    ),
    (
        "dx.variceal_bleed",
        "Variceal haemorrhage in chronic liver disease.",
        "Airway protection; vasoactive drugs; antibiotics; urgent endoscopic band ligation; consider TIPS if refractory.",
        "Child-Pugh; MELD score.",
        "Encephalopathy, refractory shock, failure to achieve haemostasis.",
        "Secondary prophylaxis with beta-blocker and repeat banding.",
        "kl.ugib.variceal",
    ),
    (
        "dx.mallory_weiss",
        "Mucosal tear at gastro-oesophageal junction after retching.",
        "Usually self-limited; endoscopy if ongoing bleeding; PPI short course.",
        "No standard score — assess haemodynamic stability.",
        "Persistent haematemesis, haemodynamic instability.",
        "Discharge when stable; review alcohol and anti-platelet use.",
        "kl.ugib.mallory_weiss",
    ),
    (
        "dx.gastric_malignancy",
        "Gastric cancer presenting with bleeding.",
        "Stabilise; urgent endoscopy with biopsies; staging once diagnosis confirmed.",
        "No acute bleeding score specific — use Rockall for re-bleed risk.",
        "Obstruction, perforation, continued transfusion requirement.",
        "Multidisciplinary team referral after histological confirmation.",
        "kl.gastric_cancer.overview",
    ),
]

LGIB_DIAGNOSES = [
    ("dx.diverticular_bleed", "Diverticular bleeding", "gi", "kl.lgib.diverticular"),
    ("dx.angiodysplasia", "Angiodysplasia", "gi", "kl.lgib.angiodysplasia"),
    ("dx.hemorrhoids", "Haemorrhoids", "gi", "kl.lgib.hemorrhoids"),
    ("dx.anal_fissure", "Anal fissure", "gi", "kl.lgib.anal_fissure"),
    ("dx.ischaemic_colitis", "Ischaemic colitis", "gi", "kl.lgib.ischaemic_colitis"),
    ("dx.anorectal_malignancy", "Anorectal malignancy", "gi", "kl.lgib.anorectal_cancer"),
]

LGIB_QUESTIONS = [
    ("q.lgib.bright_red", "Bright red blood per rectum (haematochezia)?", "presenting", "boolean", None, False,
     "Suggests lower GI source; massive UGI bleed can mimic", "supports"),
    ("q.lgib.clots", "Passing blood clots?", "presenting", "boolean", None, False,
     "Clots favour colonic source", "supports"),
    ("q.lgib.amount", "Estimated bleeding volume", "presenting", "choice",
     ["streaks_on_paper", "small_volume", "moderate", "massive"], False, None, "alarm"),
    ("q.lgib.pain", "Associated abdominal pain?", "presenting", "boolean", None, False,
     "Ischaemic colitis, IBD, diverticulitis patterns", "supports"),
    ("q.lgib.diarrhea", "Associated diarrhoea?", "presenting", "boolean", None, False,
     "IBD and infectious colitis", "supports"),
    ("q.lgib.constipation", "Constipation or straining?", "presenting", "boolean", None, False,
     "Haemorrhoids and fissure", "supports"),
    ("q.lgib.age_over_50", "Age 50 years or older?", "risk", "boolean", None, False,
     "Higher pre-test probability of colorectal cancer", "risk_factor"),
    ("q.lgib.family_crc", "Family history of colorectal cancer?", "risk", "boolean", None, False,
     "Screening and cancer risk", "risk_factor"),
    ("q.lgib.weight_loss", "Unintentional weight loss?", "alarm", "boolean", None, True,
     "Alarm feature — malignancy or IBD", "alarm"),
    ("q.lgib.anemia", "Symptoms of anaemia (fatigue, dyspnoea)?", "alarm", "boolean", None, True,
     "Chronic or significant acute blood loss", "alarm"),
    ("q.lgib.nocturnal", "Bleeding or bowel symptoms waking from sleep?", "alarm", "boolean", None, True,
     "Organic disease more likely", "alarm"),
    ("q.lgib.prior_colonoscopy", "Previous colonoscopy within 10 years?", "exclusion", "boolean", None, True,
     "Recent normal colonoscopy lowers cancer probability", "excludes"),
    ("q.lgib.anticoagulant", "On anticoagulation?", "presenting", "boolean", None, False,
     "Bleeding severity and reversal", "risk_factor"),
    ("q.lgib.prior_diverticulosis", "Known diverticular disease?", "presenting", "boolean", None, False,
     "Common cause in older adults", "risk_factor"),
    ("q.lgib.urgency", "Urgency or tenesmus?", "presenting", "boolean", None, False,
     "Distal colonic or rectal pathology", "supports"),
]

LGIB_PRIORS = [
    ("hist.lower_gi_bleeding", "dx.diverticular_bleed", 1.2),
    ("hist.lower_gi_bleeding", "dx.colorectal_cancer", 0.8),
    ("hist.lower_gi_bleeding", "dx.hemorrhoids", 1.0),
    ("hist.lower_gi_bleeding", "dx.anal_fissure", 0.7),
    ("hist.lower_gi_bleeding", "dx.ibd", 0.6),
    ("hist.lower_gi_bleeding", "dx.angiodysplasia", 0.5),
    ("hist.lower_gi_bleeding", "dx.ischaemic_colitis", 0.4),
    ("hist.lower_gi_bleeding", "dx.anorectal_malignancy", 0.3),
]

LGIB_WEIGHT_RULES = [
    ("hist.lower_gi_bleeding", "q.lgib.bright_red", "yes", "dx.hemorrhoids", 1.5),
    ("hist.lower_gi_bleeding", "q.lgib.bright_red", "yes", "dx.diverticular_bleed", 1.5),
    ("hist.lower_gi_bleeding", "q.lgib.constipation", "yes", "dx.hemorrhoids", 2.5),
    ("hist.lower_gi_bleeding", "q.lgib.constipation", "yes", "dx.anal_fissure", 2.0),
    ("hist.lower_gi_bleeding", "q.lgib.age_over_50", "yes", "dx.colorectal_cancer", 2.0),
    ("hist.lower_gi_bleeding", "q.lgib.age_over_50", "yes", "dx.diverticular_bleed", 1.5),
    ("hist.lower_gi_bleeding", "q.lgib.weight_loss", "yes", "dx.colorectal_cancer", 3.0),
    ("hist.lower_gi_bleeding", "q.lgib.diarrhea", "yes", "dx.ibd", 2.5),
    ("hist.lower_gi_bleeding", "q.lgib.pain", "yes", "dx.ischaemic_colitis", 2.0),
    ("hist.lower_gi_bleeding", "q.lgib.pain", "yes", "dx.ibd", 1.5),
    ("hist.lower_gi_bleeding", "q.lgib.prior_diverticulosis", "yes", "dx.diverticular_bleed", 2.5),
    ("hist.lower_gi_bleeding", "q.lgib.prior_colonoscopy", "yes", "dx.colorectal_cancer", -1.5),
    ("hist.lower_gi_bleeding", "q.lgib.nocturnal", "yes", "dx.ibd", 2.0),
    ("hist.lower_gi_bleeding", "q.lgib.family_crc", "yes", "dx.colorectal_cancer", 2.0),
    ("hist.lower_gi_bleeding", "q.lgib.amount", "massive", "dx.diverticular_bleed", 1.5),
]

LGIB_RULES = [
    ("q.lgib.bright_red", 10, "supports", 3.0, None, None, None, targets("dx.hemorrhoids", "dx.diverticular_bleed"), None),
    ("q.lgib.amount", 20, "alarm", 3.5, None, None, None, None, None),
    ("q.lgib.clots", 30, "supports", 2.0, None, None, None, targets("dx.diverticular_bleed", "dx.colorectal_cancer"), None),
    ("q.lgib.pain", 40, "supports", 2.0, None, None, None, targets("dx.ischaemic_colitis", "dx.ibd"), None),
    ("q.lgib.diarrhea", 50, "supports", 2.0, None, None, None, targets("dx.ibd"), None),
    ("q.lgib.constipation", 60, "supports", 2.0, None, None, None, targets("dx.hemorrhoids", "dx.anal_fissure"), None),
    ("q.lgib.urgency", 70, "supports", 1.5, None, None, None, targets("dx.hemorrhoids", "dx.anorectal_malignancy"), None),
    ("q.lgib.age_over_50", 80, "risk_factor", 2.0, None, None, None, targets("dx.colorectal_cancer", "dx.diverticular_bleed"), None),
    ("q.lgib.family_crc", 90, "risk_factor", 2.0, None, None, None, targets("dx.colorectal_cancer"), None),
    ("q.lgib.weight_loss", 100, "alarm", 3.0, None, None, None, targets("dx.colorectal_cancer", "dx.ibd"), None),
    ("q.lgib.anemia", 110, "alarm", 2.5, None, None, None, None, None),
    ("q.lgib.nocturnal", 120, "alarm", 2.0, None, None, None, targets("dx.ibd"), None),
    ("q.lgib.prior_colonoscopy", 130, "excludes", 2.0, None, None, None, targets("dx.colorectal_cancer"), "Recent normal scope lowers cancer probability"),
    ("q.lgib.anticoagulant", 140, "risk_factor", 1.5, None, None, None, None, None),
    ("q.lgib.prior_diverticulosis", 150, "risk_factor", 2.0, None, None, None, targets("dx.diverticular_bleed"), None),
] + common_context_rules(900)

LGIB_BASELINE = [
    ("hist.lower_gi_bleeding", "lab.cbc", "CBC — assess anaemia"),
    ("hist.lower_gi_bleeding", "lab.coagulation", "Coagulation if anticoagulated"),
    ("hist.lower_gi_bleeding", "lab.crp", "CRP if inflammatory cause suspected"),
    ("hist.lower_gi_bleeding", "lab.calprotectin", "Faecal calprotectin if IBD suspected"),
]

LGIB_ADVANCED = [
    ("dx.colorectal_cancer", "proc.colonoscopy", "Colonoscopy with biopsies"),
    ("dx.diverticular_bleed", "proc.colonoscopy", "Colonoscopy when stable — localize and treat"),
    ("dx.ibd", "proc.colonoscopy", "Ileocolonoscopy with biopsies"),
    ("dx.angiodysplasia", "proc.colonoscopy", "Colonoscopy — angioectasia therapy"),
    ("dx.ischaemic_colitis", "img.ct_abdomen", "CT angiography if acute ischaemia suspected"),
    ("dx.anorectal_malignancy", "proc.colonoscopy", "Colonoscopy and rectal examination under anaesthesia if needed"),
]

LGIB_MANAGEMENT = [
    (
        "dx.diverticular_bleed",
        "Acute lower GI bleeding from colonic diverticula.",
        "Resuscitate; colonoscopy when stable; interventional radiology or surgery if refractory.",
        "No universal score — use clinical instability and transfusion need.",
        "Haemodynamic instability, persistent bleeding despite endoscopy.",
        "Repeat colonoscopy or CT angiography if bleeding recurs.",
        "kl.lgib.diverticular",
    ),
    (
        "dx.colorectal_cancer",
        "Colorectal cancer presenting with rectal bleeding.",
        "Complete colonoscopy; staging; multidisciplinary team referral.",
        "TNM staging after histology.",
        "Obstruction, perforation, uncontrolled bleeding.",
        "Oncology and surgical follow-up per stage.",
        "kl.colorectal_cancer.overview",
    ),
    (
        "dx.hemorrhoids",
        "Haemorrhoidal bleeding — diagnosis of exclusion in young patients.",
        "Confirm with examination; treat constipation; rubber band ligation if symptomatic.",
        "No mandatory score.",
        "Anaemia, weight loss, age >50 without screening — investigate further.",
        "Colonoscopy if alarm features or inadequate response.",
        "kl.lgib.hemorrhoids",
    ),
]

UGIB_BUNDLE = {
    "complaint_code": "hist.upper_gi_bleeding",
    "diagnoses": UGIB_DIAGNOSES,
    "questions": UGIB_QUESTIONS,
    "rules": UGIB_RULES,
    "priors": UGIB_PRIORS,
    "weight_rules": UGIB_WEIGHT_RULES,
    "baseline_investigations": UGIB_BASELINE,
    "advanced_investigations": UGIB_ADVANCED,
    "management": UGIB_MANAGEMENT,
}

LGIB_BUNDLE = {
    "complaint_code": "hist.lower_gi_bleeding",
    "diagnoses": LGIB_DIAGNOSES,
    "questions": LGIB_QUESTIONS,
    "rules": LGIB_RULES,
    "priors": LGIB_PRIORS,
    "weight_rules": LGIB_WEIGHT_RULES,
    "baseline_investigations": LGIB_BASELINE,
    "advanced_investigations": LGIB_ADVANCED,
    "management": LGIB_MANAGEMENT,
}

BLEEDING_BUNDLES = [UGIB_BUNDLE, LGIB_BUNDLE]
