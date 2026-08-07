"""Management Plan AI orchestration — Gastro25."""

from __future__ import annotations

import json
from typing import Any

from gi_platform import history_service
from gi_platform.audit_service import log_event
from gi_platform.clinical_assessment import service as assessment_service
from gi_platform.management_plan_ai.catalogue_seed import seed_management_rules_if_empty
from gi_platform.management_plan_ai.constants import (
    AUDIT_PREFIX, DECISION_ACCEPTED, DECISION_MANUAL, DECISION_MODIFIED, DECISION_REJECTED,
    PLAN_STATUS_APPROVED, PLAN_STATUS_DRAFT, PLAN_STATUS_MODIFIED, PLAN_STATUS_REJECTED,
    PLAN_STATUS_REVIEWED, SUGGESTION_STATUS_SUGGESTED,
)
from gi_platform.management_plan_ai.context_builder import ManagementContextBuilder
from gi_platform.management_plan_ai.management_engine import ManagementEngine
from gi_platform.management_plan_ai.permissions import require_management_plan_ai_use, require_management_plan_ai_view
from gi_platform.management_plan_ai.recommendation_generator import ManagementRecommendationGenerator


class NotFoundError(LookupError):
    pass


class ValidationError(ValueError):
    pass


def generate_plan(db, *, role, user_id, history_session_id: int) -> dict:
    require_management_plan_ai_use(role=role)
    seed_management_rules_if_empty(db)

    hist = history_service.get_session(db, history_session_id)
    if not hist:
        raise NotFoundError(f'No history session {history_session_id}')

    assessment = assessment_service.get_latest_run(db, role=role, history_session_id=history_session_id)
    if not assessment:
        raise ValidationError('Clinical assessment required before management planning.')

    context = ManagementContextBuilder().build(db, history_session_id=history_session_id, role=role)
    working = context.get('working_diagnoses') or []
    if not working:
        raise ValidationError('Confirmed or suspected diagnosis required before management planning.')

    deterministic = ManagementEngine().generate(db, context)

    ai_result = ManagementRecommendationGenerator(db).generate(
        role=role, user_id=user_id, history_session_id=history_session_id,
        ward_patient_id=hist['ward_patient_id'], clinical_context=context,
        deterministic_suggestions=deterministic,
    )

    interp = db.execute(
        """
        SELECT id FROM gi_clinical_interpretation_run
        WHERE history_session_id = ? ORDER BY created_at DESC LIMIT 1
        """,
        (history_session_id,),
    ).fetchone()

    inv_plan = db.execute(
        """
        SELECT id FROM gi_investigation_plan
        WHERE history_session_id = ? ORDER BY created_at DESC LIMIT 1
        """,
        (history_session_id,),
    ).fetchone()

    cur = db.execute(
        """
        INSERT INTO gi_ai_management_plan (
            history_session_id, ward_patient_id, assessment_run_id,
            interpretation_run_id, investigation_plan_id,
            ai_session_uuid, provider_key, model_name, status,
            working_diagnoses_json, knowledge_sources_json, clinical_context_json, created_by
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            history_session_id, hist['ward_patient_id'], assessment['id'],
            interp['id'] if interp else None, inv_plan['id'] if inv_plan else None,
            ai_result['ai_session_uuid'], ai_result['provider_key'], ai_result['model_name'],
            PLAN_STATUS_DRAFT, json.dumps(working),
            json.dumps(context.get('knowledge_sources') or []),
            json.dumps(context), user_id,
        ),
    )
    plan_id = cur.lastrowid

    for item in deterministic:
        db.execute(
            """
            INSERT INTO gi_management_ai_suggestion (
                plan_id, history_session_id, ward_patient_id,
                suggestion_key, category, description, clinical_indication,
                related_diagnosis, supporting_evidence_json, knowledge_references_json,
                guideline_references_json, priority, confidence_indicator,
                ai_session_uuid, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                plan_id, history_session_id, hist['ward_patient_id'],
                item['suggestion_key'], item['category'], item['description'],
                item.get('clinical_indication'), item.get('related_diagnosis'),
                json.dumps(item.get('supporting_evidence') or []),
                json.dumps(item.get('knowledge_references') or []),
                json.dumps(item.get('guideline_references') or []),
                item.get('priority', 'recommended'),
                item.get('confidence_indicator', 'medium'),
                ai_result['ai_session_uuid'], SUGGESTION_STATUS_SUGGESTED,
            ),
        )

    db.commit()
    log_event(
        db, action=f'{AUDIT_PREFIX}.generation_completed',
        entity_type='ai_management_plan', entity_id=plan_id, user_id=user_id,
        details={'working_diagnoses': working, 'suggestion_count': len(deterministic)},
    )
    return get_plan(db, role=role, plan_id=plan_id)


def get_plan(db, *, role, plan_id: int) -> dict:
    require_management_plan_ai_view(role=role)
    row = db.execute('SELECT * FROM gi_ai_management_plan WHERE id = ?', (plan_id,)).fetchone()
    if not row:
        raise NotFoundError(f'No management plan {plan_id}')
    return plan_to_dict(row)


def get_latest_plan(db, *, role, history_session_id: int) -> dict | None:
    require_management_plan_ai_view(role=role)
    row = db.execute(
        """
        SELECT * FROM gi_ai_management_plan
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
    grouped = ManagementEngine().group_by_category(suggestions)
    return {'plan': plan, 'suggestions': suggestions, 'decisions': decisions, 'grouped': grouped}


def list_suggestions(db, *, role, plan_id: int) -> list[dict]:
    get_plan(db, role=role, plan_id=plan_id)
    rows = db.execute(
        'SELECT * FROM gi_management_ai_suggestion WHERE plan_id = ? ORDER BY id',
        (plan_id,),
    ).fetchall()
    return [suggestion_to_dict(r) for r in rows]


def accept_suggestion(db, *, role, user_id, suggestion_id, notes=None):
    require_management_plan_ai_use(role=role)
    s = _get_suggestion(db, suggestion_id)
    return _record_decision(
        db, user_id=user_id, suggestion=s, plan_id=s['plan_id'],
        history_session_id=s['history_session_id'], ward_patient_id=s['ward_patient_id'],
        category=s['category'], description=s['description'],
        original_description=s['description'], physician_status=DECISION_ACCEPTED, notes=notes,
    )


def reject_suggestion(db, *, role, user_id, suggestion_id, notes=None):
    require_management_plan_ai_use(role=role)
    s = _get_suggestion(db, suggestion_id)
    return _record_decision(
        db, user_id=user_id, suggestion=s, plan_id=s['plan_id'],
        history_session_id=s['history_session_id'], ward_patient_id=s['ward_patient_id'],
        category=s['category'], description=s['description'],
        original_description=s['description'], physician_status=DECISION_REJECTED, notes=notes,
    )


def modify_suggestion(db, *, role, user_id, suggestion_id, description=None, category=None, notes=None):
    require_management_plan_ai_use(role=role)
    s = _get_suggestion(db, suggestion_id)
    modified_fields = {}
    desc = description or s['description']
    cat = category or s['category']
    if description:
        modified_fields['description'] = description
    if category:
        modified_fields['category'] = category
    db.execute(
        'UPDATE gi_ai_management_plan SET status = ? WHERE id = ?',
        (PLAN_STATUS_MODIFIED, s['plan_id']),
    )
    return _record_decision(
        db, user_id=user_id, suggestion=s, plan_id=s['plan_id'],
        history_session_id=s['history_session_id'], ward_patient_id=s['ward_patient_id'],
        category=cat, description=desc, original_description=s['description'],
        physician_status=DECISION_MODIFIED, notes=notes, modified_fields=modified_fields,
    )


def add_manual_plan_item(db, *, role, user_id, history_session_id, description, category=None, notes=None):
    require_management_plan_ai_use(role=role)
    hist = history_service.get_session(db, history_session_id)
    plan = get_latest_plan(db, role=role, history_session_id=history_session_id)
    return _record_decision(
        db, user_id=user_id, suggestion=None,
        plan_id=plan['id'] if plan else None,
        history_session_id=history_session_id,
        ward_patient_id=hist['ward_patient_id'] if hist else None,
        category=category, description=description, original_description=None,
        physician_status=DECISION_MANUAL, notes=notes,
    )


def review_plan(db, *, role, plan_id: int) -> dict:
    get_plan(db, role=role, plan_id=plan_id)
    db.execute(
        'UPDATE gi_ai_management_plan SET status = ? WHERE id = ?',
        (PLAN_STATUS_REVIEWED, plan_id),
    )
    db.commit()
    return get_plan(db, role=role, plan_id=plan_id)


def approve_plan(db, *, role, user_id, plan_id: int) -> dict:
    require_management_plan_ai_use(role=role)
    db.execute(
        'UPDATE gi_ai_management_plan SET status = ? WHERE id = ?',
        (PLAN_STATUS_APPROVED, plan_id),
    )
    db.commit()
    log_event(
        db, action=f'{AUDIT_PREFIX}.plan_approved',
        entity_type='ai_management_plan', entity_id=plan_id, user_id=user_id,
    )
    return get_plan(db, role=role, plan_id=plan_id)


def reject_plan(db, *, role, user_id, plan_id: int, reason=None) -> dict:
    db.execute(
        'UPDATE gi_ai_management_plan SET status = ? WHERE id = ?',
        (PLAN_STATUS_REJECTED, plan_id),
    )
    db.commit()
    log_event(
        db, action=f'{AUDIT_PREFIX}.plan_rejected',
        entity_type='ai_management_plan', entity_id=plan_id, user_id=user_id,
        details={'reason': reason},
    )
    return get_plan(db, role=role, plan_id=plan_id)


def get_physician_decisions(db, *, role, history_session_id) -> list[dict]:
    require_management_plan_ai_view(role=role)
    rows = db.execute(
        """
        SELECT * FROM gi_physician_management_decision
        WHERE history_session_id = ? ORDER BY created_at DESC
        """,
        (history_session_id,),
    ).fetchall()
    return [decision_to_dict(r) for r in rows]


def _get_suggestion(db, suggestion_id) -> dict:
    row = db.execute(
        'SELECT * FROM gi_management_ai_suggestion WHERE id = ?', (suggestion_id,),
    ).fetchone()
    if not row:
        raise NotFoundError(f'No suggestion {suggestion_id}')
    return suggestion_to_dict(row)


def _record_decision(db, *, user_id, suggestion, plan_id, history_session_id, ward_patient_id,
                     category, description, original_description, physician_status,
                     notes=None, modified_fields=None) -> dict:
    cur = db.execute(
        """
        INSERT INTO gi_physician_management_decision (
            plan_id, suggestion_id, history_session_id, ward_patient_id,
            category, description, original_description, physician_status,
            physician_notes, modified_fields_json, created_by
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            plan_id, suggestion['id'] if suggestion else None,
            history_session_id, ward_patient_id,
            category, description, original_description, physician_status,
            notes, json.dumps(modified_fields or {}), user_id,
        ),
    )
    db.commit()
    return decision_to_dict(db.execute(
        'SELECT * FROM gi_physician_management_decision WHERE id = ?', (cur.lastrowid,),
    ).fetchone())


def plan_to_dict(row) -> dict:
    return {
        'id': row['id'],
        'history_session_id': row['history_session_id'],
        'ward_patient_id': row['ward_patient_id'],
        'assessment_run_id': row['assessment_run_id'],
        'interpretation_run_id': row['interpretation_run_id'],
        'investigation_plan_id': row['investigation_plan_id'],
        'ai_session_uuid': row['ai_session_uuid'],
        'provider_key': row['provider_key'],
        'model_name': row['model_name'],
        'status': row['status'],
        'working_diagnoses': json.loads(row['working_diagnoses_json'] or '[]'),
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
        'suggestion_key': data['suggestion_key'],
        'category': data['category'],
        'description': data['description'],
        'clinical_indication': data.get('clinical_indication'),
        'related_diagnosis': data.get('related_diagnosis'),
        'supporting_evidence': json.loads(data.get('supporting_evidence_json') or '[]'),
        'knowledge_references': json.loads(data.get('knowledge_references_json') or '[]'),
        'guideline_references': json.loads(data.get('guideline_references_json') or '[]'),
        'priority': data.get('priority'),
        'confidence_indicator': data.get('confidence_indicator'),
        'status': data.get('status'),
    }


def decision_to_dict(row) -> dict:
    return {
        'id': row['id'],
        'suggestion_id': row['suggestion_id'],
        'category': row['category'],
        'description': row['description'],
        'original_description': row['original_description'],
        'physician_status': row['physician_status'],
        'physician_notes': row['physician_notes'],
        'modified_fields': json.loads(row['modified_fields_json'] or '{}'),
        'created_at': row['created_at'],
    }
