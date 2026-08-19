"""Default management plan rules seed — configurable data, not hardcoded engine logic."""

from __future__ import annotations

from app.extensions import db
from app.modules.management_plan_ai.constants import (
    CATEGORY_FOLLOW_UP,
    CATEGORY_MONITORING,
    CATEGORY_PATIENT_EDUCATION,
    CATEGORY_REFERRAL,
    CATEGORY_SAFETY,
    CATEGORY_TREATMENT,
    PRIORITY_ESSENTIAL,
    PRIORITY_OPTIONAL,
    PRIORITY_RECOMMENDED,
)
from app.modules.management_plan_ai.models import ManagementPlanRule

DEFAULT_SPECIALTY = "gastroenterology"

RULES = [
    {
        "diagnosis_name": "Peptic ulcer disease",
        "complaint_code": "intake.cc.epigastric_pain",
        "category": CATEGORY_TREATMENT,
        "description_template": (
            "Consider acid suppression therapy pathway (e.g. PPI class) per local guideline — "
            "physician to select agent and dosing. Do not auto-prescribe."
        ),
        "clinical_indication": "Suspected or confirmed peptic ulcer disease",
        "priority": PRIORITY_ESSENTIAL,
        "knowledge_topic_key": "kl.epigastric.overview",
        "guideline_reference": "Acid suppression for peptic ulcer disease",
        "sort_order": 10,
    },
    {
        "diagnosis_name": "Peptic ulcer disease",
        "category": CATEGORY_MONITORING,
        "description_template": "Monitor for alarm features: haematemesis, melaena, weight loss, anaemia progression.",
        "clinical_indication": "Safety monitoring during ulcer management",
        "priority": PRIORITY_ESSENTIAL,
        "guideline_reference": "Alarm feature monitoring",
        "sort_order": 20,
    },
    {
        "diagnosis_name": "Peptic ulcer disease",
        "category": CATEGORY_FOLLOW_UP,
        "description_template": "Arrange follow-up to assess symptom response and review need for endoscopy or H. pylori testing.",
        "clinical_indication": "Structured follow-up after initial management",
        "priority": PRIORITY_RECOMMENDED,
        "sort_order": 30,
    },
    {
        "diagnosis_name": "Peptic ulcer disease",
        "category": CATEGORY_PATIENT_EDUCATION,
        "description_template": "Educate on NSAID avoidance, alcohol moderation, and when to seek urgent care for bleeding symptoms.",
        "clinical_indication": "Patient self-management support",
        "priority": PRIORITY_RECOMMENDED,
        "sort_order": 40,
    },
    {
        "diagnosis_name": "Peptic ulcer disease",
        "category": CATEGORY_SAFETY,
        "description_template": "Review anticoagulant/antiplatelet use and bleeding risk with patient context.",
        "clinical_indication": "Bleeding risk mitigation",
        "priority": PRIORITY_ESSENTIAL,
        "sort_order": 15,
    },
    {
        "diagnosis_name": "Gastro-oesophageal reflux disease",
        "complaint_code": "intake.cc.epigastric_pain",
        "category": CATEGORY_TREATMENT,
        "description_template": (
            "Consider lifestyle modification and acid suppression pathway per guideline — "
            "physician to select therapy. No automatic prescription."
        ),
        "clinical_indication": "Reflux-related epigastric symptoms",
        "priority": PRIORITY_RECOMMENDED,
        "sort_order": 10,
    },
    {
        "diagnosis_name": "Gastro-oesophageal reflux disease",
        "category": CATEGORY_MONITORING,
        "description_template": "Monitor symptom frequency, nocturnal symptoms, and dysphagia.",
        "clinical_indication": "Assess response and alarm features",
        "priority": PRIORITY_RECOMMENDED,
        "sort_order": 20,
    },
    {
        "diagnosis_name": "Gastro-oesophageal reflux disease",
        "category": CATEGORY_FOLLOW_UP,
        "description_template": "Review at 4–8 weeks if symptoms persist; consider endoscopy if alarm features develop.",
        "clinical_indication": "Step-up care planning",
        "priority": PRIORITY_OPTIONAL,
        "sort_order": 30,
    },
    {
        "diagnosis_name": "Upper gastrointestinal bleeding",
        "category": CATEGORY_TREATMENT,
        "description_template": (
            "Resuscitation and haemostasis pathway per local UGI bleeding protocol — "
            "physician-directed; no automatic treatment orders."
        ),
        "clinical_indication": "Active or recent upper GI bleeding",
        "priority": PRIORITY_ESSENTIAL,
        "knowledge_topic_key": "kl.epigastric.overview",
        "guideline_reference": "UGI bleeding management protocol",
        "sort_order": 5,
    },
    {
        "diagnosis_name": "Upper gastrointestinal bleeding",
        "category": CATEGORY_MONITORING,
        "description_template": "Serial haemoglobin, haemodynamic monitoring, and transfusion threshold assessment.",
        "clinical_indication": "Bleeding severity monitoring",
        "priority": PRIORITY_ESSENTIAL,
        "sort_order": 10,
    },
    {
        "diagnosis_name": "Upper gastrointestinal bleeding",
        "category": CATEGORY_REFERRAL,
        "description_template": "Urgent gastroenterology/endoscopy referral if ongoing bleeding or instability.",
        "clinical_indication": "Escalation for endoscopic haemostasis",
        "priority": PRIORITY_ESSENTIAL,
        "sort_order": 15,
    },
    {
        "diagnosis_name": "Acute coronary syndrome",
        "category": CATEGORY_REFERRAL,
        "description_template": "Urgent cardiology assessment — must-not-miss alternative in epigastric pain.",
        "clinical_indication": "Cardiac cause exclusion/management",
        "priority": PRIORITY_ESSENTIAL,
        "sort_order": 5,
    },
    {
        "diagnosis_name": "Acute coronary syndrome",
        "category": CATEGORY_SAFETY,
        "description_template": "Do not attribute epigastric pain to GI cause until cardiac evaluation addressed where indicated.",
        "clinical_indication": "Diagnostic safety",
        "priority": PRIORITY_ESSENTIAL,
        "sort_order": 10,
    },
]


def seed_management_rules_if_empty(specialty_code: str = DEFAULT_SPECIALTY) -> int:
    if ManagementPlanRule.query.first() is not None:
        return 0

    for item in RULES:
        db.session.add(
            ManagementPlanRule(
                diagnosis_name=item["diagnosis_name"],
                complaint_code=item.get("complaint_code"),
                category=item["category"],
                description_template=item["description_template"],
                clinical_indication=item.get("clinical_indication"),
                priority=item.get("priority", PRIORITY_RECOMMENDED),
                knowledge_topic_key=item.get("knowledge_topic_key"),
                knowledge_stable_id=item.get("knowledge_stable_id"),
                guideline_reference=item.get("guideline_reference"),
                sort_order=item.get("sort_order", 100),
                specialty_code=specialty_code,
                department_id=1,
            )
        )
    db.session.commit()
    return len(RULES)
