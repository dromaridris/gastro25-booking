"""Analytics Foundation constants."""

from __future__ import annotations

PERM_VIEW = "analytics:view"
PERM_CONFIGURE = "analytics:configure"
PERM_EXPORT = "analytics:export"

METRIC_STATUS_ACTIVE = "active"
METRIC_STATUS_INACTIVE = "inactive"

ALL_METRIC_STATUSES = (METRIC_STATUS_ACTIVE, METRIC_STATUS_INACTIVE)

CATEGORY_VOLUME = "volume"
CATEGORY_COMPLETION = "completion"
CATEGORY_UTILIZATION = "utilization"

ALL_CATEGORIES = (CATEGORY_VOLUME, CATEGORY_COMPLETION, CATEGORY_UTILIZATION)

PERIOD_DAILY = "daily"
PERIOD_WEEKLY = "weekly"
PERIOD_MONTHLY = "monthly"
PERIOD_CUSTOM = "custom"

ALL_PERIODS = (PERIOD_DAILY, PERIOD_WEEKLY, PERIOD_MONTHLY, PERIOD_CUSTOM)

# Built-in metric identifiers (foundation metrics — not clinical/endoscopy KPIs).
METRIC_PATIENT_VOLUME = "patient_volume"
METRIC_ENCOUNTER_COUNT = "encounter_count"
METRIC_PROCEDURE_COUNT = "procedure_count"
METRIC_FOLLOW_UP_COMPLETION_RATE = "follow_up_completion_rate"
METRIC_DOCUMENT_COMPLETION_RATE = "document_completion_rate"

TRAINEE_ROLE_CODES = frozenset(
    {
        "senior_registrar",
        "house_officer",
        "visiting_trainee",
    }
)

AUDIT_DASHBOARD_ACCESS = "analytics.dashboard_access"
AUDIT_METRIC_EXECUTION = "analytics.metric_execution"
AUDIT_EXPORT_REQUEST = "analytics.export_request"
AUDIT_CONFIG_CHANGE = "analytics.config_change"
