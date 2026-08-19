"""Investigation library + recommendation rules seed — Gastro25 SQLite."""

from __future__ import annotations

import json

from gi_platform.investigation_planning.constants import (
    CATEGORY_ENDOSCOPY, CATEGORY_IMAGING, CATEGORY_LABORATORY,
    GROUP_CONFIRM, GROUP_EXCLUDE, GROUP_INITIAL, GROUP_SEVERITY,
    PRIORITY_ESSENTIAL, PRIORITY_RECOMMENDED,
)

DEFAULT_SPECIALTY = 'gastroenterology'

LIBRARY = [
    {
        'investigation_id': 'inv.lab.hb',
        'name': 'Full blood count',
        'category': CATEGORY_LABORATORY,
        'catalogue_code': 'lab.hb',
        'indications': ['Anaemia assessment', 'Bleeding work-up'],
        'related_diagnosis_concepts': ['Upper gastrointestinal bleeding', 'Peptic ulcer bleeding'],
    },
    {
        'investigation_id': 'inv.lab.crp',
        'name': 'CRP',
        'category': CATEGORY_LABORATORY,
        'catalogue_code': 'lab.crp',
        'indications': ['Inflammation assessment'],
        'related_diagnosis_concepts': ['Peptic ulcer disease'],
    },
    {
        'investigation_id': 'inv.lab.lft',
        'name': 'Liver function tests',
        'category': CATEGORY_LABORATORY,
        'catalogue_code': 'lab.alt',
        'indications': ['Hepatobiliary assessment'],
        'related_diagnosis_concepts': ['Variceal haemorrhage'],
    },
    {
        'investigation_id': 'inv.endoscopy.egd',
        'name': 'Upper GI endoscopy',
        'category': CATEGORY_ENDOSCOPY,
        'catalogue_code': None,
        'indications': ['Evaluate upper GI bleeding', 'Assess epigastric pain alarm features'],
        'related_diagnosis_concepts': ['Peptic ulcer bleeding', 'Upper gastrointestinal bleeding'],
    },
    {
        'investigation_id': 'inv.imaging.abdominal_us',
        'name': 'Abdominal ultrasound',
        'category': CATEGORY_IMAGING,
        'catalogue_code': 'img.abdominal_us',
        'indications': ['Biliary assessment', 'Exclude alternative causes'],
        'related_diagnosis_concepts': ['Peptic ulcer disease'],
    },
]

RULES = [
    {
        'complaint_code': 'hist.abdominal_pain',
        'diagnosis_name': 'Peptic ulcer disease',
        'investigation_id': 'inv.lab.hb',
        'workup_group': GROUP_INITIAL,
        'priority': PRIORITY_ESSENTIAL,
        'reason_template': 'Assess for anaemia in epigastric pain presentation.',
        'related_diagnosis': 'Peptic ulcer disease',
        'missing_info_addressed': 'Baseline haematology',
    },
    {
        'complaint_code': 'hist.abdominal_pain',
        'diagnosis_name': 'Peptic ulcer disease',
        'investigation_id': 'inv.endoscopy.egd',
        'workup_group': GROUP_CONFIRM,
        'priority': PRIORITY_ESSENTIAL,
        'reason_template': 'Confirm mucosal source in suspected peptic ulcer disease.',
        'related_diagnosis': 'Peptic ulcer disease',
    },
    {
        'complaint_code': 'hist.abdominal_pain',
        'diagnosis_name': 'Peptic ulcer disease',
        'investigation_id': 'inv.imaging.abdominal_us',
        'workup_group': GROUP_EXCLUDE,
        'priority': PRIORITY_RECOMMENDED,
        'reason_template': 'Exclude biliary alternative in upper abdominal pain.',
        'related_diagnosis': 'Peptic ulcer disease',
    },
    {
        'complaint_code': 'hist.upper_gi_bleeding',
        'diagnosis_name': 'Upper gastrointestinal bleeding',
        'investigation_id': 'inv.lab.hb',
        'workup_group': GROUP_INITIAL,
        'priority': PRIORITY_ESSENTIAL,
        'reason_template': 'Assess severity of possible GI blood loss.',
        'related_diagnosis': 'Upper gastrointestinal bleeding',
    },
    {
        'complaint_code': 'hist.upper_gi_bleeding',
        'diagnosis_name': 'Upper gastrointestinal bleeding',
        'investigation_id': 'inv.endoscopy.egd',
        'workup_group': GROUP_SEVERITY,
        'priority': PRIORITY_ESSENTIAL,
        'reason_template': 'Identify and risk-stratify upper GI bleeding source.',
        'related_diagnosis': 'Upper gastrointestinal bleeding',
    },
    {
        'complaint_code': 'hist.upper_gi_bleeding',
        'diagnosis_name': 'Peptic ulcer bleeding',
        'investigation_id': 'inv.lab.lft',
        'workup_group': GROUP_INITIAL,
        'priority': PRIORITY_RECOMMENDED,
        'reason_template': 'Assess liver function if variceal bleed is possible.',
        'related_diagnosis': 'Peptic ulcer bleeding',
    },
]


def seed_investigation_library_if_empty(db) -> int:
    row = db.execute('SELECT COUNT(*) AS c FROM gi_investigation_library_entry').fetchone()
    if row['c'] > 0:
        return 0
    for item in LIBRARY:
        db.execute(
            """
            INSERT INTO gi_investigation_library_entry (
                investigation_id, name, category, catalogue_code,
                indications_json, related_diagnosis_concepts_json, specialty_code
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                item['investigation_id'], item['name'], item['category'], item.get('catalogue_code'),
                json.dumps(item.get('indications') or []),
                json.dumps(item.get('related_diagnosis_concepts') or []),
                DEFAULT_SPECIALTY,
            ),
        )
    sort = 10
    for rule in RULES:
        db.execute(
            """
            INSERT INTO gi_investigation_recommendation_rule (
                complaint_code, diagnosis_name, investigation_id, workup_group, priority,
                reason_template, related_diagnosis, missing_info_addressed, sort_order, specialty_code
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                rule.get('complaint_code'), rule.get('diagnosis_name'), rule['investigation_id'],
                rule['workup_group'], rule['priority'], rule.get('reason_template'),
                rule.get('related_diagnosis'), rule.get('missing_info_addressed'), sort, DEFAULT_SPECIALTY,
            ),
        )
        sort += 10
    db.commit()
    return len(LIBRARY)
