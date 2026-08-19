"""Duty schedule views — Phase 7E."""

from __future__ import annotations

from datetime import date

from app.engines import permission_engine
from app.modules.workforce_identity.constants import DUTY_ROLE_GROUPS
from app.modules.workforce_identity.roster_integration import (
    list_today_on_duty,
    list_user_upcoming_duties,
)


def _require(user, permission: str) -> None:
    permission_engine.require(user, permission)


def get_my_next_duties(user, *, limit: int = 10) -> list:
    _require(user, "workforce_identity:duty_view")
    return list_user_upcoming_duties(user.id, limit=limit)


def get_today_on_call_team(acting_user, *, roster_date: date | None = None) -> dict:
    _require(acting_user, "workforce_identity:duty_view")
    entries = list_today_on_duty(roster_date=roster_date)
    grouped: dict[str, list[str]] = {}
    role_labels = dict(DUTY_ROLE_GROUPS)
    for entry in entries:
        role_code = entry.user.role.code if entry.user and entry.user.role else "staff"
        label = role_labels.get(role_code, entry.user.role.name if entry.user and entry.user.role else "Staff")
        grouped.setdefault(label, []).append(entry.user.full_name if entry.user else "Unknown")
    return {
        "roster_date": roster_date or date.today(),
        "team_by_role": grouped,
        "entries": entries,
    }
