"""Sync published KL content into legacy UI catalogue tables (forms only — not intelligence source)."""

from __future__ import annotations

import json

from app.extensions import db
from app.modules.clinical_history.models import (
    ChiefComplaintDefinition,
    DiagnosisDefinition,
    HistoryQuestionDefinition,
)
from app.modules.knowledge_library.kl_catalog_loader import get_kl_catalog_index


def sync_ui_catalogue_from_knowledge_library() -> int:
    """Ensure interview UI tables have rows matching published KL — idempotent."""
    index = get_kl_catalog_index()
    index.ensure_loaded()
    if not index.is_populated():
        return 0

    count = 0
    for complaint in index.complaints:
        if ChiefComplaintDefinition.query.filter_by(code=complaint.code).first() is None:
            db.session.add(
                ChiefComplaintDefinition(
                    code=complaint.code,
                    name=complaint.name,
                    category=complaint.category,
                    sort_order=complaint.sort_order,
                    knowledge_topic_key=complaint.knowledge_topic_key,
                    department_id=1,
                )
            )
            count += 1

    for dx in index.diagnoses.values():
        if DiagnosisDefinition.query.filter_by(code=dx.code).first() is None:
            db.session.add(
                DiagnosisDefinition(
                    code=dx.code,
                    name=dx.name,
                    category=dx.category,
                    knowledge_topic_key=dx.knowledge_topic_key,
                    department_id=1,
                )
            )
            count += 1

    for question in index.questions.values():
        if HistoryQuestionDefinition.query.filter_by(code=question.code).first() is None:
            db.session.add(
                HistoryQuestionDefinition(
                    code=question.code,
                    prompt_text=question.prompt_text,
                    section=question.section,
                    answer_type=question.answer_type,
                    choices_json=question.choices_json,
                    is_exclusion_question=question.is_exclusion_question,
                    help_text=question.help_text,
                    knowledge_topic_key=question.knowledge_topic_key,
                    department_id=1,
                )
            )
            count += 1

    db.session.commit()
    return count
