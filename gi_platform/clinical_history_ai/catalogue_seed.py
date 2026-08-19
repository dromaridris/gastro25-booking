"""Default guided history question seed — SQLite."""

from __future__ import annotations

import json

from gi_platform.clinical_history_ai.constants import (
    CATEGORY_ASSOCIATED_SYMPTOMS,
    CATEGORY_HPI,
    CATEGORY_MEDICATION,
    CATEGORY_NEGATIVE_FINDINGS,
    CATEGORY_PMH,
    CATEGORY_RED_FLAGS,
    CATEGORY_SOCIAL,
    DEFAULT_COMPLAINT,
    QUESTION_TYPE_BOOLEAN,
    QUESTION_TYPE_CHOICE,
    QUESTION_TYPE_TEXT,
)

DEFAULT_SPECIALTY = 'gastroenterology'

QUESTIONS = [
    {
        'question_id': 'gh.q.onset',
        'question_text': 'When did the symptom start?',
        'category': CATEGORY_HPI,
        'clinical_purpose': 'Establish symptom onset',
        'question_type': QUESTION_TYPE_CHOICE,
        'answer_options': ['Hours', 'Days', 'Weeks', 'Months'],
        'is_required': True,
        'priority': 10,
    },
    {
        'question_id': 'gh.q.severity',
        'question_text': 'How severe is the symptom?',
        'category': CATEGORY_HPI,
        'clinical_purpose': 'Symptom severity',
        'question_type': QUESTION_TYPE_CHOICE,
        'answer_options': ['Mild', 'Moderate', 'Severe'],
        'is_required': True,
        'priority': 20,
    },
    {
        'question_id': 'gh.q.radiation',
        'question_text': 'Does the pain radiate?',
        'category': CATEGORY_ASSOCIATED_SYMPTOMS,
        'question_type': QUESTION_TYPE_BOOLEAN,
        'answer_options': ['Yes', 'No'],
        'priority': 30,
        'conditional_rules': {'show_when': [{'question_id': 'gh.q.severity', 'answer_in': ['Moderate', 'Severe']}]},
    },
    {
        'question_id': 'gh.q.weight_loss',
        'question_text': 'Any unintentional weight loss?',
        'category': CATEGORY_RED_FLAGS,
        'question_type': QUESTION_TYPE_BOOLEAN,
        'answer_options': ['Yes', 'No'],
        'is_required': True,
        'priority': 50,
    },
    {
        'question_id': 'gh.q.vomiting_blood',
        'question_text': 'Any vomiting of blood?',
        'category': CATEGORY_RED_FLAGS,
        'question_type': QUESTION_TYPE_BOOLEAN,
        'answer_options': ['Yes', 'No'],
        'is_required': True,
        'priority': 60,
    },
    {
        'question_id': 'gh.q.prior_similar',
        'question_text': 'Any prior similar episodes?',
        'category': CATEGORY_PMH,
        'question_type': QUESTION_TYPE_BOOLEAN,
        'answer_options': ['Yes', 'No'],
        'priority': 70,
    },
    {
        'question_id': 'gh.q.current_medications',
        'question_text': 'Current regular medications?',
        'category': CATEGORY_MEDICATION,
        'question_type': QUESTION_TYPE_TEXT,
        'priority': 80,
    },
    {
        'question_id': 'gh.q.alcohol',
        'question_text': 'Alcohol use?',
        'category': CATEGORY_SOCIAL,
        'question_type': QUESTION_TYPE_CHOICE,
        'answer_options': ['None', 'Occasional', 'Regular', 'Heavy'],
        'priority': 100,
    },
    {
        'question_id': 'gh.q.no_fever',
        'question_text': 'No fever reported?',
        'category': CATEGORY_NEGATIVE_FINDINGS,
        'question_type': QUESTION_TYPE_BOOLEAN,
        'answer_options': ['Yes', 'No'],
        'priority': 110,
    },
]

COMPLAINT_RULES: dict[str, list[str]] = {
    DEFAULT_COMPLAINT: [q['question_id'] for q in QUESTIONS],
    'hist.abdominal_pain': [q['question_id'] for q in QUESTIONS],
    'hist.upper_gi_bleeding': [
        'gh.q.onset', 'gh.q.severity', 'gh.q.weight_loss', 'gh.q.vomiting_blood',
        'gh.q.prior_similar', 'gh.q.current_medications', 'gh.q.alcohol',
    ],
    'hist.lower_gi_bleeding': [
        'gh.q.onset', 'gh.q.severity', 'gh.q.weight_loss', 'gh.q.prior_similar',
        'gh.q.current_medications', 'gh.q.alcohol',
    ],
    'intake.cc.epigastric_pain': [q['question_id'] for q in QUESTIONS],
    'intake.cc.melena': [
        'gh.q.onset', 'gh.q.severity', 'gh.q.weight_loss', 'gh.q.vomiting_blood',
        'gh.q.prior_similar', 'gh.q.current_medications', 'gh.q.alcohol',
    ],
}


def seed_guided_history_questions_if_empty(db) -> int:
    row = db.execute('SELECT COUNT(*) AS c FROM gi_guided_history_question').fetchone()
    if row['c'] > 0:
        return 0

    for item in QUESTIONS:
        db.execute(
            """
            INSERT INTO gi_guided_history_question (
                question_id, question_text, category, clinical_purpose, question_type,
                answer_options_json, is_required, priority, conditional_rules_json, specialty_code
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                item['question_id'], item['question_text'], item['category'],
                item.get('clinical_purpose'), item['question_type'],
                json.dumps(item.get('answer_options') or []),
                1 if item.get('is_required') else 0,
                item.get('priority', 100),
                json.dumps(item.get('conditional_rules') or {}),
                DEFAULT_SPECIALTY,
            ),
        )

    sort = 10
    for complaint_code, question_ids in COMPLAINT_RULES.items():
        for question_id in question_ids:
            db.execute(
                """
                INSERT INTO gi_guided_history_question_rule
                (complaint_code, question_id, sort_order, specialty_code)
                VALUES (?, ?, ?, ?)
                """,
                (complaint_code, question_id, sort, DEFAULT_SPECIALTY),
            )
            sort += 10

    db.commit()
    return len(QUESTIONS)
