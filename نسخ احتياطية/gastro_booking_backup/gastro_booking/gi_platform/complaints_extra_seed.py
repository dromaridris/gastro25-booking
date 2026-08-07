"""Extra GI complaints + symptom-specific trained questions seed."""

from __future__ import annotations

import json

EXTRA_COMPLAINTS = [
    {
        'slug': 'kl.complaint.abdominal_distension',
        'title': 'Abdominal distension',
        'complaint_code': 'hist.abdominal_distension',
        'category': 'luminal',
        'sort_order': 45,
    },
    {
        'slug': 'kl.complaint.loose_stools',
        'title': 'Loose stools / diarrhoea',
        'complaint_code': 'hist.loose_stools',
        'category': 'luminal',
        'sort_order': 46,
    },
]

DISTENSION_QUESTIONS = [
    ('gh.dist.onset', 'When did abdominal distension start?', 'history_of_present_illness', 'choice', ['Hours', 'Days', 'Weeks', 'Months'], True, 10),
    ('gh.dist.progression', 'Is distension increasing?', 'associated_symptoms', 'boolean', ['Yes', 'No'], True, 20),
    ('gh.dist.pain', 'Associated abdominal pain?', 'associated_symptoms', 'boolean', ['Yes', 'No'], True, 30),
    ('gh.dist.bowel', 'Change in bowel habit?', 'associated_symptoms', 'boolean', ['Yes', 'No'], False, 40),
    ('gh.dist.vomit', 'Vomiting present?', 'red_flags', 'boolean', ['Yes', 'No'], True, 50),
    ('gh.dist.fever', 'Fever?', 'red_flags', 'boolean', ['Yes', 'No'], False, 60),
]

LOOSE_STOOL_QUESTIONS = [
    ('gh.loose.onset', 'When did loose stools start?', 'history_of_present_illness', 'choice', ['Hours', 'Days', 'Weeks', 'Months'], True, 10),
    ('gh.loose.frequency', 'Bowel frequency per day?', 'history_of_present_illness', 'choice', ['1-3', '4-6', '7-10', '>10'], True, 20),
    ('gh.loose.blood', 'Blood in stool?', 'red_flags', 'boolean', ['Yes', 'No'], True, 30),
    ('gh.loose.dehydration', 'Signs of dehydration (thirst, dizziness)?', 'red_flags', 'boolean', ['Yes', 'No'], True, 40),
    ('gh.loose.travel', 'Recent travel or food exposure?', 'associated_symptoms', 'boolean', ['Yes', 'No'], False, 50),
    ('gh.loose.antibiotics', 'Recent antibiotic use?', 'associated_symptoms', 'boolean', ['Yes', 'No'], False, 60),
]


def seed_extra_complaints_if_missing(db) -> int:
    added = 0
    for item in EXTRA_COMPLAINTS:
        row = db.execute(
            'SELECT id FROM gi_knowledge_object WHERE slug = ?', (item['slug'],),
        ).fetchone()
        if row:
            continue
        db.execute(
            """
            INSERT INTO gi_knowledge_object (slug, title, object_type, status, body_json)
            VALUES (?, ?, 'complaint', 'published', ?)
            """,
            (
                item['slug'], item['title'],
                json.dumps({
                    'complaint_code': item['complaint_code'],
                    'category': item['category'],
                    'sort_order': item['sort_order'],
                }),
            ),
        )
        added += 1
    if added:
        db.commit()
    return added


def seed_symptom_training_questions(db) -> int:
    """Add trained questions for distension and loose stools if not present."""
    from gi_platform.history_ai_training import service as training

    count = 0
    for qid, text, cat, qtype, opts, required, priority in DISTENSION_QUESTIONS + LOOSE_STOOL_QUESTIONS:
        if training.get_trained_question(db, qid):
            continue
        training.create_question(
            db, question_id=qid, question_text=text, category=cat,
            question_type=qtype, answer_options=opts, is_required=required, priority=priority,
        )
        count += 1

    rules_map = {
        'hist.abdominal_distension': [q[0] for q in DISTENSION_QUESTIONS],
        'hist.loose_stools': [q[0] for q in LOOSE_STOOL_QUESTIONS],
    }
    sort = 10
    for code, qids in rules_map.items():
        for qid in qids:
            existing = db.execute(
                """
                SELECT id FROM gi_guided_history_question_rule
                WHERE complaint_code = ? AND question_id = ?
                """,
                (code, qid),
            ).fetchone()
            if existing:
                continue
            training.add_complaint_rule(db, complaint_code=code, question_id=qid, sort_order=sort)
            sort += 10
            count += 1
    return count
