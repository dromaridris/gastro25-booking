"""Default guided history question configuration seed."""

from __future__ import annotations

import json

from app.extensions import db
from app.modules.clinical_history_ai.constants import (
    CATEGORY_ASSOCIATED_SYMPTOMS,
    CATEGORY_HPI,
    CATEGORY_MEDICATION,
    CATEGORY_NEGATIVE_FINDINGS,
    CATEGORY_PMH,
    CATEGORY_RED_FLAGS,
    CATEGORY_SOCIAL,
    QUESTION_TYPE_BOOLEAN,
    QUESTION_TYPE_CHOICE,
    QUESTION_TYPE_TEXT,
)
from app.modules.clinical_history_ai.models import GuidedHistoryQuestion, GuidedHistoryQuestionRule

DEFAULT_SPECIALTY = "gastroenterology"

QUESTIONS = [
    {
        "question_id": "gh.q.onset",
        "question_text": "When did the symptom start?",
        "category": CATEGORY_HPI,
        "clinical_purpose": "Establish symptom onset",
        "question_type": QUESTION_TYPE_CHOICE,
        "answer_options": ["Hours", "Days", "Weeks", "Months"],
        "is_required": True,
        "priority": 10,
    },
    {
        "question_id": "gh.q.severity",
        "question_text": "How severe is the symptom?",
        "category": CATEGORY_HPI,
        "clinical_purpose": "Symptom severity",
        "question_type": QUESTION_TYPE_CHOICE,
        "answer_options": ["Mild", "Moderate", "Severe"],
        "is_required": True,
        "priority": 20,
    },
    {
        "question_id": "gh.q.radiation",
        "question_text": "Does the pain radiate?",
        "category": CATEGORY_ASSOCIATED_SYMPTOMS,
        "clinical_purpose": "Associated radiation pattern",
        "question_type": QUESTION_TYPE_BOOLEAN,
        "answer_options": ["Yes", "No"],
        "is_required": False,
        "priority": 30,
        "conditional_rules": {"show_when": [{"question_id": "gh.q.severity", "answer_in": ["Moderate", "Severe"]}]},
    },
    {
        "question_id": "gh.q.radiation_site",
        "question_text": "Where does the pain radiate to?",
        "category": CATEGORY_ASSOCIATED_SYMPTOMS,
        "clinical_purpose": "Radiation destination",
        "question_type": QUESTION_TYPE_TEXT,
        "is_required": False,
        "priority": 40,
        "conditional_rules": {"show_when": [{"question_id": "gh.q.radiation", "answer_equals": "yes"}]},
    },
    {
        "question_id": "gh.q.weight_loss",
        "question_text": "Any unintentional weight loss?",
        "category": CATEGORY_RED_FLAGS,
        "clinical_purpose": "Red flag screening",
        "question_type": QUESTION_TYPE_BOOLEAN,
        "answer_options": ["Yes", "No"],
        "is_required": True,
        "priority": 50,
    },
    {
        "question_id": "gh.q.vomiting_blood",
        "question_text": "Any vomiting of blood?",
        "category": CATEGORY_RED_FLAGS,
        "clinical_purpose": "Red flag screening",
        "question_type": QUESTION_TYPE_BOOLEAN,
        "answer_options": ["Yes", "No"],
        "is_required": True,
        "priority": 60,
    },
    {
        "question_id": "gh.q.prior_similar",
        "question_text": "Any prior similar episodes?",
        "category": CATEGORY_PMH,
        "clinical_purpose": "Prior episode context",
        "question_type": QUESTION_TYPE_BOOLEAN,
        "answer_options": ["Yes", "No"],
        "is_required": False,
        "priority": 70,
    },
    {
        "question_id": "gh.q.current_medications",
        "question_text": "Current regular medications?",
        "category": CATEGORY_MEDICATION,
        "clinical_purpose": "Medication history",
        "question_type": QUESTION_TYPE_TEXT,
        "is_required": False,
        "priority": 80,
    },
    {
        "question_id": "gh.q.nsaid_use",
        "question_text": "Recent NSAID use?",
        "category": CATEGORY_MEDICATION,
        "clinical_purpose": "Medication risk factor",
        "question_type": QUESTION_TYPE_BOOLEAN,
        "answer_options": ["Yes", "No"],
        "is_required": False,
        "priority": 90,
        "conditional_rules": {"hide_when": [{"question_id": "gh.q.current_medications", "answer_equals": ""}]},
    },
    {
        "question_id": "gh.q.alcohol",
        "question_text": "Alcohol use?",
        "category": CATEGORY_SOCIAL,
        "clinical_purpose": "Social history",
        "question_type": QUESTION_TYPE_CHOICE,
        "answer_options": ["None", "Occasional", "Regular", "Heavy"],
        "is_required": False,
        "priority": 100,
    },
    {
        "question_id": "gh.q.no_fever",
        "question_text": "No fever reported?",
        "category": CATEGORY_NEGATIVE_FINDINGS,
        "clinical_purpose": "Relevant negative",
        "question_type": QUESTION_TYPE_BOOLEAN,
        "answer_options": ["Yes", "No"],
        "is_required": False,
        "priority": 110,
    },
]

COMPLAINT_RULES = {
    "intake.cc.epigastric_pain": [
        "gh.q.onset",
        "gh.q.severity",
        "gh.q.radiation",
        "gh.q.radiation_site",
        "gh.q.weight_loss",
        "gh.q.vomiting_blood",
        "gh.q.prior_similar",
        "gh.q.current_medications",
        "gh.q.nsaid_use",
        "gh.q.alcohol",
        "gh.q.no_fever",
    ],
    "intake.cc.melena": [
        "gh.q.onset",
        "gh.q.severity",
        "gh.q.weight_loss",
        "gh.q.vomiting_blood",
        "gh.q.prior_similar",
        "gh.q.current_medications",
        "gh.q.alcohol",
    ],
}


def seed_guided_history_questions_if_empty(specialty_code: str = DEFAULT_SPECIALTY) -> int:
    if GuidedHistoryQuestion.query.first() is not None:
        return 0

    for item in QUESTIONS:
        db.session.add(
            GuidedHistoryQuestion(
                question_id=item["question_id"],
                question_text=item["question_text"],
                category=item["category"],
                clinical_purpose=item.get("clinical_purpose"),
                question_type=item["question_type"],
                answer_options_json=json.dumps(item.get("answer_options") or []),
                is_required=item.get("is_required", False),
                priority=item.get("priority", 100),
                conditional_rules_json=json.dumps(item.get("conditional_rules") or {}),
                knowledge_topic_key=item.get("knowledge_topic_key"),
                knowledge_stable_id=item.get("knowledge_stable_id"),
                specialty_code=specialty_code,
                department_id=1,
            )
        )

    sort = 10
    for complaint_code, question_ids in COMPLAINT_RULES.items():
        for question_id in question_ids:
            db.session.add(
                GuidedHistoryQuestionRule(
                    complaint_code=complaint_code,
                    question_id=question_id,
                    sort_order=sort,
                    specialty_code=specialty_code,
                    department_id=1,
                )
            )
            sort += 10

    db.session.commit()
    return len(QUESTIONS)
