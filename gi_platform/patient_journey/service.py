"""Patient Journey AI orchestration — Gastro25."""

from __future__ import annotations

import json
from typing import Any

from gi_platform import history_service, patient_journey_service
from gi_platform.audit_service import log_event
from gi_platform.management_plan_ai import service as management_service
from gi_platform.patient_journey.catalogue_seed import seed_follow_up_rules_if_empty
from gi_platform.patient_journey.constants import (
    AUDIT_PREFIX, FOLLOWUP_STATUS_PLANNED, SUMMARY_STATUS_APPROVED,
    SUMMARY_STATUS_DRAFT, SUMMARY_STATUS_REJECTED,
)
from gi_platform.patient_journey.context_builder import JourneyContextBuilder
from gi_platform.patient_journey.followup_engine import FollowUpEngine, FollowUpSummaryGenerator
from gi_platform.patient_journey.permissions import require_journey_use, require_journey_view


class NotFoundError(LookupError):
    pass


class ValidationError(ValueError):
    pass


def get_journey_view(db, *, role, ward_patient_id: int, history_session_id: int | None = None) -> dict[str, Any]:
    require_journey_view(role=role)
    if not history_session_id:
        row = db.execute(
            """
            SELECT id FROM gi_history_session
            WHERE ward_patient_id = ? ORDER BY updated_at DESC LIMIT 1
            """,
            (ward_patient_id,),
        ).fetchone()
        history_session_id = row['id'] if row else None

    context = None
    follow_up_suggestions = []
    if history_session_id:
        context = JourneyContextBuilder().build(db, history_session_id=history_session_id, role=role)
        follow_up_suggestions = FollowUpEngine().suggest(db, context)

    timeline = _build_timeline(db, ward_patient_id=ward_patient_id)
    follow_ups = db.execute(
        """
        SELECT * FROM gi_follow_up_plan
        WHERE ward_patient_id = ? ORDER BY created_at DESC
        """,
        (ward_patient_id,),
    ).fetchall()

    summaries = []
    if history_session_id:
        summaries = db.execute(
            """
            SELECT * FROM gi_journey_summary_draft
            WHERE history_session_id = ? ORDER BY created_at DESC
            """,
            (history_session_id,),
        ).fetchall()

    return {
        'context': context,
        'timeline': timeline,
        'follow_up_suggestions': follow_up_suggestions,
        'follow_up_plans': [follow_up_to_dict(p) for p in follow_ups],
        'summaries': [summary_to_dict(s) for s in summaries],
    }


def create_follow_up_plan(db, *, role, user_id, history_session_id: int, **kwargs) -> dict:
    require_journey_use(role=role)
    seed_follow_up_rules_if_empty(db)

    hist = history_service.get_session(db, history_session_id)
    if not hist:
        raise NotFoundError(f'No history session {history_session_id}')

    mgmt = management_service.get_latest_plan(db, role=role, history_session_id=history_session_id)
    if not mgmt:
        raise ValidationError('Management plan required before follow-up planning.')

    context = JourneyContextBuilder().build(db, history_session_id=history_session_id, role=role)
    suggestions = FollowUpEngine().suggest(db, context)
    sug = suggestions[0] if suggestions else {}

    related_condition = kwargs.get('related_condition') or sug.get('related_condition')
    interval_days = kwargs.get('recommended_interval_days') or sug.get('recommended_interval_days')
    interval_text = kwargs.get('recommended_interval_text') or sug.get('recommended_interval_text')
    reason = kwargs.get('reason') or sug.get('reason')

    cur = db.execute(
        """
        INSERT INTO gi_follow_up_plan (
            history_session_id, ward_patient_id, management_plan_id,
            related_condition, responsible_user_id, recommended_interval_days,
            recommended_interval_text, reason, status, knowledge_references_json, created_by
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            history_session_id, hist['ward_patient_id'], mgmt['id'],
            related_condition, kwargs.get('responsible_user_id') or user_id,
            interval_days, interval_text, reason, FOLLOWUP_STATUS_PLANNED,
            json.dumps(sug.get('knowledge_references') or []), user_id,
        ),
    )
    db.commit()
    log_event(
        db, action=f'{AUDIT_PREFIX}.follow_up_created',
        entity_type='follow_up_plan', entity_id=cur.lastrowid, user_id=user_id,
    )
    return follow_up_to_dict(db.execute('SELECT * FROM gi_follow_up_plan WHERE id = ?', (cur.lastrowid,)).fetchone())


def generate_summary_draft(db, *, role, user_id, history_session_id: int) -> dict:
    require_journey_use(role=role)
    hist = history_service.get_session(db, history_session_id)
    if not hist:
        raise NotFoundError(f'No history session {history_session_id}')

    context = JourneyContextBuilder().build(db, history_session_id=history_session_id, role=role)
    ai_result = FollowUpSummaryGenerator(db).generate(
        role=role, user_id=user_id, history_session_id=history_session_id,
        ward_patient_id=hist['ward_patient_id'], clinical_context=context,
    )

    follow_up = db.execute(
        """
        SELECT id FROM gi_follow_up_plan
        WHERE history_session_id = ? ORDER BY created_at DESC LIMIT 1
        """,
        (history_session_id,),
    ).fetchone()

    cur = db.execute(
        """
        INSERT INTO gi_journey_summary_draft (
            history_session_id, ward_patient_id, follow_up_plan_id,
            ai_session_uuid, provider_key, model_name, draft_text, status,
            knowledge_references_json, missing_information_json, created_by
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            history_session_id, hist['ward_patient_id'],
            follow_up['id'] if follow_up else None,
            ai_result['ai_session_uuid'], ai_result['provider_key'], ai_result['model_name'],
            ai_result['draft_text'], SUMMARY_STATUS_DRAFT,
            json.dumps(ai_result.get('knowledge_references') or []),
            json.dumps(ai_result.get('missing_information') or []), user_id,
        ),
    )
    db.commit()
    return summary_to_dict(db.execute('SELECT * FROM gi_journey_summary_draft WHERE id = ?', (cur.lastrowid,)).fetchone())


def approve_summary(db, *, role, user_id, draft_id: int, approved_text: str | None = None) -> dict:
    require_journey_use(role=role)
    draft = _get_summary(db, draft_id)
    db.execute(
        """
        UPDATE gi_journey_summary_draft
        SET approved_text = ?, status = ? WHERE id = ?
        """,
        (approved_text or draft['draft_text'], SUMMARY_STATUS_APPROVED, draft_id),
    )
    db.commit()
    return summary_to_dict(db.execute('SELECT * FROM gi_journey_summary_draft WHERE id = ?', (draft_id,)).fetchone())


def reject_summary(db, *, role, user_id, draft_id: int, reason=None) -> dict:
    db.execute(
        'UPDATE gi_journey_summary_draft SET status = ? WHERE id = ?',
        (SUMMARY_STATUS_REJECTED, draft_id),
    )
    db.commit()
    return summary_to_dict(db.execute('SELECT * FROM gi_journey_summary_draft WHERE id = ?', (draft_id,)).fetchone())


def _build_timeline(db, *, ward_patient_id: int) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for e in patient_journey_service.timeline_for_patient(db, ward_patient_id=ward_patient_id):
        items.append({
            'event_type': e['event_type'],
            'title': e['title'],
            'event_at': e['event_at'],
            'source_module': e.get('source_module'),
        })

    for row in db.execute(
        """
        SELECT id, created_at FROM gi_clinical_assessment_run
        WHERE ward_patient_id = ? ORDER BY created_at
        """,
        (ward_patient_id,),
    ).fetchall():
        items.append({
            'event_type': 'assessment',
            'title': 'Differential assessment generated',
            'event_at': row['created_at'],
            'source_module': 'clinical_assessment',
        })

    for row in db.execute(
        """
        SELECT id, signed_at FROM gi_signed_clinical_document
        WHERE ward_patient_id = ? ORDER BY signed_at
        """,
        (ward_patient_id,),
    ).fetchall():
        items.append({
            'event_type': 'documentation',
            'title': 'Clinical document signed',
            'event_at': row['signed_at'],
            'source_module': 'documentation_ai',
        })

    return sorted(items, key=lambda x: x.get('event_at') or '')


def _get_summary(db, draft_id) -> dict:
    row = db.execute('SELECT * FROM gi_journey_summary_draft WHERE id = ?', (draft_id,)).fetchone()
    if not row:
        raise NotFoundError(f'No summary draft {draft_id}')
    return summary_to_dict(row)


def follow_up_to_dict(row) -> dict:
    data = dict(row)
    return {
        'id': data['id'],
        'history_session_id': data['history_session_id'],
        'ward_patient_id': data['ward_patient_id'],
        'management_plan_id': data.get('management_plan_id'),
        'related_condition': data.get('related_condition'),
        'recommended_interval_days': data.get('recommended_interval_days'),
        'recommended_interval_text': data.get('recommended_interval_text'),
        'reason': data.get('reason'),
        'status': data.get('status'),
        'created_at': data.get('created_at'),
    }


def summary_to_dict(row) -> dict:
    data = dict(row)
    return {
        'id': data['id'],
        'history_session_id': data['history_session_id'],
        'draft_text': data.get('draft_text'),
        'approved_text': data.get('approved_text'),
        'status': data.get('status'),
        'ai_session_uuid': data.get('ai_session_uuid'),
        'missing_information': json.loads(data.get('missing_information_json') or '[]'),
        'created_at': data.get('created_at'),
    }
