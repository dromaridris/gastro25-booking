"""Clinical reasoning engine — re-exports Clinical Intelligence differential engine."""

from app.modules.clinical_history.intelligence.differential_engine import (
    CONSIDERATION_LOW,
    CONSIDERATION_MODERATE,
    CONSIDERATION_STRONG,
    compute_differential,
    differential_for_display,
    top_diagnoses,
)

__all__ = [
    "CONSIDERATION_STRONG",
    "CONSIDERATION_MODERATE",
    "CONSIDERATION_LOW",
    "compute_differential",
    "differential_for_display",
    "top_diagnoses",
]
