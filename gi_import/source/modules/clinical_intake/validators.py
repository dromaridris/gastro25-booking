"""Clinical Intake validation."""

from __future__ import annotations

from app.core.exceptions import ValidationError
from app.modules.clinical_intake.models import (
    ALL_INTAKE_STATUSES,
    ALL_PRIORITIES,
    ClinicalIntakeRecord,
    normalize_text,
)


def validate_complaint_required(chief_complaint: str | None) -> str:
    text = (chief_complaint or "").strip()
    if not text:
        raise ValidationError("Chief complaint is required.")
    return text


def validate_priority(priority: str | None) -> str:
    value = (priority or "routine").strip().lower()
    if value not in ALL_PRIORITIES:
        raise ValidationError(f"Invalid priority: {priority}")
    return value


def validate_status(status: str | None) -> str:
    value = (status or "draft").strip().lower()
    if value not in ALL_INTAKE_STATUSES:
        raise ValidationError(f"Invalid intake status: {status}")
    return value


def validate_no_duplicate_intake(encounter_id: int, *, exclude_id: int | None = None) -> None:
    query = ClinicalIntakeRecord.query.filter_by(encounter_id=encounter_id, is_archived=False)
    if exclude_id is not None:
        query = query.filter(ClinicalIntakeRecord.id != exclude_id)
    if query.first() is not None:
        raise ValidationError("An active clinical intake already exists for this encounter.")


def validate_normalized_entry(
    *,
    normalized_complaint: str,
    is_unknown: bool,
    complaint_entry_id: int | None,
) -> None:
    if not normalized_complaint:
        raise ValidationError("Normalized complaint is required.")
    if is_unknown and complaint_entry_id is not None:
        raise ValidationError("Unknown complaints cannot reference a library entry.")
    if not is_unknown and complaint_entry_id is None:
        raise ValidationError("A valid library complaint must be selected or matched.")


def build_unknown_normalization(chief_complaint: str) -> str:
    """Fallback normalization when no library match exists."""
    return normalize_text(chief_complaint)
