"""Management plan rules seed — Gastro25 SQLite."""

from __future__ import annotations

from gi_platform.management_plan_ai.constants import (
    CATEGORY_FOLLOW_UP, CATEGORY_MONITORING, CATEGORY_PATIENT_EDUCATION,
    CATEGORY_REFERRAL, CATEGORY_SAFETY, CATEGORY_TREATMENT,
    PRIORITY_ESSENTIAL, PRIORITY_RECOMMENDED,
)

DEFAULT_SPECIALTY = 'gastroenterology'

RULES = [
    {
        'diagnosis_name': 'Peptic ulcer bleeding',
        'complaint_code': 'hist.upper_gi_bleeding',
        'category': CATEGORY_TREATMENT,
        'description_template': (
            'Consider acid suppression pathway (e.g. PPI class) per local guideline — '
            'physician to select agent and dosing. Do not auto-prescribe.'
        ),
        'clinical_indication': 'Suspected or confirmed peptic ulcer bleeding',
        'priority': PRIORITY_ESSENTIAL,
        'guideline_reference': 'Acid suppression for peptic ulcer disease',
        'sort_order': 10,
    },
    {
        'diagnosis_name': 'Peptic ulcer bleeding',
        'category': CATEGORY_MONITORING,
        'description_template': 'Monitor haemoglobin trend, haemodynamic status, and rebleeding signs.',
        'clinical_indication': 'Bleeding severity monitoring',
        'priority': PRIORITY_ESSENTIAL,
        'sort_order': 20,
    },
    {
        'diagnosis_name': 'Peptic ulcer bleeding',
        'category': CATEGORY_REFERRAL,
        'description_template': 'Urgent gastroenterology/endoscopy referral if ongoing bleeding or instability.',
        'clinical_indication': 'Escalation for endoscopic haemostasis',
        'priority': PRIORITY_ESSENTIAL,
        'sort_order': 15,
    },
    {
        'diagnosis_name': 'Peptic ulcer bleeding',
        'category': CATEGORY_PATIENT_EDUCATION,
        'description_template': 'Educate on NSAID avoidance and when to seek urgent care for bleeding symptoms.',
        'clinical_indication': 'Patient self-management support',
        'priority': PRIORITY_RECOMMENDED,
        'sort_order': 40,
    },
    {
        'diagnosis_name': 'Upper gastrointestinal bleeding',
        'complaint_code': 'hist.upper_gi_bleeding',
        'category': CATEGORY_TREATMENT,
        'description_template': (
            'Resuscitation and haemostasis pathway per local UGI bleeding protocol — '
            'physician-directed; no automatic treatment orders.'
        ),
        'clinical_indication': 'Active or recent upper GI bleeding',
        'priority': PRIORITY_ESSENTIAL,
        'guideline_reference': 'UGI bleeding management protocol',
        'sort_order': 5,
    },
    {
        'diagnosis_name': 'Upper gastrointestinal bleeding',
        'category': CATEGORY_MONITORING,
        'description_template': 'Serial haemoglobin, haemodynamic monitoring, and transfusion threshold assessment.',
        'clinical_indication': 'Bleeding severity monitoring',
        'priority': PRIORITY_ESSENTIAL,
        'sort_order': 10,
    },
    {
        'diagnosis_name': 'Upper gastrointestinal bleeding',
        'category': CATEGORY_SAFETY,
        'description_template': 'Review anticoagulant/antiplatelet use and bleeding risk with patient context.',
        'clinical_indication': 'Bleeding risk mitigation',
        'priority': PRIORITY_ESSENTIAL,
        'sort_order': 12,
    },
    {
        'diagnosis_name': 'Peptic ulcer disease',
        'complaint_code': 'hist.abdominal_pain',
        'category': CATEGORY_TREATMENT,
        'description_template': (
            'Consider acid suppression therapy pathway per local guideline — physician to select therapy.'
        ),
        'clinical_indication': 'Suspected or confirmed peptic ulcer disease',
        'priority': PRIORITY_ESSENTIAL,
        'sort_order': 10,
    },
    {
        'diagnosis_name': 'Peptic ulcer disease',
        'category': CATEGORY_FOLLOW_UP,
        'description_template': 'Arrange follow-up to assess symptom response and review need for endoscopy.',
        'clinical_indication': 'Structured follow-up after initial management',
        'priority': PRIORITY_RECOMMENDED,
        'sort_order': 30,
    },
]


def seed_management_rules_if_empty(db) -> int:
    row = db.execute('SELECT COUNT(*) AS c FROM gi_management_plan_rule').fetchone()
    if row['c'] > 0:
        return 0
    for item in RULES:
        db.execute(
            """
            INSERT INTO gi_management_plan_rule (
                diagnosis_name, complaint_code, category, description_template,
                clinical_indication, priority, knowledge_topic_key, knowledge_stable_id,
                guideline_reference, sort_order, specialty_code
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                item['diagnosis_name'], item.get('complaint_code'), item['category'],
                item['description_template'], item.get('clinical_indication'),
                item.get('priority', PRIORITY_RECOMMENDED),
                item.get('knowledge_topic_key'), item.get('knowledge_stable_id'),
                item.get('guideline_reference'), item.get('sort_order', 100),
                DEFAULT_SPECIALTY,
            ),
        )
    db.commit()
    return len(RULES)
