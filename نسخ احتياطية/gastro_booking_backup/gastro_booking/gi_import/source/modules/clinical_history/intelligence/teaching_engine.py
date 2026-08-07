"""Teaching mode — educational explanation after consultant confirms diagnosis.

Output is for trainee education, NOT the official medical record.
"""

from __future__ import annotations

import json

from app.modules.clinical_history import knowledge_bridge
from app.modules.clinical_history.intelligence.branching_engine import answer_map
from app.modules.clinical_history.intelligence.catalog_provider import get_catalog_provider
from app.modules.clinical_history.intelligence.differential_engine import compute_differential
from app.modules.clinical_history.intelligence.investigation_engine import all_suggestions_for_session
from app.modules.clinical_history.models import HistorySession


def _normalize(v: str) -> str:
    return (v or "").strip().lower()


def generate_teaching_explanation(session: HistorySession) -> dict:
    if not session.confirmed_diagnosis_code or not session.chief_complaint_code:
        return {}

    provider = get_catalog_provider()
    confirmed = session.confirmed_diagnosis_code
    dx = provider.diagnosis(confirmed)
    answers = answer_map(session.id)

    supporting: list[dict] = []
    excluding: list[dict] = []

    for rule in provider.weight_rules_for_complaint(session.chief_complaint_code):
        ans = answers.get(rule.question_code)
        if ans is None:
            continue
        if _normalize(rule.answer_match) != ans:
            continue

        q = provider.get_question(rule.question_code)
        prompt = q.prompt_text if q else rule.question_code

        entry = {
            "question_code": rule.question_code,
            "prompt": prompt,
            "answer": ans,
            "weight_delta": rule.weight_delta,
        }

        if rule.diagnosis_code == confirmed and rule.weight_delta > 0:
            supporting.append(entry)
        elif rule.diagnosis_code != confirmed and rule.weight_delta > 0:
            excluding.append({
                **entry,
                "excluded_diagnosis": rule.diagnosis_code,
                "excluded_name": (provider.diagnosis(rule.diagnosis_code).name
                                  if provider.diagnosis(rule.diagnosis_code) else rule.diagnosis_code),
            })

    differential = compute_differential(session.chief_complaint_code, session.id)
    suggestions = all_suggestions_for_session(session)
    management = provider.management_for_diagnosis(confirmed)

    kl_topics: list[dict] = []
    if management and management.knowledge_topic_key:
        kl_topics.extend(knowledge_bridge.fetch_guidance(management.knowledge_topic_key, {
            "diagnosis_code": confirmed,
            "complaint_code": session.chief_complaint_code,
        }))
    if dx and dx.knowledge_topic_key:
        kl_topics.extend(knowledge_bridge.fetch_guidance(dx.knowledge_topic_key, {
            "diagnosis_code": confirmed,
        }))

    explanation = {
        "confirmed_diagnosis_code": confirmed,
        "confirmed_diagnosis_name": dx.name if dx else confirmed,
        "why_this_diagnosis": (
            f"The confirmed diagnosis of {dx.name if dx else confirmed} is supported by the "
            f"history features listed below. This represents the consultant's clinical judgement "
            f"— the system's differential considerations are educational aids only."
        ),
        "supporting_features": supporting,
        "features_that_excluded_alternatives": excluding,
        "differential_at_completion": differential,
        "investigation_rationale": [
            {
                "investigation_code": s["investigation_code"],
                "tier": s["tier"],
                "reason": s.get("reason_text"),
                "linked_diagnosis": s.get("linked_diagnosis_code"),
            }
            for s in suggestions
        ],
        "management_summary": management.summary_text if management else None,
        "management_principles": management.principles_text if management else None,
        "recommended_scores": management.scores_text if management else None,
        "red_flags": management.red_flags_text if management else None,
        "follow_up_guidance": management.follow_up_text if management else None,
        "knowledge_library_notes": kl_topics,
        "disclaimer": (
            "This teaching explanation is for trainee education. It does not form part of "
            "the medico-legal medical record."
        ),
    }
    return explanation


def persist_teaching_explanation(session: HistorySession) -> dict:
    explanation = generate_teaching_explanation(session)
    session.teaching_json = json.dumps(explanation)
    from app.extensions import db
    db.session.commit()
    return explanation
