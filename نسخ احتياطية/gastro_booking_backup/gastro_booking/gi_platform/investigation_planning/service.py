"""Investigation Planning orchestration — Gastro25."""

from __future__ import annotations

import json
from typing import Any

from gi_platform import history_service
from gi_platform.audit_service import log_event
from gi_platform.clinical_assessment import service as assessment_service
from gi_platform.investigation_planning.catalogue_seed import seed_investigation_library_if_empty
from gi_platform.investigation_planning.constants import (
    AUDIT_PREFIX, DECISION_ACCEPTED, DECISION_MANUAL, DECISION_MODIFIED, DECISION_REJECTED,
    PLAN_STATUS_APPROVED, PLAN_STATUS_DRAFT, PLAN_STATUS_MODIFIED, PLAN_STATUS_REJECTED,
    PLAN_STATUS_REVIEWED, SUGGESTION_STATUS_SUGGESTED,
)
from gi_platform.investigation_planning.context_builder import InvestigationContextBuilder
from gi_platform.investigation_planning.investigation_engine import InvestigationSuggestionEngine
from gi_platform.investigation_planning.permissions import require_investigation_plan_use, require_investigation_plan_view
from gi_platform.investigation_planning.recommendation_generator import InvestigationRecommendationGenerator


class NotFoundError(LookupError):
    pass


class ValidationError(ValueError):
    pass


def generate_plan(db, *, role, user_id, history_session_id: int) -> dict:
    require_investigation_plan_use(role=role)
    seed_investigation_library_if_empty(db)

    hist = history_service.get_session(db, history_session_id)
    if not hist:
        raise NotFoundError(f'No history session {history_session_id}')
    if not hist['complaint_code']:
        raise ValidationError('Chief complaint required before investigation planning.')

    assessment = assessment_service.get_latest_run(db, role=role, history_session_id=history_session_id)
    if not assessment:
        raise ValidationError('Differential assessment required before investigation planning.')

    context = InvestigationContextBuilder().build(db, history_session_id=history_session_id, role=role)
    deterministic = InvestigationSuggestionEngine().generate(db, context)

    ai_result = InvestigationRecommendationGenerator(db).generate(
        role=role, user_id=user_id, history_session_id=history_session_id,
        ward_patient_id=hist['ward_patient_id'], clinical_context=context,
        deterministic_suggestions=deterministic,
    )

    cur = db.execute(
        """
        INSERT INTO gi_investigation_plan (
            history_session_id, ward_patient_id, assessment_run_id,
            ai_session_uuid, provider_key, model_name, status,
            knowledge_sources_json, clinical_context_json, created_by
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            history_session_id, hist['ward_patient_id'], assessment['id'],
            ai_result['ai_session_uuid'], ai_result['provider_key'], ai_result['model_name'],
            PLAN_STATUS_DRAFT,
            json.dumps(context.get('knowledge_sources') or []),
            json.dumps(context), user_id,
        ),
    )
    plan_id = cur.lastrowid

    for item in deterministic:
        db.execute(
            """
            INSERT INTO gi_investigation_plan_suggestion (
                plan_id, history_session_id, ward_patient_id,
                investigation_id, investigation_name, category, priority, workup_group,
                reason, related_diagnosis, clinical_purpose, missing_info_addressed,
                knowledge_references_json, confidence_indicator, ai_session_uuid,
                duplicate_skipped, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                plan_id, history_session_id, hist['ward_patient_id'],
                item['investigation_id'], item['investigation_name'], item['category'],
                item['priority'], item['workup_group'], item.get('reason'),
                item.get('related_diagnosis'), item.get('clinical_purpose'),
                item.get('missing_info_addressed'),
                json.dumps(item.get('knowledge_references') or []),
                item.get('confidence_indicator', 'medium'),
                ai_result['ai_session_uuid'], 1 if item.get('duplicate_skipped') else 0,
                SUGGESTION_STATUS_SUGGESTED,
            ),
        )

    db.commit()
    log_event(
        db, action=f'{AUDIT_PREFIX}.generation_completed',
        entity_type='investigation_plan', entity_id=plan_id, user_id=user_id,
        details={'history_session_id': history_session_id, 'suggestion_count': len(deterministic)},
    )
    return get_plan(db, role=role, plan_id=plan_id)


def get_plan(db, *, role, plan_id: int) -> dict:
    require_investigation_plan_view(role=role)
    row = db.execute('SELECT * FROM gi_investigation_plan WHERE id = ?', (plan_id,)).fetchone()
    if not row:
        raise NotFoundError(f'No investigation plan {plan_id}')
    return plan_to_dict(row)


def get_latest_plan(db, *, role, history_session_id: int) -> dict | None:
    require_investigation_plan_view(role=role)
    row = db.execute(
        """
        SELECT * FROM gi_investigation_plan
        WHERE history_session_id = ? ORDER BY created_at DESC LIMIT 1
        """,
        (history_session_id,),
    ).fetchone()
    return plan_to_dict(row) if row else None


def get_plan_view(db, *, role, history_session_id: int) -> dict[str, Any]:
    plan = get_latest_plan(db, role=role, history_session_id=history_session_id)
    if not plan:
        return {'plan': None, 'suggestions': [], 'decisions': [], 'grouped': {}}

    suggestions = list_suggestions(db, role=role, plan_id=plan['id'])
    decisions = get_physician_decisions(db, role=role, history_session_id=history_session_id)
    grouped = InvestigationSuggestionEngine().group_by_workup(suggestions)
    return {'plan': plan, 'suggestions': suggestions, 'decisions': decisions, 'grouped': grouped}


def list_suggestions(db, *, role, plan_id: int) -> list[dict]:
    get_plan(db, role=role, plan_id=plan_id)
    rows = db.execute(
        """
        SELECT * FROM gi_investigation_plan_suggestion
        WHERE plan_id = ? ORDER BY id
        """,
        (plan_id,),
    ).fetchall()
    return [suggestion_to_dict(r) for r in rows]


def accept_suggestion(db, *, role, user_id, suggestion_id, reason=None):
    require_investigation_plan_use(role=role)
    s = _get_suggestion(db, suggestion_id)
    return _record_decision(
        db, user_id=user_id, suggestion=s, plan_id=s['plan_id'],
        history_session_id=s['history_session_id'], ward_patient_id=s['ward_patient_id'],
        investigation_name=s['investigation_name'], category=s['category'], priority=s['priority'],
        physician_status=DECISION_ACCEPTED, physician_reason=reason,
    )


def reject_suggestion(db, *, role, user_id, suggestion_id, reason=None):
    require_investigation_plan_use(role=role)
    s = _get_suggestion(db, suggestion_id)
    return _record_decision(
        db, user_id=user_id, suggestion=s, plan_id=s['plan_id'],
        history_session_id=s['history_session_id'], ward_patient_id=s['ward_patient_id'],
        investigation_name=s['investigation_name'], category=s['category'], priority=s['priority'],
        physician_status=DECISION_REJECTED, physician_reason=reason,
    )


def modify_suggestion(db, *, role, user_id, suggestion_id, investigation_name=None, priority=None, reason=None):
    require_investigation_plan_use(role=role)
    s = _get_suggestion(db, suggestion_id)
    modified_fields = {}
    name = investigation_name or s['investigation_name']
    pri = priority or s['priority']
    if investigation_name:
        modified_fields['investigation_name'] = investigation_name
    if priority:
        modified_fields['priority'] = priority
    db.execute(
        "UPDATE gi_investigation_plan SET status = ? WHERE id = ?",
        (PLAN_STATUS_MODIFIED, s['plan_id']),
    )
    return _record_decision(
        db, user_id=user_id, suggestion=s, plan_id=s['plan_id'],
        history_session_id=s['history_session_id'], ward_patient_id=s['ward_patient_id'],
        investigation_name=name, category=s['category'], priority=pri,
        physician_status=DECISION_MODIFIED, physician_reason=reason,
        modified_fields=modified_fields,
    )


def add_manual_investigation(db, *, role, user_id, history_session_id, investigation_name,
                             category=None, priority=None, reason=None):
    require_investigation_plan_use(role=role)
    hist = history_service.get_session(db, history_session_id)
    plan = get_latest_plan(db, role=role, history_session_id=history_session_id)
    return _record_decision(
        db, user_id=user_id, suggestion=None,
        plan_id=plan['id'] if plan else None,
        history_session_id=history_session_id,
        ward_patient_id=hist['ward_patient_id'] if hist else None,
        investigation_name=investigation_name, category=category, priority=priority,
        physician_status=DECISION_MANUAL, physician_reason=reason,
    )


def review_plan(db, *, role, plan_id: int) -> dict:
    get_plan(db, role=role, plan_id=plan_id)
    db.execute(
        "UPDATE gi_investigation_plan SET status = ? WHERE id = ?",
        (PLAN_STATUS_REVIEWED, plan_id),
    )
    db.commit()
    return get_plan(db, role=role, plan_id=plan_id)


def approve_plan(db, *, role, user_id, plan_id: int) -> dict:
    require_investigation_plan_use(role=role)
    db.execute(
        "UPDATE gi_investigation_plan SET status = ? WHERE id = ?",
        (PLAN_STATUS_APPROVED, plan_id),
    )
    db.commit()
    log_event(
        db, action=f'{AUDIT_PREFIX}.plan_approved',
        entity_type='investigation_plan', entity_id=plan_id, user_id=user_id,
    )
    return get_plan(db, role=role, plan_id=plan_id)


def reject_plan(db, *, role, user_id, plan_id: int, reason=None) -> dict:
    db.execute(
        "UPDATE gi_investigation_plan SET status = ? WHERE id = ?",
        (PLAN_STATUS_REJECTED, plan_id),
    )
    db.commit()
    log_event(
        db, action=f'{AUDIT_PREFIX}.plan_rejected',
        entity_type='investigation_plan', entity_id=plan_id, user_id=user_id,
        details={'reason': reason},
    )
    return get_plan(db, role=role, plan_id=plan_id)


def get_physician_decisions(db, *, role, history_session_id) -> list[dict]:
    require_investigation_plan_view(role=role)
    rows = db.execute(
        """
        SELECT * FROM gi_physician_investigation_decision
        WHERE history_session_id = ? ORDER BY created_at DESC
        """,
        (history_session_id,),
    ).fetchall()
    return [decision_to_dict(r) for r in rows]


def _get_suggestion(db, suggestion_id) -> dict:
    row = db.execute(
        'SELECT * FROM gi_investigation_plan_suggestion WHERE id = ?', (suggestion_id,),
    ).fetchone()
    if not row:
        raise NotFoundError(f'No suggestion {suggestion_id}')
    return suggestion_to_dict(row)


def _record_decision(db, *, user_id, suggestion, plan_id, history_session_id, ward_patient_id,
                     investigation_name, category, priority, physician_status,
                     physician_reason=None, modified_fields=None) -> dict:
    cur = db.execute(
        """
        INSERT INTO gi_physician_investigation_decision (
            plan_id, suggestion_id, history_session_id, ward_patient_id,
            investigation_name, category, priority, physician_status,
            physician_reason, modified_fields_json, created_by
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            plan_id, suggestion['id'] if suggestion else None,
            history_session_id, ward_patient_id,
            investigation_name, category, priority, physician_status,
            physician_reason, json.dumps(modified_fields or {}), user_id,
        ),
    )
    db.commit()
    return decision_to_dict(db.execute(
        'SELECT * FROM gi_physician_investigation_decision WHERE id = ?', (cur.lastrowid,),
    ).fetchone())


def plan_to_dict(row) -> dict:
    return {
        'id': row['id'],
        'history_session_id': row['history_session_id'],
        'ward_patient_id': row['ward_patient_id'],
        'assessment_run_id': row['assessment_run_id'],
        'ai_session_uuid': row['ai_session_uuid'],
        'provider_key': row['provider_key'],
        'model_name': row['model_name'],
        'status': row['status'],
        'knowledge_sources': json.loads(row['knowledge_sources_json'] or '[]'),
        'created_at': row['created_at'],
    }


def suggestion_to_dict(row) -> dict:
    data = dict(row)
    return {
        'id': data['id'],
        'plan_id': data['plan_id'],
        'history_session_id': data.get('history_session_id'),
        'ward_patient_id': data.get('ward_patient_id'),
        'investigation_id': data['investigation_id'],
        'investigation_name': data['investigation_name'],
        'category': data['category'],
        'priority': data['priority'],
        'workup_group': data['workup_group'],
        'reason': data.get('reason'),
        'related_diagnosis': data.get('related_diagnosis'),
        'clinical_purpose': data.get('clinical_purpose'),
        'missing_info_addressed': data.get('missing_info_addressed'),
        'knowledge_references': json.loads(data.get('knowledge_references_json') or '[]'),
        'confidence_indicator': data.get('confidence_indicator'),
        'duplicate_skipped': bool(data.get('duplicate_skipped')),
        'status': data.get('status'),
    }


def decision_to_dict(row) -> dict:
    return {
        'id': row['id'],
        'suggestion_id': row['suggestion_id'],
        'investigation_name': row['investigation_name'],
        'category': row['category'],
        'priority': row['priority'],
        'physician_status': row['physician_status'],
        'physician_reason': row['physician_reason'],
        'modified_fields': json.loads(row['modified_fields_json'] or '{}'),
        'created_at': row['created_at'],
    }
