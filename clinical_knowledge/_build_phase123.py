#!/usr/bin/env python3
"""One-shot builder for Phase 3 question library + Phase 2 history templates."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
QDIR = ROOT / "questions"
TDIR = ROOT / "templates" / "history"
PDIR = ROOT / "packs" / "complaints"

QDIR.mkdir(parents=True, exist_ok=True)
TDIR.mkdir(parents=True, exist_ok=True)
PDIR.mkdir(parents=True, exist_ok=True)

COUNTER = 0


def q(
    prompt: str,
    answer_type: str = "text",
    *,
    choices: list[str] | None = None,
    bates_domain: str = "HPI",
    dedupe_key: str | None = None,
    priority_default: str = "routine",
    specialty_tags: list[str] | None = None,
) -> dict:
    global COUNTER
    COUNTER += 1
    item = {
        "id": f"Q{COUNTER:06d}",
        "prompt": prompt,
        "answer_type": answer_type,
        "bates_domain": bates_domain,
        "dedupe_key": dedupe_key or f"auto_{COUNTER:06d}",
        "priority_default": priority_default,
        "schema_version": 1,
        "revision": 1,
        "status": "active",
        "specialty_tags": specialty_tags or ["general"],
    }
    if choices is not None:
        item["choices"] = choices
    return item


questions: list[dict] = []

# --- Universal HPI / symptom characteristics (Bates OLDCARTS-style) ---
questions += [
    q("What is the chief complaint in the patient's own words?", "text", bates_domain="HPI", dedupe_key="chief_complaint_verbatim"),
    q("When did this problem begin?", "duration", bates_domain="symptom_characteristics", dedupe_key="onset_timing"),
    q("Was the onset sudden or gradual?", "choice", choices=["Sudden", "Gradual", "Unclear"], bates_domain="symptom_characteristics", dedupe_key="onset_pattern"),
    q("Where is the symptom located?", "text", bates_domain="symptom_characteristics", dedupe_key="location"),
    q("Does the symptom radiate anywhere?", "text", bates_domain="symptom_characteristics", dedupe_key="radiation"),
    q("How would you describe the quality/character of the symptom?", "text", bates_domain="symptom_characteristics", dedupe_key="quality"),
    q("How severe is it on a scale of 0–10?", "scale", bates_domain="symptom_characteristics", dedupe_key="severity_0_10"),
    q("Is it constant or intermittent?", "choice", choices=["Constant", "Intermittent", "Waxing and waning", "Unclear"], bates_domain="symptom_characteristics", dedupe_key="timing_pattern"),
    q("How long does each episode last?", "duration", bates_domain="symptom_characteristics", dedupe_key="episode_duration"),
    q("How often does it occur?", "text", bates_domain="symptom_characteristics", dedupe_key="frequency"),
    q("What makes it worse?", "text", bates_domain="symptom_characteristics", dedupe_key="aggravating"),
    q("What makes it better?", "text", bates_domain="symptom_characteristics", dedupe_key="relieving"),
    q("Have the symptoms been getting better, worse, or staying the same?", "choice", choices=["Improving", "Worsening", "Stable", "Fluctuating", "Unclear"], bates_domain="symptom_characteristics", dedupe_key="course"),
    q("Have you had this same problem before?", "boolean", bates_domain="HPI", dedupe_key="prior_similar_episodes"),
    q("What happened around the time it started (context/setting)?", "text", bates_domain="HPI", dedupe_key="context_setting"),
    q("What treatments have you tried so far, and did they help?", "text", bates_domain="HPI", dedupe_key="treatments_tried"),
]

# Shared associated / systemic
questions += [
    q("Have you had fever?", "boolean", bates_domain="associated_symptoms", dedupe_key="assoc_fever"),
    q("Have you had chills or night sweats?", "boolean", bates_domain="associated_symptoms", dedupe_key="assoc_chills_sweats"),
    q("Have you had unintentional weight loss?", "boolean", bates_domain="associated_symptoms", dedupe_key="assoc_weight_loss", priority_default="high"),
    q("Have you had loss of appetite?", "boolean", bates_domain="associated_symptoms", dedupe_key="assoc_anorexia"),
    q("Have you had nausea?", "boolean", bates_domain="associated_symptoms", dedupe_key="assoc_nausea"),
    q("Have you had vomiting?", "boolean", bates_domain="associated_symptoms", dedupe_key="assoc_vomiting"),
    q("Have you had diarrhea?", "boolean", bates_domain="associated_symptoms", dedupe_key="assoc_diarrhea"),
    q("Have you had constipation?", "boolean", bates_domain="associated_symptoms", dedupe_key="assoc_constipation"),
    q("Have you had bloating or abdominal distension?", "boolean", bates_domain="associated_symptoms", dedupe_key="assoc_bloating"),
    q("Have you noticed jaundice (yellow eyes/skin)?", "boolean", bates_domain="associated_symptoms", dedupe_key="assoc_jaundice", priority_default="high"),
    q("Have you had dark urine?", "boolean", bates_domain="associated_symptoms", dedupe_key="assoc_dark_urine"),
    q("Have you had pale or clay-colored stools?", "boolean", bates_domain="associated_symptoms", dedupe_key="assoc_pale_stools"),
    q("Have you had itching (pruritus)?", "boolean", bates_domain="associated_symptoms", dedupe_key="assoc_pruritus"),
    q("Have you had heartburn or acid regurgitation?", "boolean", bates_domain="associated_symptoms", dedupe_key="assoc_heartburn"),
    q("Have you had difficulty swallowing?", "boolean", bates_domain="associated_symptoms", dedupe_key="assoc_dysphagia", priority_default="high"),
    q("Have you had painful swallowing?", "boolean", bates_domain="associated_symptoms", dedupe_key="assoc_odynophagia"),
    q("Have you vomited blood or coffee-ground material?", "boolean", bates_domain="red_flags", dedupe_key="rf_hematemesis", priority_default="emergency"),
    q("Have you passed black tarry stools (melena)?", "boolean", bates_domain="red_flags", dedupe_key="rf_melena", priority_default="emergency"),
    q("Have you passed bright red blood from the rectum?", "boolean", bates_domain="red_flags", dedupe_key="rf_hematochezia", priority_default="emergency"),
    q("Have you had chest pain?", "boolean", bates_domain="associated_symptoms", dedupe_key="assoc_chest_pain", priority_default="high"),
    q("Have you had shortness of breath?", "boolean", bates_domain="associated_symptoms", dedupe_key="assoc_dyspnea", priority_default="high"),
    q("Have you had lightheadedness, dizziness, or fainting?", "boolean", bates_domain="associated_symptoms", dedupe_key="assoc_dizziness_syncope", priority_default="high"),
    q("Have you had cough?", "boolean", bates_domain="associated_symptoms", dedupe_key="assoc_cough"),
    q("Have you had headache?", "boolean", bates_domain="associated_symptoms", dedupe_key="assoc_headache"),
    q("Have you had urinary symptoms (dysuria, frequency, hematuria)?", "boolean", bates_domain="associated_symptoms", dedupe_key="assoc_urinary"),
]

# GI-specific characteristics
questions += [
    q("Which part of the abdomen hurts most (point with one finger if possible)?", "choice", choices=["Epigastric", "RUQ", "LUQ", "RLQ", "LLQ", "Periumbilical", "Diffuse", "Other/unclear"], bates_domain="symptom_characteristics", dedupe_key="abd_pain_region", specialty_tags=["gastroenterology", "surgery", "emergency"]),
    q("Is the pain related to meals?", "choice", choices=["Worse after meals", "Better after meals", "Worse when fasting", "No relation", "Unclear"], bates_domain="symptom_characteristics", dedupe_key="abd_pain_meals", specialty_tags=["gastroenterology"]),
    q("Is the pain related to bowel movements?", "choice", choices=["Worse before BM", "Better after BM", "No relation", "Unclear"], bates_domain="symptom_characteristics", dedupe_key="abd_pain_bm", specialty_tags=["gastroenterology"]),
    q("Have you had inability to pass stool or gas?", "boolean", bates_domain="red_flags", dedupe_key="rf_obstipation", priority_default="emergency", specialty_tags=["surgery", "gastroenterology", "emergency"]),
    q("Have you noticed progressive abdominal swelling?", "boolean", bates_domain="associated_symptoms", dedupe_key="assoc_progressive_distension", specialty_tags=["gastroenterology", "hepatology"]),
    q("How many bowel movements per day (or week) currently?", "text", bates_domain="symptom_characteristics", dedupe_key="bm_frequency", specialty_tags=["gastroenterology"]),
    q("What is the stool consistency (e.g. Bristol description or watery/formed)?", "text", bates_domain="symptom_characteristics", dedupe_key="stool_consistency", specialty_tags=["gastroenterology"]),
    q("Is there mucus in the stool?", "boolean", bates_domain="associated_symptoms", dedupe_key="stool_mucus", specialty_tags=["gastroenterology"]),
    q("Is there urgency or incontinence with stools?", "boolean", bates_domain="associated_symptoms", dedupe_key="stool_urgency", specialty_tags=["gastroenterology"]),
    q("Any nocturnal diarrhea waking you from sleep?", "boolean", bates_domain="red_flags", dedupe_key="rf_nocturnal_diarrhea", priority_default="high", specialty_tags=["gastroenterology"]),
    q("Any recent antibiotic use?", "boolean", bates_domain="risk_factors", dedupe_key="rf_recent_antibiotics", specialty_tags=["infectious_disease", "gastroenterology"]),
    q("Any recent travel or suspect food/water exposure?", "boolean", bates_domain="risk_factors", dedupe_key="rf_travel_food", specialty_tags=["infectious_disease", "gastroenterology"]),
    q("Is dysphagia to solids, liquids, or both?", "choice", choices=["Solids only", "Liquids only", "Both", "Unclear"], bates_domain="symptom_characteristics", dedupe_key="dysphagia_solids_liquids", specialty_tags=["gastroenterology", "ent"]),
    q("Is dysphagia progressive or intermittent?", "choice", choices=["Progressive", "Intermittent", "Unclear"], bates_domain="symptom_characteristics", dedupe_key="dysphagia_course", specialty_tags=["gastroenterology"]),
    q("Do you feel food sticking, and where (neck vs chest)?", "text", bates_domain="symptom_characteristics", dedupe_key="dysphagia_level", specialty_tags=["gastroenterology", "ent"]),
    q("Any regurgitation of undigested food?", "boolean", bates_domain="associated_symptoms", dedupe_key="assoc_regurgitation", specialty_tags=["gastroenterology"]),
    q("Any food impaction episodes?", "boolean", bates_domain="red_flags", dedupe_key="rf_food_impaction", priority_default="high", specialty_tags=["gastroenterology"]),
    q("Does heartburn occur after meals or when lying down?", "choice", choices=["After meals", "When lying down", "Both", "Neither / unclear"], bates_domain="symptom_characteristics", dedupe_key="heartburn_triggers", specialty_tags=["gastroenterology"]),
    q("How often do you have heartburn?", "text", bates_domain="symptom_characteristics", dedupe_key="heartburn_frequency", specialty_tags=["gastroenterology"]),
    q("Any response to antacids or acid suppression?", "text", bates_domain="HPI", dedupe_key="heartburn_response_therapy", specialty_tags=["gastroenterology"]),
    q("Did jaundice start with pain, fever, or without symptoms?", "text", bates_domain="HPI", dedupe_key="jaundice_context", specialty_tags=["hepatology", "gastroenterology"]),
    q("Any known liver disease, hepatitis, or alcohol use relevant to this presentation?", "text", bates_domain="risk_factors", dedupe_key="jaundice_liver_risk", specialty_tags=["hepatology"]),
    q("Any pale stools and dark urine together?", "boolean", bates_domain="associated_symptoms", dedupe_key="cholestatic_features", specialty_tags=["hepatology"]),
]

# Chest / dyspnea specific
questions += [
    q("Is the chest pain pressure-like, sharp, burning, or tearing?", "choice", choices=["Pressure/squeezing", "Sharp/pleuritic", "Burning", "Tearing", "Other/unclear"], bates_domain="symptom_characteristics", dedupe_key="chest_pain_quality", specialty_tags=["cardiology", "emergency", "pulmonology"], priority_default="high"),
    q("Does chest pain radiate to arm, jaw, back, or neck?", "text", bates_domain="symptom_characteristics", dedupe_key="chest_pain_radiation", specialty_tags=["cardiology", "emergency"], priority_default="high"),
    q("Is chest pain worse with exertion or better with rest?", "choice", choices=["Worse with exertion", "Better with rest", "No relation", "Unclear"], bates_domain="symptom_characteristics", dedupe_key="chest_pain_exertion", specialty_tags=["cardiology", "emergency"], priority_default="high"),
    q("Is chest pain worse with breathing or position?", "text", bates_domain="symptom_characteristics", dedupe_key="chest_pain_pleuritic_positional", specialty_tags=["pulmonology", "cardiology", "emergency"]),
    q("Any associated sweating, nausea, or sense of doom?", "boolean", bates_domain="red_flags", dedupe_key="rf_acs_assoc", priority_default="emergency", specialty_tags=["cardiology", "emergency"]),
    q("Is dyspnea at rest, with exertion, or orthopnea/PND?", "text", bates_domain="symptom_characteristics", dedupe_key="dyspnea_pattern", specialty_tags=["pulmonology", "cardiology", "emergency"], priority_default="high"),
    q("Any wheezing or known asthma/COPD?", "text", bates_domain="associated_symptoms", dedupe_key="dyspnea_wheeze_lung_hx", specialty_tags=["pulmonology"]),
    q("Any leg swelling?", "boolean", bates_domain="associated_symptoms", dedupe_key="assoc_leg_edema", specialty_tags=["cardiology", "general"]),
]

# Red flags general
questions += [
    q("Any severe or rapidly worsening pain?", "boolean", bates_domain="red_flags", dedupe_key="rf_severe_pain", priority_default="emergency"),
    q("Any confusion, lethargy, or altered mental status?", "boolean", bates_domain="red_flags", dedupe_key="rf_altered_mental", priority_default="emergency"),
    q("Any signs of dehydration (very dry mouth, little urine, extreme thirst)?", "boolean", bates_domain="red_flags", dedupe_key="rf_dehydration", priority_default="high"),
    q("Any pregnancy possibility?", "boolean", bates_domain="risk_factors", dedupe_key="rf_pregnancy", priority_default="high", specialty_tags=["obstetrics", "emergency", "general"]),
    q("Any black stools or vomiting blood (reconfirm GI bleed alarms)?", "boolean", bates_domain="red_flags", dedupe_key="rf_gi_bleed_confirm", priority_default="emergency", specialty_tags=["gastroenterology", "emergency"]),
]

# PMH / PSH / drugs / allergies / FH / SH
questions += [
    q("What medical problems have you been diagnosed with in the past?", "text", bates_domain="PMH", dedupe_key="pmh_list"),
    q("Any prior hospitalizations related to this problem?", "boolean", bates_domain="PMH", dedupe_key="pmh_related_admissions"),
    q("What surgeries have you had?", "text", bates_domain="PSH", dedupe_key="psh_list"),
    q("What medicines do you take regularly (including over-the-counter and herbs)?", "text", bates_domain="drugs", dedupe_key="meds_list"),
    q("Are you taking NSAIDs, aspirin, or blood thinners?", "boolean", bates_domain="drugs", dedupe_key="meds_nsaid_aspirin_anticoag", priority_default="high"),
    q("Do you have any drug allergies? What happens?", "text", bates_domain="allergies", dedupe_key="allergies_detail"),
    q("Is there important disease in your family (especially similar problems or cancer)?", "text", bates_domain="FH", dedupe_key="fh_summary"),
    q("Do you smoke or use tobacco? How much and for how long?", "text", bates_domain="SH", dedupe_key="sh_tobacco"),
    q("Do you drink alcohol? How much and how often?", "text", bates_domain="SH", dedupe_key="sh_alcohol"),
    q("Any recreational drug use?", "text", bates_domain="SH", dedupe_key="sh_drugs"),
    q("What is your occupation and any relevant exposures?", "text", bates_domain="SH", dedupe_key="sh_occupation"),
    q("Who do you live with / what support do you have at home?", "text", bates_domain="SH", dedupe_key="sh_support"),
]

# ROS brief GI/general
questions += [
    q("Any other new symptoms not already discussed?", "text", bates_domain="ROS", dedupe_key="ros_other"),
    q("Any change in bowel habit lasting more than a few weeks?", "boolean", bates_domain="ROS", dedupe_key="ros_bowel_habit_change", priority_default="high", specialty_tags=["gastroenterology"]),
    q("Any early satiety?", "boolean", bates_domain="ROS", dedupe_key="ros_early_satiety", specialty_tags=["gastroenterology"]),
]

# Build ID lookup by dedupe_key
by_key = {item["dedupe_key"]: item["id"] for item in questions}


def ids(*keys: str) -> list[str]:
    out = []
    for k in keys:
        if k not in by_key:
            raise KeyError(k)
        out.append(by_key[k])
    return out


COMMON_BACKGROUND = ids(
    "pmh_list",
    "pmh_related_admissions",
    "psh_list",
    "meds_list",
    "meds_nsaid_aspirin_anticoag",
    "allergies_detail",
    "fh_summary",
    "sh_tobacco",
    "sh_alcohol",
    "sh_drugs",
    "sh_occupation",
    "sh_support",
    "ros_other",
)

CORE_HPI = ids(
    "chief_complaint_verbatim",
    "onset_timing",
    "onset_pattern",
    "location",
    "radiation",
    "quality",
    "severity_0_10",
    "timing_pattern",
    "episode_duration",
    "frequency",
    "aggravating",
    "relieving",
    "course",
    "prior_similar_episodes",
    "context_setting",
    "treatments_tried",
)


def template(
    complaint_code: str,
    name: str,
    synonyms: list[str],
    body_system: str,
    sections: list[dict],
    red_flags: list[str],
    associated: list[str] | None = None,
) -> dict:
    return {
        "id": f"HT_{complaint_code}",
        "complaint_code": f"CC_{complaint_code}",
        "name": name,
        "synonyms": synonyms,
        "body_system": body_system,
        "source": {
            "work": "Bates' Guide to Physical Examination and History Taking",
            "note": "Structure for history-taking only; not for disease extraction.",
        },
        "red_flag_question_ids": red_flags,
        "sections": sections,
        "associated_complaint_codes": associated or [],
        "schema_version": 1,
        "revision": 1,
        "status": "active",
    }


templates = {
    "abdominal_pain": template(
        "abdominal_pain",
        "Abdominal pain history",
        ["Belly pain", "Stomach pain", "Abdominal discomfort"],
        "abdomen",
        [
            {"key": "hpi_core", "title": "HPI — core characteristics", "question_ids": CORE_HPI + ids("abd_pain_region", "abd_pain_meals", "abd_pain_bm")},
            {"key": "associated", "title": "Associated symptoms", "question_ids": ids(
                "assoc_nausea", "assoc_vomiting", "assoc_diarrhea", "assoc_constipation", "assoc_bloating",
                "assoc_fever", "assoc_anorexia", "assoc_jaundice", "assoc_urinary",
                "assoc_chest_pain", "assoc_dyspnea", "assoc_dizziness_syncope",
            )},
            {"key": "red_flags", "title": "Alarm / red flags", "question_ids": ids(
                "rf_hematemesis", "rf_melena", "rf_hematochezia", "rf_obstipation", "rf_severe_pain",
                "rf_altered_mental", "rf_dehydration", "rf_pregnancy", "assoc_weight_loss",
            )},
            {"key": "risk_context", "title": "Risk factors & exposures", "question_ids": ids("rf_travel_food", "rf_recent_antibiotics")},
            {"key": "background", "title": "PMH / PSH / meds / allergies / FH / SH", "question_ids": COMMON_BACKGROUND},
        ],
        ids("rf_hematemesis", "rf_melena", "rf_hematochezia", "rf_obstipation", "rf_severe_pain", "rf_altered_mental", "rf_pregnancy"),
        ["CC_nausea", "CC_vomiting", "CC_diarrhea", "CC_constipation", "CC_jaundice"],
    ),
    "dysphagia": template(
        "dysphagia",
        "Dysphagia history",
        ["Difficulty swallowing", "Food sticking"],
        "esophagus",
        [
            {"key": "hpi_core", "title": "HPI — core characteristics", "question_ids": CORE_HPI + ids(
                "dysphagia_solids_liquids", "dysphagia_course", "dysphagia_level",
            )},
            {"key": "associated", "title": "Associated symptoms", "question_ids": ids(
                "assoc_odynophagia", "assoc_regurgitation", "assoc_heartburn", "assoc_weight_loss",
                "assoc_cough", "assoc_chest_pain", "assoc_anorexia",
            )},
            {"key": "red_flags", "title": "Alarm / red flags", "question_ids": ids(
                "rf_food_impaction", "assoc_weight_loss", "rf_hematemesis", "assoc_dysphagia",
            )},
            {"key": "background", "title": "PMH / PSH / meds / allergies / FH / SH", "question_ids": COMMON_BACKGROUND},
        ],
        ids("rf_food_impaction", "assoc_weight_loss", "rf_hematemesis"),
        ["CC_heartburn", "CC_odynophagia", "CC_chest_pain"],
    ),
    "diarrhea": template(
        "diarrhea",
        "Diarrhea history",
        ["Loose stools", "Watery stools"],
        "abdomen",
        [
            {"key": "hpi_core", "title": "HPI — core characteristics", "question_ids": CORE_HPI + ids(
                "bm_frequency", "stool_consistency", "stool_mucus", "stool_urgency",
            )},
            {"key": "associated", "title": "Associated symptoms", "question_ids": ids(
                "abd_pain_region",
                "assoc_nausea", "assoc_vomiting", "assoc_fever", "assoc_anorexia", "assoc_weight_loss",
                "assoc_bloating",
            )},
            {"key": "red_flags", "title": "Alarm / red flags", "question_ids": ids(
                "rf_hematochezia", "rf_melena", "rf_nocturnal_diarrhea", "rf_dehydration",
                "assoc_weight_loss", "rf_altered_mental",
            )},
            {"key": "risk_context", "title": "Risk factors & exposures", "question_ids": ids("rf_travel_food", "rf_recent_antibiotics")},
            {"key": "background", "title": "PMH / PSH / meds / allergies / FH / SH", "question_ids": COMMON_BACKGROUND + ids("ros_bowel_habit_change")},
        ],
        ids("rf_hematochezia", "rf_melena", "rf_nocturnal_diarrhea", "rf_dehydration", "assoc_weight_loss"),
        ["CC_abdominal_pain", "CC_vomiting", "CC_fever"],
    ),
    "constipation": template(
        "constipation",
        "Constipation history",
        ["Infrequent stools", "Hard stools", "Difficulty passing stool"],
        "abdomen",
        [
            {"key": "hpi_core", "title": "HPI — core characteristics", "question_ids": CORE_HPI + ids("bm_frequency", "stool_consistency")},
            {"key": "associated", "title": "Associated symptoms", "question_ids": ids(
                "abd_pain_region", "assoc_bloating", "assoc_nausea", "assoc_vomiting", "assoc_anorexia", "ros_early_satiety",
            )},
            {"key": "red_flags", "title": "Alarm / red flags", "question_ids": ids(
                "rf_obstipation", "rf_hematochezia", "assoc_weight_loss", "rf_severe_pain", "ros_bowel_habit_change",
            )},
            {"key": "background", "title": "PMH / PSH / meds / allergies / FH / SH", "question_ids": COMMON_BACKGROUND},
        ],
        ids("rf_obstipation", "rf_hematochezia", "assoc_weight_loss", "rf_severe_pain"),
        ["CC_abdominal_pain", "CC_vomiting"],
    ),
    "heartburn": template(
        "heartburn",
        "Heartburn / reflux symptom history",
        ["Pyrosis", "Acid reflux", "GERD symptoms"],
        "esophagus",
        [
            {"key": "hpi_core", "title": "HPI — core characteristics", "question_ids": CORE_HPI + ids(
                "heartburn_triggers", "heartburn_frequency", "heartburn_response_therapy",
            )},
            {"key": "associated", "title": "Associated symptoms", "question_ids": ids(
                "assoc_regurgitation", "assoc_dysphagia", "assoc_odynophagia", "assoc_chest_pain", "assoc_cough", "assoc_nausea",
            )},
            {"key": "red_flags", "title": "Alarm / red flags", "question_ids": ids(
                "assoc_dysphagia", "assoc_weight_loss", "rf_hematemesis", "rf_melena", "assoc_odynophagia",
            )},
            {"key": "background", "title": "PMH / PSH / meds / allergies / FH / SH", "question_ids": COMMON_BACKGROUND},
        ],
        ids("assoc_dysphagia", "assoc_weight_loss", "rf_hematemesis", "rf_melena"),
        ["CC_dysphagia", "CC_chest_pain", "CC_abdominal_pain"],
    ),
    "jaundice": template(
        "jaundice",
        "Jaundice history",
        ["Icterus", "Yellow eyes/skin"],
        "hepatobiliary",
        [
            {"key": "hpi_core", "title": "HPI — core characteristics", "question_ids": CORE_HPI + ids("jaundice_context", "cholestatic_features")},
            {"key": "associated", "title": "Associated symptoms", "question_ids": ids(
                "assoc_dark_urine", "assoc_pale_stools", "assoc_pruritus", "abd_pain_region",
                "assoc_fever", "assoc_nausea", "assoc_vomiting", "assoc_anorexia", "assoc_weight_loss", "assoc_bloating",
            )},
            {"key": "red_flags", "title": "Alarm / red flags", "question_ids": ids(
                "assoc_fever", "rf_altered_mental", "rf_hematemesis", "rf_melena", "rf_severe_pain",
            )},
            {"key": "risk_context", "title": "Risk factors", "question_ids": ids("jaundice_liver_risk", "rf_travel_food")},
            {"key": "background", "title": "PMH / PSH / meds / allergies / FH / SH", "question_ids": COMMON_BACKGROUND},
        ],
        ids("assoc_fever", "rf_altered_mental", "rf_hematemesis", "rf_melena", "rf_severe_pain"),
        ["CC_abdominal_pain", "CC_pruritus", "CC_fever"],
    ),
    "chest_pain": template(
        "chest_pain",
        "Chest pain history",
        ["Thoracic pain", "Chest discomfort"],
        "thorax",
        [
            {"key": "hpi_core", "title": "HPI — core characteristics", "question_ids": CORE_HPI + ids(
                "chest_pain_quality", "chest_pain_radiation", "chest_pain_exertion", "chest_pain_pleuritic_positional",
            )},
            {"key": "associated", "title": "Associated symptoms", "question_ids": ids(
                "assoc_dyspnea", "assoc_cough", "assoc_nausea", "assoc_dizziness_syncope", "assoc_heartburn", "rf_acs_assoc",
            )},
            {"key": "red_flags", "title": "Alarm / red flags", "question_ids": ids(
                "rf_acs_assoc", "assoc_dyspnea", "assoc_dizziness_syncope", "rf_severe_pain", "rf_altered_mental",
            )},
            {"key": "background", "title": "PMH / PSH / meds / allergies / FH / SH", "question_ids": COMMON_BACKGROUND},
        ],
        ids("rf_acs_assoc", "assoc_dyspnea", "assoc_dizziness_syncope", "rf_severe_pain"),
        ["CC_dyspnea", "CC_heartburn", "CC_syncope"],
    ),
    "dyspnea": template(
        "dyspnea",
        "Dyspnea / shortness of breath history",
        ["Breathlessness", "Shortness of breath", "Difficulty breathing"],
        "respiratory",
        [
            {"key": "hpi_core", "title": "HPI — core characteristics", "question_ids": CORE_HPI + ids("dyspnea_pattern", "dyspnea_wheeze_lung_hx")},
            {"key": "associated", "title": "Associated symptoms", "question_ids": ids(
                "assoc_chest_pain", "assoc_cough", "assoc_fever", "assoc_leg_edema", "assoc_dizziness_syncope",
            )},
            {"key": "red_flags", "title": "Alarm / red flags", "question_ids": ids(
                "assoc_chest_pain", "assoc_dizziness_syncope", "rf_altered_mental", "rf_severe_pain",
            )},
            {"key": "background", "title": "PMH / PSH / meds / allergies / FH / SH", "question_ids": COMMON_BACKGROUND},
        ],
        ids("assoc_chest_pain", "assoc_dizziness_syncope", "rf_altered_mental"),
        ["CC_chest_pain", "CC_cough", "CC_fever"],
    ),
    "vomiting": template(
        "vomiting",
        "Vomiting / nausea history",
        ["Emesis", "Throwing up", "Nausea and vomiting"],
        "abdomen",
        [
            {"key": "hpi_core", "title": "HPI — core characteristics", "question_ids": CORE_HPI},
            {"key": "associated", "title": "Associated symptoms", "question_ids": ids(
                "assoc_nausea", "abd_pain_region", "assoc_diarrhea", "assoc_fever", "assoc_headache", "assoc_dizziness_syncope",
            )},
            {"key": "red_flags", "title": "Alarm / red flags", "question_ids": ids(
                "rf_hematemesis", "rf_dehydration", "rf_altered_mental", "rf_obstipation", "assoc_weight_loss",
            )},
            {"key": "risk_context", "title": "Risk factors & exposures", "question_ids": ids("rf_travel_food", "rf_recent_antibiotics", "rf_pregnancy")},
            {"key": "background", "title": "PMH / PSH / meds / allergies / FH / SH", "question_ids": COMMON_BACKGROUND},
        ],
        ids("rf_hematemesis", "rf_dehydration", "rf_altered_mental", "rf_obstipation"),
        ["CC_abdominal_pain", "CC_diarrhea", "CC_headache"],
    ),
    "fever": template(
        "fever",
        "Fever history",
        ["Pyrexia", "High temperature"],
        "general",
        [
            {"key": "hpi_core", "title": "HPI — core characteristics", "question_ids": CORE_HPI},
            {"key": "associated", "title": "Associated symptoms", "question_ids": ids(
                "assoc_chills_sweats", "assoc_cough", "assoc_headache", "assoc_nausea", "assoc_vomiting",
                "assoc_diarrhea", "assoc_urinary", "abd_pain_region", "assoc_dyspnea",
            )},
            {"key": "red_flags", "title": "Alarm / red flags", "question_ids": ids(
                "rf_altered_mental", "rf_severe_pain", "assoc_dyspnea", "rf_dehydration",
            )},
            {"key": "risk_context", "title": "Risk factors & exposures", "question_ids": ids("rf_travel_food", "rf_recent_antibiotics")},
            {"key": "background", "title": "PMH / PSH / meds / allergies / FH / SH", "question_ids": COMMON_BACKGROUND},
        ],
        ids("rf_altered_mental", "rf_severe_pain", "assoc_dyspnea", "rf_dehydration"),
        ["CC_cough", "CC_abdominal_pain", "CC_dysuria"],
    ),
    "weight_loss": template(
        "weight_loss",
        "Unintentional weight loss history",
        ["Losing weight", "Unexplained weight loss"],
        "general",
        [
            {"key": "hpi_core", "title": "HPI — core characteristics", "question_ids": CORE_HPI + ids("assoc_anorexia", "ros_early_satiety")},
            {"key": "associated", "title": "Associated symptoms", "question_ids": ids(
                "assoc_fever", "assoc_chills_sweats", "assoc_diarrhea", "assoc_dysphagia", "assoc_nausea",
                "assoc_vomiting", "assoc_jaundice", "ros_bowel_habit_change",
            )},
            {"key": "red_flags", "title": "Alarm / red flags", "question_ids": ids(
                "assoc_dysphagia", "rf_hematemesis", "rf_melena", "rf_hematochezia", "assoc_jaundice",
            )},
            {"key": "background", "title": "PMH / PSH / meds / allergies / FH / SH", "question_ids": COMMON_BACKGROUND},
        ],
        ids("assoc_dysphagia", "rf_hematemesis", "rf_melena", "rf_hematochezia", "assoc_jaundice"),
        ["CC_anorexia", "CC_diarrhea", "CC_dysphagia", "CC_jaundice"],
    ),
}

# Fix diarrhea associated that incorrectly used abd_pain_region as stand-in — add a dedicated bool if missing
# Already have abd_pain_region; for diarrhea it's OK as location probe when pain present.
# Clean dead ternary leftovers: none remain if we used proper keys.

library = {
    "schema_version": 1,
    "revision": 1,
    "description": "Universal Question Library — Phase 3. Templates reference ids only; never duplicate prompts.",
    "next_id": COUNTER + 1,
    "questions": questions,
}

def dump(obj) -> str:
    return json.dumps(obj, indent=2, ensure_ascii=False) + "\n"


(QDIR / "library.json").write_text(dump(library), encoding="utf-8")
(QDIR / "_index.json").write_text(
    dump(
        {
            "schema_version": 1,
            "revision": 1,
            "library_file": "library.json",
            "question_count": len(questions),
            "id_range": {"first": "Q000001", "last": questions[-1]["id"]},
            "next_id": COUNTER + 1,
        }
    ),
    encoding="utf-8",
)

for code, tmpl in templates.items():
    (TDIR / f"{code}.json").write_text(dump(tmpl), encoding="utf-8")

# Validate all referenced Q ids exist
all_q = {item["id"] for item in questions}
missing = []
for code, tmpl in templates.items():
    for sec in tmpl["sections"]:
        for qid in sec["question_ids"]:
            if qid not in all_q:
                missing.append((code, qid))
    for qid in tmpl["red_flag_question_ids"]:
        if qid not in all_q:
            missing.append((code, f"red:{qid}"))

manifest = {
    "schema_version": 1,
    "revision": 1,
    "phase": "1-3",
    "dictionary_index": "dictionary/_index.json",
    "question_library": "questions/library.json",
    "history_templates": sorted(f"templates/history/{c}.json" for c in templates),
    "complaint_codes": [f"CC_{c}" for c in sorted(templates)],
    "question_count": len(questions),
    "template_count": len(templates),
    "validation": {"missing_question_refs": missing, "ok": not missing},
}
(ROOT / "manifest.json").write_text(dump(manifest), encoding="utf-8")

(PDIR / "_index.json").write_text(
    dump(
        {
            "schema_version": 1,
            "revision": 1,
            "complaints": [
                {
                    "complaint_code": f"CC_{c}",
                    "history_template": f"templates/history/{c}.json",
                    "name": templates[c]["name"],
                }
                for c in sorted(templates)
            ],
        }
    ),
    encoding="utf-8",
)

print(f"Wrote {len(questions)} questions and {len(templates)} templates; missing={missing}")
