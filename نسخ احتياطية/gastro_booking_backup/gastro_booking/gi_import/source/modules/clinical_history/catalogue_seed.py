"""Chief complaints, adaptive question trees, differential weights — Sprint 4C-HIST seed."""

import json

from app.extensions import db
from app.modules.clinical_history.models import (
    ANSWER_TYPE_BOOLEAN,
    ANSWER_TYPE_CHOICE,
    ANSWER_TYPE_TEXT,
    ChiefComplaintDefinition,
    DiagnosisDefinition,
    HistoryQuestionDefinition,
    ManagementGuidanceRule,
)
from app.modules.clinical_history.catalogue_bundle_loader import seed_intelligence_bundle
from app.modules.clinical_history.catalogue_gi_bundles import ALL_INTELLIGENCE_BUNDLES

CHIEF_COMPLAINTS = [
    ("hist.abdominal_pain", "Abdominal pain", "gi", 10, "kl.complaint.abdominal_pain"),
    ("hist.upper_gi_bleeding", "Upper GI bleeding", "gi", 20, "kl.complaint.upper_gi_bleeding"),
    ("hist.lower_gi_bleeding", "Lower GI bleeding", "gi", 30, "kl.complaint.lower_gi_bleeding"),
    ("hist.dysphagia", "Dysphagia", "gi", 40, "kl.complaint.dysphagia"),
    ("hist.diarrhea", "Diarrhea", "gi", 50, "kl.complaint.diarrhea"),
    ("hist.constipation", "Constipation", "gi", 60, "kl.complaint.constipation"),
    ("hist.jaundice", "Jaundice", "hepatology", 70, "kl.complaint.jaundice"),
    ("hist.ascites", "Ascites", "hepatology", 75, "kl.complaint.ascites"),
    ("hist.dyspepsia", "Dyspepsia", "gi", 80, "kl.complaint.dyspepsia"),
    ("hist.pancreatitis", "Pancreatitis", "gi", 85, "kl.complaint.pancreatitis"),
    ("hist.biliary_pain", "Biliary pain", "hepatology", 90, "kl.complaint.biliary_pain"),
    ("hist.weight_loss", "Weight loss", "gi", 95, "kl.complaint.weight_loss"),
    ("hist.vomiting", "Vomiting", "gi", 100, "kl.complaint.vomiting"),
    ("hist.chronic_liver_disease", "Chronic liver disease", "hepatology", 110, "kl.complaint.chronic_liver_disease"),
]

# Shared diagnoses referenced across multiple complaint bundles
BASE_DIAGNOSES = [
    ("dx.peptic_ulcer_bleed", "Peptic ulcer bleeding", "gi", "kl.ugib.peptic_ulcer"),
    ("dx.variceal_bleed", "Variceal bleeding", "hepatology", "kl.ugib.variceal"),
    ("dx.mallory_weiss", "Mallory-Weiss tear", "gi", "kl.ugib.mallory_weiss"),
    ("dx.gastric_malignancy", "Gastric malignancy", "gi", "kl.gastric_cancer.overview"),
    ("dx.ibs", "Irritable bowel syndrome", "gi", "kl.ibs.overview"),
    ("dx.ibd", "Inflammatory bowel disease", "gi", "kl.ibd.overview"),
    ("dx.cholelithiasis", "Cholelithiasis / biliary colic", "hepatology", "kl.biliary.cholelithiasis"),
    ("dx.viral_hepatitis", "Viral hepatitis", "hepatology", "kl.jaundice.viral_hepatitis"),
    ("dx.pancreatitis", "Acute pancreatitis", "gi", "kl.pancreatitis.acute"),
    ("dx.gerd", "Gastro-oesophageal reflux disease", "gi", "kl.gerd.overview"),
    ("dx.achalasia", "Achalasia", "gi", "kl.achalasia.overview"),
    ("dx.colorectal_cancer", "Colorectal cancer", "gi", "kl.colorectal_cancer.overview"),
]

# Shared + chronic diarrhoea base questions (extended in diarrhoea intelligence bundle)
COMMON_AND_DIARRHEA_QUESTIONS = [
    ("q.common.pmh", "Relevant past medical history", "pmh", ANSWER_TYPE_TEXT, None, False, None),
    ("q.common.surgical", "Previous abdominal or GI surgery", "surgical", ANSWER_TYPE_TEXT, None, False, None),
    ("q.common.drugs", "Current medications", "drugs", ANSWER_TYPE_TEXT, None, False, None),
    ("q.common.allergy", "Drug allergies", "allergy", ANSWER_TYPE_TEXT, None, False, None),
    ("q.common.family", "Relevant family history", "family", ANSWER_TYPE_TEXT, None, False, None),
    ("q.common.smoking", "Smoking status", "social", ANSWER_TYPE_CHOICE, ["never", "former", "current"], False, None),
    ("q.common.alcohol_social", "Alcohol use?", "social", ANSWER_TYPE_CHOICE,
     ["None", "Occasional", "Regular", "Heavy"], False,
     "Alcohol use affects bleeding risk, liver disease, pancreatitis, and malignancy work-up."),
    ("q.diar.frequency", "Bowel frequency per day", "presenting", ANSWER_TYPE_CHOICE, ["1-3", "4-6", "7+"], False, None),
    ("q.diar.blood", "Visible blood in stool?", "presenting", ANSWER_TYPE_BOOLEAN, None, False, None),
    ("q.diar.nocturnal", "Nocturnal diarrhea?", "exclusion", ANSWER_TYPE_BOOLEAN, None, True, "Against IBS — consider IBD"),
    ("q.diar.weight_loss", "Weight loss?", "exclusion", ANSWER_TYPE_BOOLEAN, None, True, None),
    ("q.diar.fever", "Fever?", "exclusion", ANSWER_TYPE_BOOLEAN, None, True, None),
    ("q.diar.family_ibd", "Family history of IBD?", "exclusion", ANSWER_TYPE_BOOLEAN, None, True, None),
]

SHARED_MANAGEMENT = [
    (
        "dx.ibd",
        "Inflammatory bowel disease — Crohn's or ulcerative colitis.",
        "Confirm with colonoscopy and histology; assess disease extent and severity; induction then maintenance therapy.",
        "Mayo score (UC); Crohn's disease activity indices.",
        "Toxic megacolon, severe anaemia, perianal sepsis, significant weight loss.",
        "Gastroenterology clinic follow-up; colonoscopic surveillance per guidelines.",
        "kl.ibd.overview",
    ),
    (
        "dx.ibs",
        "Irritable bowel syndrome — diagnosis of exclusion.",
        "Apply Rome IV criteria; minimal investigations if low alarm features; diet and lifestyle first line.",
        "No mandatory score — consider IBS-SSS for severity tracking.",
        "New alarm features: weight loss, bleeding, nocturnal symptoms, anaemia, family history CRC.",
        "Primary care or gastroenterology review if symptoms refractory.",
        "kl.ibs.overview",
    ),
]


def seed_clinical_history_catalogue_if_empty() -> int:
    from app.modules.knowledge_library.catalogue_migrator import (
        kl_catalogue_is_seeded,
        migrate_catalogue_to_knowledge_library_if_empty,
    )
    from app.modules.knowledge_library.ui_catalogue_sync import sync_ui_catalogue_from_knowledge_library
    from app.modules.clinical_history.intelligence.catalog_provider import reset_catalog_provider
    from app.modules.knowledge_library.kl_catalog_loader import reset_kl_catalog_index

    migrated = migrate_catalogue_to_knowledge_library_if_empty()
    if migrated > 0 or kl_catalogue_is_seeded():
        reset_kl_catalog_index()
        reset_catalog_provider()
        ui_count = sync_ui_catalogue_from_knowledge_library()
        return migrated + ui_count

    if ChiefComplaintDefinition.query.first() is not None:
        return 0

    count = 0
    for code, name, category, sort_order, kl_key in CHIEF_COMPLAINTS:
        db.session.add(ChiefComplaintDefinition(
            code=code,
            name=name,
            category=category,
            sort_order=sort_order,
            knowledge_topic_key=kl_key,
            department_id=1,
        ))
        count += 1

    for code, prompt, section, atype, choices, is_excl, help_text in COMMON_AND_DIARRHEA_QUESTIONS:
        db.session.add(HistoryQuestionDefinition(
            code=code,
            prompt_text=prompt,
            section=section,
            answer_type=atype,
            choices_json=json.dumps(choices) if choices else None,
            is_exclusion_question=is_excl,
            help_text=help_text,
            department_id=1,
        ))
        count += 1

    db.session.flush()

    for dx_code, dx_name, dx_cat, kl_key in BASE_DIAGNOSES:
        db.session.add(DiagnosisDefinition(
            code=dx_code,
            name=dx_name,
            category=dx_cat,
            knowledge_topic_key=kl_key,
            department_id=1,
        ))
        count += 1

    for bundle in ALL_INTELLIGENCE_BUNDLES:
        count += seed_intelligence_bundle(**bundle)

    for row in SHARED_MANAGEMENT:
        if ManagementGuidanceRule.query.filter_by(diagnosis_code=row[0]).first() is None:
            db.session.add(ManagementGuidanceRule(
                diagnosis_code=row[0],
                summary_text=row[1],
                principles_text=row[2],
                scores_text=row[3],
                red_flags_text=row[4],
                follow_up_text=row[5],
                knowledge_topic_key=row[6],
                department_id=1,
            ))
            count += 1

    db.session.commit()
    return count
