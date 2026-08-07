"""Red flag detection — immediate alerts when structured conditions are met."""

from __future__ import annotations

from gi_platform.decision_support.context import AssessmentContext, RedFlagAlert
from gi_platform.decision_support.knowledge_accessor import CdsKnowledgeAccessor
from gi_platform.decision_support.variable_resolver import condition_met


def detect_red_flags(
    context: AssessmentContext,
    accessor: CdsKnowledgeAccessor,
) -> list[RedFlagAlert]:
    alerts: list[RedFlagAlert] = []
    for rule in accessor.red_flag_rules(context.complaint_code):
        attrs = rule.attributes
        condition = attrs.get("condition")
        if not condition_met(context, condition):
            continue
        alerts.append(
            RedFlagAlert(
                stable_id=rule.stable_id,
                code=attrs.get("red_flag_code") or rule.stable_id,
                title=rule.title,
                message=attrs.get("message") or rule.summary or rule.title,
                severity=attrs.get("severity", "high"),
            )
        )
    return alerts
