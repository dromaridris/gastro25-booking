"""Reusable aggregation services for analytics periods."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from .constants import PERIOD_CUSTOM, PERIOD_DAILY, PERIOD_MONTHLY, PERIOD_WEEKLY


@dataclass
class PeriodWindow:
    period_type: str
    start: datetime
    end: datetime

    def to_dict(self) -> dict:
        return {
            "period_type": self.period_type,
            "start": self.start.isoformat(),
            "end": self.end.isoformat(),
        }


def _ensure_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def resolve_period(
    period_type: str,
    *,
    reference: datetime | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> PeriodWindow:
    """Resolve aggregation window for daily, weekly, monthly, or custom ranges."""
    now = _ensure_utc(reference or datetime.now(timezone.utc))

    if period_type == PERIOD_CUSTOM:
        if date_from is None or date_to is None:
            raise ValueError("Custom period requires date_from and date_to.")
        return PeriodWindow(
            period_type=PERIOD_CUSTOM,
            start=_ensure_utc(date_from),
            end=_ensure_utc(date_to),
        )

    if period_type == PERIOD_DAILY:
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1) - timedelta(microseconds=1)
        return PeriodWindow(period_type=PERIOD_DAILY, start=start, end=end)

    if period_type == PERIOD_WEEKLY:
        weekday = now.weekday()
        start = (now - timedelta(days=weekday)).replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=7) - timedelta(microseconds=1)
        return PeriodWindow(period_type=PERIOD_WEEKLY, start=start, end=end)

    if period_type == PERIOD_MONTHLY:
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if start.month == 12:
            next_month = start.replace(year=start.year + 1, month=1)
        else:
            next_month = start.replace(month=start.month + 1)
        end = next_month - timedelta(microseconds=1)
        return PeriodWindow(period_type=PERIOD_MONTHLY, start=start, end=end)

    raise ValueError(f"Unsupported period type: {period_type}")


def bucket_daily_series(
    period_start: datetime,
    period_end: datetime,
) -> list[tuple[datetime, datetime]]:
    """Split a custom range into daily buckets for time-series aggregation."""
    start = _ensure_utc(period_start)
    end = _ensure_utc(period_end)
    buckets: list[tuple[datetime, datetime]] = []
    cursor = start.replace(hour=0, minute=0, second=0, microsecond=0)
    while cursor <= end:
        bucket_end = min(cursor + timedelta(days=1) - timedelta(microseconds=1), end)
        buckets.append((cursor, bucket_end))
        cursor = cursor + timedelta(days=1)
    return buckets
