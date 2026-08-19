"""Seed complaint intelligence bundles into the clinical history catalogue."""

import json

from app.extensions import db
from app.modules.clinical_history.models import (
    ANSWER_TYPE_BOOLEAN,
    ANSWER_TYPE_CHOICE,
    ANSWER_TYPE_TEXT,
    AnswerWeightRule,
    ComplaintDifferentialPrior,
    ComplaintQuestionRule,
    DiagnosisDefinition,
    HistoryQuestionDefinition,
    InvestigationGuidanceRule,
    ManagementGuidanceRule,
    SUGGESTION_TIER_ADVANCED,
    SUGGESTION_TIER_BASELINE,
)

_TYPE_MAP = {
    "boolean": ANSWER_TYPE_BOOLEAN,
    "choice": ANSWER_TYPE_CHOICE,
    "text": ANSWER_TYPE_TEXT,
}


def seed_intelligence_bundle(
    complaint_code: str,
    *,
    diagnoses=None,
    questions=None,
    rules=None,
    priors=None,
    weight_rules=None,
    baseline_investigations=None,
    advanced_investigations=None,
    management=None,
) -> int:
    """Idempotent per-entity inserts for one complaint intelligence bundle."""
    count = 0
    diagnoses = diagnoses or []
    questions = questions or []
    rules = rules or []
    priors = priors or []
    weight_rules = weight_rules or []
    baseline_investigations = baseline_investigations or []
    advanced_investigations = advanced_investigations or []
    management = management or []

    for dx_code, dx_name, dx_cat, kl_key in diagnoses:
        if DiagnosisDefinition.query.filter_by(code=dx_code).first() is None:
            db.session.add(
                DiagnosisDefinition(
                    code=dx_code,
                    name=dx_name,
                    category=dx_cat,
                    knowledge_topic_key=kl_key,
                    department_id=1,
                )
            )
            count += 1

    for row in questions:
        code, prompt, section, atype, choices, is_excl, help_text, _purpose = row
        if HistoryQuestionDefinition.query.filter_by(code=code).first() is None:
            db.session.add(
                HistoryQuestionDefinition(
                    code=code,
                    prompt_text=prompt,
                    section=section,
                    answer_type=_TYPE_MAP.get(atype, ANSWER_TYPE_BOOLEAN),
                    choices_json=json.dumps(choices) if choices else None,
                    is_exclusion_question=is_excl,
                    help_text=help_text,
                    department_id=1,
                )
            )
            count += 1

    db.session.flush()

    for rule in rules:
        (
            qcode,
            sort_order,
            purpose,
            priority,
            parent_q,
            parent_a,
            activation_json,
            targets_json,
            rationale,
        ) = rule
        if ComplaintQuestionRule.query.filter_by(
            complaint_code=complaint_code, question_code=qcode
        ).first() is None:
            db.session.add(
                ComplaintQuestionRule(
                    complaint_code=complaint_code,
                    question_code=qcode,
                    sort_order=sort_order,
                    parent_question_code=parent_q,
                    parent_answer_required=parent_a,
                    activation_json=activation_json,
                    question_purpose=purpose,
                    differential_priority=priority,
                    target_diagnosis_codes_json=targets_json,
                    clinical_rationale=rationale,
                    department_id=1,
                )
            )
            count += 1

    for complaint, dx, prior in priors:
        if ComplaintDifferentialPrior.query.filter_by(
            complaint_code=complaint, diagnosis_code=dx
        ).first() is None:
            db.session.add(
                ComplaintDifferentialPrior(
                    complaint_code=complaint,
                    diagnosis_code=dx,
                    prior_weight=prior,
                    department_id=1,
                )
            )
            count += 1

    for complaint, qcode, match, dx, delta in weight_rules:
        db.session.add(
            AnswerWeightRule(
                complaint_code=complaint,
                question_code=qcode,
                answer_match=match,
                diagnosis_code=dx,
                weight_delta=delta,
                department_id=1,
            )
        )
        count += 1

    for idx, row in enumerate(baseline_investigations):
        complaint, inv_code, reason = row
        db.session.add(
            InvestigationGuidanceRule(
                complaint_code=complaint,
                investigation_code=inv_code,
                tier=SUGGESTION_TIER_BASELINE,
                reason_text=reason,
                sort_order=(idx + 1) * 10,
                department_id=1,
            )
        )
        count += 1

    for idx, row in enumerate(advanced_investigations):
        dx, inv_code, reason = row
        db.session.add(
            InvestigationGuidanceRule(
                diagnosis_code=dx,
                investigation_code=inv_code,
                tier=SUGGESTION_TIER_ADVANCED,
                reason_text=reason,
                sort_order=(idx + 1) * 10,
                department_id=1,
            )
        )
        count += 1

    for row in management:
        if ManagementGuidanceRule.query.filter_by(diagnosis_code=row[0]).first() is None:
            db.session.add(
                ManagementGuidanceRule(
                    diagnosis_code=row[0],
                    summary_text=row[1],
                    principles_text=row[2],
                    scores_text=row[3],
                    red_flags_text=row[4],
                    follow_up_text=row[5],
                    knowledge_topic_key=row[6],
                    department_id=1,
                )
            )
            count += 1

    return count
