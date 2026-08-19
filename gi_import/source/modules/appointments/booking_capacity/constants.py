"""Endoscopy appointment booking capacity rules (scheduling only)."""

from __future__ import annotations

# Procedure-type capacity buckets counted against daily limits.
CAPACITY_UPPER_GI = "upper_gi"
CAPACITY_COLONOSCOPY = "colonoscopy"
CAPACITY_PEG = "peg"
CAPACITY_ERCP = "ercp"
CAPACITY_SPECIAL = "special"
CAPACITY_NONE = "none"

ALL_CAPACITY_CATEGORIES = (
    CAPACITY_UPPER_GI,
    CAPACITY_COLONOSCOPY,
    CAPACITY_PEG,
    CAPACITY_ERCP,
    CAPACITY_SPECIAL,
    CAPACITY_NONE,
)

CAPACITY_CATEGORY_LABELS = {
    CAPACITY_UPPER_GI: "Upper GI endoscopy",
    CAPACITY_COLONOSCOPY: "Colonoscopy / sigmoidoscopy",
    CAPACITY_PEG: "PEG insertion",
    CAPACITY_ERCP: "ERCP",
    CAPACITY_SPECIAL: "Special / advanced therapeutic",
    CAPACITY_NONE: "Not capacity-tracked",
}

# Reception / scheduler roles share a sub-quota of the daily department cap.
SCHEDULER_ROLE_CODES = frozenset({"reception_staff"})

# ERCP weekday restriction: Tuesday (1) and Saturday (5) in Python weekday().
ERCOP_ALLOWED_WEEKDAYS = frozenset({1, 5})

DEFAULT_UPPER_GI_DAILY_CAP = 20
DEFAULT_COLONOSCOPY_DAILY_CAP = 15
DEFAULT_PEG_DAILY_CAP = 3
DEFAULT_SCHEDULER_SUB_QUOTA_PERCENT = 40
DEFAULT_TIME_LOCK_HOURS = 48
