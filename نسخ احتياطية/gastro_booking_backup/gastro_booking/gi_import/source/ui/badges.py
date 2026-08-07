"""Semantic badge class mapping — replaces Bootstrap colour utilities."""

from __future__ import annotations

STATUS_BADGE_MAP = {
    "draft": "gi-badge-warning",
    "published": "gi-badge-success",
    "finalized": "gi-badge-success",
    "locked": "gi-badge-info",
    "open": "gi-badge-warning",
    "closed": "gi-badge-muted",
    "archived": "gi-badge-muted",
    "cancelled": "gi-badge-danger",
    "canceled": "gi-badge-danger",
    "active": "gi-badge-success",
    "inactive": "gi-badge-muted",
    "pending": "gi-badge-warning",
    "completed": "gi-badge-success",
    "in_progress": "gi-badge-info",
    "review": "gi-badge-info",
    "normal": "gi-badge-success",
    "high": "gi-badge-danger",
    "low": "gi-badge-warning",
}


def badge_class_for_status(status: str | None, *, default: str = "gi-badge-muted") -> str:
    if not status:
        return default
    key = status.lower().replace(" ", "_").replace("-", "_")
    return STATUS_BADGE_MAP.get(key, default)


def severity_badge_class(severity: str) -> str:
    mapping = {
        "high": "gi-badge-danger",
        "medium": "gi-badge-warning",
        "low": "gi-badge-info",
    }
    return mapping.get((severity or "").lower(), "gi-badge-muted")
