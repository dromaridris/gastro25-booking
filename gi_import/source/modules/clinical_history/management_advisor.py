"""Management support after consultant confirms diagnosis."""

from app.modules.clinical_history import knowledge_bridge
from app.modules.clinical_history.models import ManagementGuidanceRule


def get_management_support(diagnosis_code: str) -> dict | None:
    rule = ManagementGuidanceRule.query.filter_by(
        diagnosis_code=diagnosis_code,
        is_archived=False,
    ).first()
    if rule is None:
        return None

    kl_notes = []
    if rule.knowledge_topic_key:
        kl_notes = knowledge_bridge.fetch_guidance(rule.knowledge_topic_key, {"diagnosis_code": diagnosis_code})

    return {
        "diagnosis_code": diagnosis_code,
        "summary": rule.summary_text,
        "principles": rule.principles_text,
        "scores": rule.scores_text,
        "red_flags": rule.red_flags_text,
        "follow_up": rule.follow_up_text,
        "knowledge_library_notes": kl_notes,
        "knowledge_topic_key": rule.knowledge_topic_key,
    }
