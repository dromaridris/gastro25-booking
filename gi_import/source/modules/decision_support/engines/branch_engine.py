"""Interview branch activation — adaptive branching from KL rules."""

from __future__ import annotations

from app.modules.decision_support.context import AssessmentContext
from app.modules.decision_support.knowledge_accessor import CdsKnowledgeAccessor
from app.modules.decision_support.variable_resolver import condition_met


def branch_activation_rules(accessor: CdsKnowledgeAccessor, complaint_code: str):
    return accessor.branch_activation_rules(complaint_code)


def active_branches(context: AssessmentContext, accessor: CdsKnowledgeAccessor) -> list[str]:
    """Return branch codes currently active based on answers and KL activation rules."""
    active: list[str] = []
    for rule in branch_activation_rules(accessor, context.complaint_code):
        branch = rule.attributes.get("branch_code")
        condition = rule.attributes.get("condition")
        if branch and condition_met(context, condition):
            if branch not in active:
                active.append(branch)
    return active


def question_branch_visible(
    branch_code: str | None,
    context: AssessmentContext,
    accessor: CdsKnowledgeAccessor,
) -> bool:
    """Questions without a branch are always eligible; branched questions need an active branch."""
    if not branch_code:
        return True
    return branch_code in active_branches(context, accessor)
