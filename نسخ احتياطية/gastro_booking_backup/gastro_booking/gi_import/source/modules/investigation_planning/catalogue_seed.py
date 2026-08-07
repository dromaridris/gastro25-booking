"""Default investigation library and recommendation rules seed."""

from __future__ import annotations

import json

from app.extensions import db
from app.modules.investigation_planning.constants import (
    CATEGORY_ENDOSCOPY,
    CATEGORY_IMAGING,
    CATEGORY_LABORATORY,
    GROUP_CONFIRM,
    GROUP_EXCLUDE,
    GROUP_INITIAL,
    GROUP_SEVERITY,
    PRIORITY_ESSENTIAL,
    PRIORITY_RECOMMENDED,
)
from app.modules.investigation_planning.models import (
    InvestigationLibraryEntry,
    InvestigationRecommendationRule,
)

DEFAULT_SPECIALTY = "gastroenterology"

LIBRARY = [
    {
        "investigation_id": "inv.lab.hb",
        "name": "Full blood count",
        "category": CATEGORY_LABORATORY,
        "catalogue_code": "lab.hb",
        "indications": ["Anaemia assessment", "Bleeding work-up"],
        "related_diagnosis_concepts": ["Upper gastrointestinal bleeding", "Peptic ulcer disease"],
        "knowledge_topic_key": "kl.epigastric.overview",
    },
    {
        "investigation_id": "inv.lab.crp",
        "name": "CRP",
        "category": CATEGORY_LABORATORY,
        "catalogue_code": "lab.crp",
        "indications": ["Inflammation assessment"],
        "related_diagnosis_concepts": ["Peptic ulcer disease"],
    },
    {
        "investigation_id": "inv.lab.lft",
        "name": "Liver function tests",
        "category": CATEGORY_LABORATORY,
        "catalogue_code": "lab.alt",
        "indications": ["Hepatobiliary assessment"],
        "related_diagnosis_concepts": ["Biliary colic"],
    },
    {
        "investigation_id": "inv.endoscopy.egd",
        "name": "Upper GI endoscopy",
        "category": CATEGORY_ENDOSCOPY,
        "catalogue_code": None,
        "indications": ["Evaluate upper GI bleeding", "Assess epigastric pain alarm features"],
        "related_diagnosis_concepts": ["Peptic ulcer disease", "Upper gastrointestinal bleeding"],
        "knowledge_topic_key": "kl.epigastric.overview",
    },
    {
        "investigation_id": "inv.imaging.abdominal_us",
        "name": "Abdominal ultrasound",
        "category": CATEGORY_IMAGING,
        "catalogue_code": "img.abdominal_us",
        "indications": ["Biliary assessment", "Exclude alternative causes"],
        "related_diagnosis_concepts": ["Biliary colic"],
    },
]

RULES = [
    {
        "complaint_code": "intake.cc.epigastric_pain",
        "diagnosis_name": "Peptic ulcer disease",
        "investigation_id": "inv.lab.hb",
        "workup_group": GROUP_INITIAL,
        "priority": PRIORITY_ESSENTIAL,
        "reason_template": "Assess for anaemia in epigastric pain presentation.",
        "related_diagnosis": "Peptic ulcer disease",
        "missing_info_addressed": "Baseline haematology",
    },
    {
        "complaint_code": "intake.cc.epigastric_pain",
        "diagnosis_name": "Peptic ulcer disease",
        "investigation_id": "inv.endoscopy.egd",
        "workup_group": GROUP_CONFIRM,
        "priority": PRIORITY_ESSENTIAL,
        "reason_template": "Confirm mucosal source in suspected peptic ulcer disease.",
        "related_diagnosis": "Peptic ulcer disease",
    },
    {
        "complaint_code": "intake.cc.epigastric_pain",
        "diagnosis_name": "Acute coronary syndrome",
        "investigation_id": "inv.imaging.abdominal_us",
        "workup_group": GROUP_EXCLUDE,
        "priority": PRIORITY_RECOMMENDED,
        "reason_template": "Exclude biliary alternative in upper abdominal pain.",
        "related_diagnosis": "Acute coronary syndrome",
    },
    {
        "complaint_code": "intake.cc.melena",
        "diagnosis_name": "Upper gastrointestinal bleeding",
        "investigation_id": "inv.lab.hb",
        "workup_group": GROUP_INITIAL,
        "priority": PRIORITY_ESSENTIAL,
        "reason_template": "Assess severity of possible GI blood loss.",
        "related_diagnosis": "Upper gastrointestinal bleeding",
    },
    {
        "complaint_code": "intake.cc.melena",
        "diagnosis_name": "Upper gastrointestinal bleeding",
        "investigation_id": "inv.endoscopy.egd",
        "workup_group": GROUP_SEVERITY,
        "priority": PRIORITY_ESSENTIAL,
        "reason_template": "Identify and risk-stratify upper GI bleeding source.",
        "related_diagnosis": "Upper gastrointestinal bleeding",
    },
]


def seed_investigation_library_if_empty(specialty_code: str = DEFAULT_SPECIALTY) -> int:
    if InvestigationLibraryEntry.query.first() is not None:
        return 0

    for item in LIBRARY:
        db.session.add(
            InvestigationLibraryEntry(
                investigation_id=item["investigation_id"],
                name=item["name"],
                category=item["category"],
                catalogue_code=item.get("catalogue_code"),
                indications_json=json.dumps(item.get("indications") or []),
                related_diagnosis_concepts_json=json.dumps(item.get("related_diagnosis_concepts") or []),
                knowledge_topic_key=item.get("knowledge_topic_key"),
                knowledge_stable_id=item.get("knowledge_stable_id"),
                specialty_code=specialty_code,
                department_id=1,
            )
        )

    sort = 10
    for rule in RULES:
        db.session.add(
            InvestigationRecommendationRule(
                complaint_code=rule.get("complaint_code"),
                diagnosis_name=rule.get("diagnosis_name"),
                investigation_id=rule["investigation_id"],
                workup_group=rule["workup_group"],
                priority=rule["priority"],
                reason_template=rule.get("reason_template"),
                related_diagnosis=rule.get("related_diagnosis"),
                missing_info_addressed=rule.get("missing_info_addressed"),
                sort_order=sort,
                specialty_code=specialty_code,
                department_id=1,
            )
        )
        sort += 10

    db.session.commit()
    return len(LIBRARY)
