"""Default differential rule seed — configurable data, not hardcoded engine logic."""

from __future__ import annotations

import json

from app.extensions import db
from app.modules.clinical_assessment.models import DiagnosisRuleDefinition

DEFAULT_SPECIALTY = "gastroenterology"

RULES = [
    {
        "complaint_code": "intake.cc.epigastric_pain",
        "diagnosis_name": "Peptic ulcer disease",
        "category": "most_likely",
        "base_priority": 10,
        "base_confidence": 0.78,
        "inclusion_reason": "Epigastric pain with subacute onset is compatible with peptic ulcer disease.",
        "supporting_patterns": [
            {"question_id": "gh.q.onset", "answer_in": ["Days", "Weeks"]},
            {"question_id": "gh.q.severity", "answer_in": ["Moderate", "Severe"]},
        ],
        "missing_patterns": [{"question_id": "gh.q.nsaid_use", "answer_equals": ""}],
        "knowledge_topic_key": "kl.epigastric.overview",
    },
    {
        "complaint_code": "intake.cc.epigastric_pain",
        "diagnosis_name": "Gastro-oesophageal reflux disease",
        "category": "important_alternative",
        "base_priority": 20,
        "base_confidence": 0.65,
        "inclusion_reason": "Burning epigastric discomfort may represent reflux-related symptoms.",
        "supporting_patterns": [{"question_id": "gh.q.onset", "answer_in": ["Days", "Weeks", "Months"]}],
    },
    {
        "complaint_code": "intake.cc.epigastric_pain",
        "diagnosis_name": "Acute coronary syndrome",
        "category": "must_not_miss",
        "base_priority": 5,
        "base_confidence": 0.4,
        "inclusion_reason": "Cardiac causes must be considered in upper abdominal pain presentations.",
        "supporting_patterns": [{"question_id": "gh.q.radiation", "answer_equals": "yes"}],
        "missing_patterns": [{"question_id": "gh.q.radiation", "answer_equals": ""}],
    },
    {
        "complaint_code": "intake.cc.epigastric_pain",
        "diagnosis_name": "Functional dyspepsia",
        "category": "less_likely",
        "base_priority": 80,
        "base_confidence": 0.35,
        "inclusion_reason": "Consider when alarm features are absent and symptoms are chronic.",
        "supporting_patterns": [{"question_id": "gh.q.weight_loss", "answer_equals": "no"}],
    },
    {
        "complaint_code": "intake.cc.melena",
        "diagnosis_name": "Upper gastrointestinal bleeding",
        "category": "most_likely",
        "base_priority": 10,
        "base_confidence": 0.85,
        "inclusion_reason": "Melena indicates possible upper GI blood loss.",
        "supporting_patterns": [{"question_id": "gh.q.onset", "answer_in": ["Hours", "Days"]}],
    },
    {
        "complaint_code": "intake.cc.melena",
        "diagnosis_name": "Peptic ulcer bleeding",
        "category": "important_alternative",
        "base_priority": 15,
        "base_confidence": 0.72,
        "inclusion_reason": "Peptic ulceration is a common source of upper GI bleeding.",
        "supporting_patterns": [{"question_id": "gh.q.nsaid_use", "answer_equals": "yes"}],
    },
    {
        "complaint_code": "intake.cc.melena",
        "diagnosis_name": "Variceal haemorrhage",
        "category": "must_not_miss",
        "base_priority": 5,
        "base_confidence": 0.55,
        "inclusion_reason": "Must-not-miss cause of upper GI bleeding in at-risk patients.",
        "missing_patterns": [{"question_id": "gh.q.alcohol", "answer_equals": ""}],
    },
]


def seed_diagnosis_rules_if_empty(specialty_code: str = DEFAULT_SPECIALTY) -> int:
    if DiagnosisRuleDefinition.query.first() is not None:
        return 0

    for item in RULES:
        db.session.add(
            DiagnosisRuleDefinition(
                complaint_code=item["complaint_code"],
                diagnosis_name=item["diagnosis_name"],
                category=item["category"],
                base_priority=item["base_priority"],
                base_confidence=item["base_confidence"],
                inclusion_reason=item.get("inclusion_reason"),
                supporting_patterns_json=json.dumps(item.get("supporting_patterns") or []),
                missing_patterns_json=json.dumps(item.get("missing_patterns") or []),
                contradicting_patterns_json=json.dumps(item.get("contradicting_patterns") or []),
                knowledge_topic_key=item.get("knowledge_topic_key"),
                knowledge_stable_id=item.get("knowledge_stable_id"),
                specialty_code=specialty_code,
                department_id=1,
            )
        )
    db.session.commit()
    return len(RULES)
