"""Default follow-up recommendation rules seed."""

from __future__ import annotations

from app.extensions import db
from app.modules.patient_journey.models import FollowUpRecommendationRule

DEFAULT_SPECIALTY = "gastroenterology"

RULES = [
    {
        "diagnosis_name": "Peptic ulcer disease",
        "related_condition": "Peptic ulcer disease",
        "interval_days": 56,
        "interval_text": "8 weeks",
        "reason_template": "Review symptom response and assess need for repeat endoscopy.",
        "knowledge_topic_key": "kl.epigastric.overview",
        "sort_order": 10,
    },
    {
        "diagnosis_name": "Gastro-oesophageal reflux disease",
        "related_condition": "Gastro-oesophageal reflux disease",
        "interval_days": 28,
        "interval_text": "4 weeks",
        "reason_template": "Assess response to acid suppression and lifestyle measures.",
        "sort_order": 20,
    },
    {
        "diagnosis_name": "Upper gastrointestinal bleeding",
        "related_condition": "Upper gastrointestinal bleeding",
        "interval_days": 14,
        "interval_text": "2 weeks",
        "reason_template": "Monitor haemoglobin recovery and review for re-bleeding.",
        "knowledge_topic_key": "kl.epigastric.overview",
        "sort_order": 5,
    },
]


def seed_follow_up_rules_if_empty(specialty_code: str = DEFAULT_SPECIALTY) -> int:
    if FollowUpRecommendationRule.query.first() is not None:
        return 0

    for item in RULES:
        db.session.add(
            FollowUpRecommendationRule(
                diagnosis_name=item.get("diagnosis_name"),
                related_condition=item.get("related_condition"),
                interval_days=item.get("interval_days"),
                interval_text=item.get("interval_text"),
                reason_template=item.get("reason_template"),
                knowledge_topic_key=item.get("knowledge_topic_key"),
                knowledge_stable_id=item.get("knowledge_stable_id"),
                specialty_code=specialty_code,
                sort_order=item.get("sort_order", 100),
                department_id=1,
            )
        )
    db.session.commit()
    return len(RULES)
