"""Clinical Intelligence layer — configuration-driven diagnostic interview."""

from app.modules.clinical_history.intelligence.branching_engine import (
    evaluate_activation,
    get_visible_question_codes,
)
from app.modules.clinical_history.intelligence.catalog_provider import get_catalog_provider
from app.modules.clinical_history.intelligence.differential_engine import (
    compute_differential,
    differential_for_display,
    top_diagnoses,
)
from app.modules.clinical_history.intelligence.investigation_engine import (
    all_suggestions_for_session,
    sync_suggestion_records,
)
from app.modules.clinical_history.intelligence.question_selector import (
    get_next_questions,
    interview_complete,
)
from app.modules.clinical_history.intelligence.teaching_engine import generate_teaching_explanation

__all__ = [
    "get_catalog_provider",
    "evaluate_activation",
    "get_visible_question_codes",
    "compute_differential",
    "differential_for_display",
    "top_diagnoses",
    "get_next_questions",
    "interview_complete",
    "all_suggestions_for_session",
    "sync_suggestion_records",
    "generate_teaching_explanation",
]
