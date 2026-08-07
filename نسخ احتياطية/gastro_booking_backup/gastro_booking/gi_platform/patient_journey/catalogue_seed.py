"""Follow-up recommendation rules seed — Gastro25."""

DEFAULT_SPECIALTY = 'gastroenterology'

RULES = [
    {
        'diagnosis_name': 'Peptic ulcer disease',
        'related_condition': 'Peptic ulcer disease',
        'interval_days': 56,
        'interval_text': '8 weeks',
        'reason_template': 'Review symptom response and assess need for repeat endoscopy.',
        'sort_order': 10,
    },
    {
        'diagnosis_name': 'Upper gastrointestinal bleeding',
        'related_condition': 'Upper gastrointestinal bleeding',
        'interval_days': 14,
        'interval_text': '2 weeks',
        'reason_template': 'Monitor haemoglobin recovery and review for re-bleeding.',
        'sort_order': 5,
    },
    {
        'diagnosis_name': 'Peptic ulcer bleeding',
        'related_condition': 'Peptic ulcer bleeding',
        'interval_days': 14,
        'interval_text': '2 weeks',
        'reason_template': 'Review response to haemostasis and acid suppression.',
        'sort_order': 8,
    },
]


def seed_follow_up_rules_if_empty(db) -> int:
    row = db.execute('SELECT COUNT(*) AS c FROM gi_follow_up_recommendation_rule').fetchone()
    if row['c'] > 0:
        return 0
    for item in RULES:
        db.execute(
            """
            INSERT INTO gi_follow_up_recommendation_rule (
                diagnosis_name, related_condition, interval_days, interval_text,
                reason_template, sort_order, specialty_code
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                item.get('diagnosis_name'), item.get('related_condition'),
                item.get('interval_days'), item.get('interval_text'),
                item.get('reason_template'), item.get('sort_order', 100), DEFAULT_SPECIALTY,
            ),
        )
    db.commit()
    return len(RULES)
