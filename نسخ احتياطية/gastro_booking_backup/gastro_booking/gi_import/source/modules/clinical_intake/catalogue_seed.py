"""Default chief complaint library seed — specialty data, not hardcoded logic."""

from __future__ import annotations

from app.extensions import db
from app.modules.clinical_intake.models import (
    ChiefComplaintCategory,
    ChiefComplaintEntry,
    ChiefComplaintTerm,
    TERM_TYPE_ABBREVIATION,
    TERM_TYPE_ALIAS,
    TERM_TYPE_SYNONYM,
    normalize_text,
)

DEFAULT_SPECIALTY_CODE = "gastroenterology"

CATEGORIES = [
    ("intake.cat.abdominal_pain", "Abdominal pain", None, 10),
    ("intake.cat.gi_bleeding", "GI bleeding", None, 20),
    ("intake.cat.altered_bowel", "Altered bowel habit", None, 30),
]

COMPLAINTS = [
    {
        "code": "intake.cc.epigastric_pain",
        "display_name": "Epigastric pain",
        "category_code": "intake.cat.abdominal_pain",
        "parent_code": None,
        "sort_order": 10,
        "terms": [
            (TERM_TYPE_SYNONYM, "Upper abdominal pain"),
            (TERM_TYPE_SYNONYM, "Epigastric discomfort"),
            (TERM_TYPE_SYNONYM, "Pain in pit of stomach"),
            (TERM_TYPE_ALIAS, "Epigastric ache"),
            (TERM_TYPE_ABBREVIATION, "EPI pain"),
        ],
    },
    {
        "code": "intake.cc.right_upper_quadrant_pain",
        "display_name": "Right upper quadrant pain",
        "category_code": "intake.cat.abdominal_pain",
        "parent_code": None,
        "sort_order": 20,
        "terms": [
            (TERM_TYPE_SYNONYM, "RUQ pain"),
            (TERM_TYPE_ABBREVIATION, "RUQ"),
            (TERM_TYPE_ALIAS, "Pain under right ribs"),
        ],
    },
    {
        "code": "intake.cc.melena",
        "display_name": "Melena",
        "category_code": "intake.cat.gi_bleeding",
        "parent_code": None,
        "sort_order": 10,
        "terms": [
            (TERM_TYPE_SYNONYM, "Black stools"),
            (TERM_TYPE_SYNONYM, "Tarry stools"),
            (TERM_TYPE_ALIAS, "Passing black stool"),
        ],
    },
    {
        "code": "intake.cc.hematochezia",
        "display_name": "Hematochezia",
        "category_code": "intake.cat.gi_bleeding",
        "parent_code": None,
        "sort_order": 20,
        "terms": [
            (TERM_TYPE_SYNONYM, "Fresh rectal bleeding"),
            (TERM_TYPE_SYNONYM, "Bright red blood per rectum"),
            (TERM_TYPE_ABBREVIATION, "BRBPR"),
        ],
    },
    {
        "code": "intake.cc.chronic_diarrhea",
        "display_name": "Chronic diarrhea",
        "category_code": "intake.cat.altered_bowel",
        "parent_code": None,
        "sort_order": 10,
        "terms": [
            (TERM_TYPE_SYNONYM, "Loose stools"),
            (TERM_TYPE_SYNONYM, "Persistent diarrhea"),
        ],
    },
]


def seed_chief_complaint_library_if_empty(specialty_code: str = DEFAULT_SPECIALTY_CODE) -> int:
    if ChiefComplaintEntry.query.first() is not None:
        return 0

    category_ids: dict[str, int] = {}
    for code, name, parent_code, sort_order in CATEGORIES:
        parent_id = category_ids.get(parent_code) if parent_code else None
        row = ChiefComplaintCategory(
            code=code,
            name=name,
            specialty_code=specialty_code,
            parent_category_id=parent_id,
            sort_order=sort_order,
            department_id=1,
        )
        db.session.add(row)
        db.session.flush()
        category_ids[code] = row.id

    entry_ids: dict[str, int] = {}
    created = 0
    for item in COMPLAINTS:
        row = ChiefComplaintEntry(
            code=item["code"],
            display_name=item["display_name"],
            normalized_name=normalize_text(item["display_name"]),
            category_id=category_ids[item["category_code"]],
            parent_entry_id=entry_ids.get(item["parent_code"]) if item.get("parent_code") else None,
            specialty_code=specialty_code,
            sort_order=item["sort_order"],
            department_id=1,
        )
        db.session.add(row)
        db.session.flush()
        entry_ids[item["code"]] = row.id
        created += 1

        for term_type, term_text in item.get("terms", []):
            db.session.add(
                ChiefComplaintTerm(
                    complaint_id=row.id,
                    term_type=term_type,
                    term_text=term_text,
                    normalized_term=normalize_text(term_text),
                    department_id=1,
                )
            )

    db.session.commit()
    return created
