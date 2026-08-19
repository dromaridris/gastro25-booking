"""Persisted booking capacity settings and holiday calendar."""

from __future__ import annotations

from app.core.base_model import BaseModel
from app.extensions import db
from app.modules.appointments.booking_capacity.constants import (
    DEFAULT_COLONOSCOPY_DAILY_CAP,
    DEFAULT_PEG_DAILY_CAP,
    DEFAULT_SCHEDULER_SUB_QUOTA_PERCENT,
    DEFAULT_TIME_LOCK_HOURS,
    DEFAULT_UPPER_GI_DAILY_CAP,
)


class BookingCapacitySettings(BaseModel):
    """Singleton row (id=1) — department-wide endoscopy booking caps."""

    __tablename__ = "booking_capacity_settings"

    upper_gi_daily_cap = db.Column(db.Integer, nullable=False, default=DEFAULT_UPPER_GI_DAILY_CAP)
    colonoscopy_daily_cap = db.Column(db.Integer, nullable=False, default=DEFAULT_COLONOSCOPY_DAILY_CAP)
    peg_daily_cap = db.Column(db.Integer, nullable=False, default=DEFAULT_PEG_DAILY_CAP)
    scheduler_sub_quota_percent = db.Column(
        db.Integer, nullable=False, default=DEFAULT_SCHEDULER_SUB_QUOTA_PERCENT
    )
    sunday_blocked = db.Column(db.Boolean, nullable=False, default=True)
    time_lock_hours = db.Column(db.Integer, nullable=False, default=DEFAULT_TIME_LOCK_HOURS)
    ercp_weekdays_only = db.Column(db.Boolean, nullable=False, default=True)

    def __repr__(self):
        return "<BookingCapacitySettings>"


class BookingHoliday(BaseModel):
    """Optional extra blocked dates beyond fixed public holidays."""

    __tablename__ = "booking_holidays"

    holiday_date = db.Column(db.Date, nullable=False, unique=True, index=True)
    label = db.Column(db.String(120), nullable=True)

    def __repr__(self):
        return f"<BookingHoliday {self.holiday_date}>"
