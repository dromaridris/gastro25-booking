"""Diagnosis rule seed — SQLite."""

from __future__ import annotations

import json

DEFAULT_SPECIALTY = 'gastroenterology'

RULES = [
    {
        'complaint_code': 'hist.upper_gi_bleeding',
        'diagnosis_name': 'Upper gastrointestinal bleeding',
        'category': 'most_likely',
        'base_priority': 10,
        'base_confidence': 0.85,
        'inclusion_reason': 'Presentation compatible with upper GI blood loss.',
        'supporting_patterns': [{'question_id': 'gh.q.onset', 'answer_in': ['Hours', 'Days']}],
    },
    {
        'complaint_code': 'hist.upper_gi_bleeding',
        'diagnosis_name': 'Peptic ulcer bleeding',
        'category': 'important_alternative',
        'base_priority': 15,
        'base_confidence': 0.72,
        'inclusion_reason': 'Common source of UGIB.',
        'supporting_patterns': [{'question_id': 'gh.q.vomiting_blood', 'answer_equals': 'yes'}],
    },
    {
        'complaint_code': 'hist.upper_gi_bleeding',
        'diagnosis_name': 'Variceal haemorrhage',
        'category': 'must_not_miss',
        'base_priority': 5,
        'base_confidence': 0.55,
        'inclusion_reason': 'Must-not-miss in at-risk patients.',
        'supporting_patterns': [{'question_id': 'gh.q.alcohol', 'answer_in': ['Regular', 'Heavy']}],
    },
    {
        'complaint_code': 'hist.abdominal_pain',
        'diagnosis_name': 'Peptic ulcer disease',
        'category': 'most_likely',
        'base_priority': 10,
        'base_confidence': 0.78,
        'inclusion_reason': 'Epigastric pain pattern.',
        'supporting_patterns': [{'question_id': 'gh.q.severity', 'answer_in': ['Moderate', 'Severe']}],
    },
    {
        'complaint_code': 'hist.diarrhea',
        'diagnosis_name': 'Infectious gastroenteritis',
        'category': 'most_likely',
        'base_priority': 10,
        'base_confidence': 0.7,
        'inclusion_reason': 'Acute diarrhoeal illness is commonly infectious.',
        'supporting_patterns': [{'question_id': 'gh.q.onset', 'answer_in': ['Hours', 'Days']}],
    },
    {
        'complaint_code': 'hist.jaundice',
        'diagnosis_name': 'Obstructive jaundice',
        'category': 'most_likely',
        'base_priority': 10,
        'base_confidence': 0.68,
        'inclusion_reason': 'Jaundice presentation — consider biliary obstruction.',
        'supporting_patterns': [],
    },
    {
        'complaint_code': 'hist.dysphagia',
        'diagnosis_name': 'Oesophageal dysphagia — structural vs motility',
        'category': 'most_likely',
        'base_priority': 10,
        'base_confidence': 0.65,
        'inclusion_reason': 'Dysphagia requires structural and motility differentials.',
        'supporting_patterns': [],
    },
]


def seed_diagnosis_rules_if_empty(db) -> int:
    """Insert default diagnosis rules; also backfill any missing complaint/dx pairs."""
    inserted = 0
    for item in RULES:
        exists = db.execute(
            """
            SELECT id FROM gi_diagnosis_rule
            WHERE complaint_code = ? AND diagnosis_name = ?
            """,
            (item['complaint_code'], item['diagnosis_name']),
        ).fetchone()
        if exists:
            continue
        db.execute(
            """
            INSERT INTO gi_diagnosis_rule (
                complaint_code, diagnosis_name, category, base_priority, base_confidence,
                inclusion_reason, supporting_patterns_json, missing_patterns_json,
                contradicting_patterns_json, specialty_code
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                item['complaint_code'], item['diagnosis_name'], item['category'],
                item['base_priority'], item['base_confidence'],
                item.get('inclusion_reason'),
                json.dumps(item.get('supporting_patterns') or []),
                json.dumps(item.get('missing_patterns') or []),
                json.dumps(item.get('contradicting_patterns') or []),
                DEFAULT_SPECIALTY,
            ),
        )
        inserted += 1
    if inserted:
        db.commit()
    return inserted
