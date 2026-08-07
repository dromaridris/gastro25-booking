"""Clinical outcome tracking — physician-entered only."""

from __future__ import annotations

from app.modules.patient_journey.constants import ALL_OUTCOMES


class OutcomeTracker:
    """Validates and records physician-confirmed outcomes. Never auto-determines outcomes."""

    @staticmethod
    def validate_outcome(outcome: str) -> None:
        if outcome not in ALL_OUTCOMES:
            raise ValueError(
                f"Invalid outcome '{outcome}'. Must be one of: {', '.join(ALL_OUTCOMES)}"
            )

    @staticmethod
    def prepare_record(*, outcome: str, notes: str | None, physician_confirmed: bool = True) -> dict:
        OutcomeTracker.validate_outcome(outcome)
        if not physician_confirmed:
            raise ValueError("Outcomes must be physician-confirmed.")
        return {
            "outcome": outcome,
            "outcome_notes": notes,
            "physician_confirmed": True,
        }
