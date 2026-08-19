"""Investigation guidance — delegates to Clinical Intelligence investigation engine."""

from app.modules.clinical_history.intelligence.investigation_engine import (
    all_suggestions_for_session,
    sync_suggestion_records,
)

__all__ = ["all_suggestions_for_session", "sync_suggestion_records"]
