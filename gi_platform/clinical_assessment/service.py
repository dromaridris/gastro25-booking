"""Clinical Assessment orchestration — Gastro25 SQLite."""

from __future__ import annotations

import json
from typing import Any

from gi_platform import history_service
from gi_platform.audit_service import log_event
from gi_platform.clinical_assessment.ai_generator import AssessmentAIGenerator
from gi_platform.clinical_assessment.catalogue_seed import seed_diagnosis_rules_if_empty
from gi_platform.clinical_assessment.constants import (
    AUDIT_PREFIX, RUN_STATUS_FINALIZED, RUN_STATUS_GENERATED, STATUS_ACCEPTED,
    STATUS_CONFIRMED, STATUS_MANUAL, STATUS_MODIFIED, STATUS_REJECTED, STATUS_SUGGESTED,
    STATUS_SUSPECTED,
)
from gi_platform.clinical_assessment.context_builder import AssessmentContextBuilder
from gi_platform.clinical_assessment.differential_engine import DifferentialDiagnosisEngine
from gi_platform.clinical_assessment.permissions import require_assessment_use, require_assessment_view


class NotFoundError(LookupError):
    pass


class ValidationError(ValueError):
    pass


def generate_assessment(
    db, *, role: str | None, user_id: int | None, history_session_id: int,
) -> dict:
    require_assessment_use(role=role)
    seed_diagnosis_rules_if_empty(db)

    hist = history_service.get_session(db, history_session_id)
    if not hist:
        raise NotFoundError(f'No history session {history_session_id}')
    if not hist['complaint_code']:
        raise ValidationError('Chief complaint required before differential assessment.')

    answers = history_service.get_answers_map(db, history_session_id)
    if not answers:
        raise ValidationError('Clinical history answers required before differential assessment.')

    context = AssessmentContextBuilder().build(db, history_session_id=history_session_id)
    engine = DifferentialDiagnosisEngine()
    deterministic = engine.generate(db, context)

    ai_result = AssessmentAIGenerator(db).generate(
        role=role, user_id=user_id, history_session_id=history_session_id,
        ward_patient_id=hist['ward_patient_id'], clinical_context=context,
        deterministic_suggestions=deterministic,
    )

    cur = db.execute(
        """
        INSERT INTO gi_clinical_assessment_run (
            history_session_id, ward_patient_id, guided_history_session_id,
            ai_session_uuid, provider_key, model_name, status,
            knowledge_sources_json, clinical_context_json, created_by
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            history_session_id, hist['ward_patient_id'], None,
            ai_result['ai_session_uuid'], ai_result['provider_key'], ai_result['model_name'],
            RUN_STATUS_GENERATED, json.dumps(context.get('knowledge_sources') or []),
            json.dumps(context), user_id,
        ),
    )
    run_id = cur.lastrowid

    for item in deterministic:
        db.execute(
            """
            INSERT INTO gi_diagnosis_suggestion (
                assessment_run_id, history_session_id, ward_patient_id,
                diagnosis_name, category, priority_rank, supporting_findings_json,
                missing_information_json, contradicting_findings_json, inclusion_reason,
                confidence_indicator, knowledge_references_json, clinical_findings_used_json,
                ai_session_uuid, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id, history_session_id, hist['ward_patient_id'],
                item['diagnosis_name'], item['category'], item['priority_rank'],
                json.dumps(item.get('supporting_findings') or []),
                json.dumps(item.get('missing_information') or []),
                json.dumps(item.get('contradicting_findings') or []),
                item.get('inclusion_reason'),
                item.get('confidence_indicator', 'medium'),
                json.dumps(item.get('knowledge_references') or []),
                json.dumps(item.get('clinical_findings_used') or []),
                ai_result['ai_session_uuid'], STATUS_SUGGESTED,
            ),
        )

    db.commit()
    log_event(
        db, action=f'{AUDIT_PREFIX}.generation_completed',
        entity_type='clinical_assessment_run', entity_id=run_id, user_id=user_id,
        details={'history_session_id': history_session_id, 'suggestion_count': len(deterministic)},
    )
    return get_run(db, role=role, run_id=run_id)


def get_run(db, *, role: str | None, run_id: int) -> dict:
    require_assessment_view(role=role)
    row = db.execute('SELECT * FROM gi_clinical_assessment_run WHERE id = ?', (run_id,)).fetchone()
    if not row:
        raise NotFoundError(f'No assessment run {run_id}')
    return run_to_dict(row)


def get_latest_run(db, *, role: str | None, history_session_id: int) -> dict | None:
    require_assessment_view(role=role)
    row = db.execute(
        """
        SELECT * FROM gi_clinical_assessment_run
        WHERE history_session_id = ? ORDER BY created_at DESC LIMIT 1
        """,
        (history_session_id,),
    ).fetchone()
    return run_to_dict(row) if row else None


def list_suggestions(db, *, role: str | None, run_id: int) -> list[dict]:
    get_run(db, role=role, run_id=run_id)
    rows = db.execute(
        """
        SELECT * FROM gi_diagnosis_suggestion
        WHERE assessment_run_id = ? ORDER BY priority_rank
        """,
        (run_id,),
    ).fetchall()
    return [suggestion_to_dict(r) for r in rows]


def get_final_assessment(db, *, role: str | None, history_session_id: int) -> dict[str, Any]:
    run = get_latest_run(db, role=role, history_session_id=history_session_id)
    if not run:
        return {'run': None, 'suggestions': [], 'decisions': [], 'grouped': {}}
    suggestions = list_suggestions(db, role=role, run_id=run['id'])
    decisions = get_physician_decisions(db, role=role, history_session_id=history_session_id)
    grouped = DifferentialDiagnosisEngine().group_by_category(suggestions)
    return {'run': run, 'suggestions': suggestions, 'decisions': decisions, 'grouped': grouped}


def _record_decision(db, *, user_id, history_session_id, ward_patient_id, assessment_run_id,
                     suggestion_id, diagnosis_name, physician_status, original_name=None,
                     notes=None, modified_fields=None) -> dict:
    cur = db.execute(
        """
        INSERT INTO gi_physician_diagnosis_decision (
            history_session_id, ward_patient_id, assessment_run_id, suggestion_id,
            diagnosis_name, original_suggestion_name, physician_status, physician_notes,
            modified_fields_json, created_by
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            history_session_id, ward_patient_id, assessment_run_id, suggestion_id,
            diagnosis_name, original_name, physician_status, notes,
            json.dumps(modified_fields or {}), user_id,
        ),
    )
    db.commit()
    return decision_to_dict(db.execute(
        'SELECT * FROM gi_physician_diagnosis_decision WHERE id = ?', (cur.lastrowid,),
    ).fetchone())


def accept_suggestion(db, *, role, user_id, suggestion_id, notes=None):
    require_assessment_use(role=role)
    s = _get_suggestion(db, suggestion_id)
    return _record_decision(
        db, user_id=user_id, history_session_id=s['history_session_id'],
        ward_patient_id=s['ward_patient_id'], assessment_run_id=s['assessment_run_id'],
        suggestion_id=suggestion_id, diagnosis_name=s['diagnosis_name'],
        physician_status=STATUS_ACCEPTED, original_name=s['diagnosis_name'], notes=notes,
    )


def reject_suggestion(db, *, role, user_id, suggestion_id, notes=None):
    require_assessment_use(role=role)
    s = _get_suggestion(db, suggestion_id)
    return _record_decision(
        db, user_id=user_id, history_session_id=s['history_session_id'],
        ward_patient_id=s['ward_patient_id'], assessment_run_id=s['assessment_run_id'],
        suggestion_id=suggestion_id, diagnosis_name=s['diagnosis_name'],
        physician_status=STATUS_REJECTED, original_name=s['diagnosis_name'], notes=notes,
    )


def confirm_diagnosis(db, *, role, user_id, suggestion_id, notes=None):
    require_assessment_use(role=role)
    s = _get_suggestion(db, suggestion_id)
    db.execute(
        "UPDATE gi_clinical_assessment_run SET status = ? WHERE id = ?",
        (RUN_STATUS_FINALIZED, s['assessment_run_id']),
    )
    db.execute(
        "UPDATE gi_history_session SET final_diagnosis = ?, updated_at = datetime('now') WHERE id = ?",
        (s['diagnosis_name'], s['history_session_id']),
    )
    return _record_decision(
        db, user_id=user_id, history_session_id=s['history_session_id'],
        ward_patient_id=s['ward_patient_id'], assessment_run_id=s['assessment_run_id'],
        suggestion_id=suggestion_id, diagnosis_name=s['diagnosis_name'],
        physician_status=STATUS_CONFIRMED, original_name=s['diagnosis_name'], notes=notes,
    )


def add_manual_diagnosis(db, *, role, user_id, history_session_id, diagnosis_name, notes=None):
    require_assessment_use(role=role)
    hist = history_service.get_session(db, history_session_id)
    run = get_latest_run(db, role=role, history_session_id=history_session_id)
    return _record_decision(
        db, user_id=user_id, history_session_id=history_session_id,
        ward_patient_id=hist['ward_patient_id'] if hist else None,
        assessment_run_id=run['id'] if run else None, suggestion_id=None,
        diagnosis_name=diagnosis_name, physician_status=STATUS_MANUAL, notes=notes,
    )


def get_physician_decisions(db, *, role, history_session_id) -> list[dict]:
    require_assessment_view(role=role)
    rows = db.execute(
        """
        SELECT * FROM gi_physician_diagnosis_decision
        WHERE history_session_id = ? ORDER BY created_at DESC
        """,
        (history_session_id,),
    ).fetchall()
    return [decision_to_dict(r) for r in rows]


def _get_suggestion(db, suggestion_id) -> dict:
    row = db.execute('SELECT * FROM gi_diagnosis_suggestion WHERE id = ?', (suggestion_id,)).fetchone()
    if not row:
        raise NotFoundError(f'No suggestion {suggestion_id}')
    return suggestion_to_dict(row)


def run_to_dict(row) -> dict:
    return {
        'id': row['id'],
        'history_session_id': row['history_session_id'],
        'ward_patient_id': row['ward_patient_id'],
        'ai_session_uuid': row['ai_session_uuid'],
        'provider_key': row['provider_key'],
        'model_name': row['model_name'],
        'status': row['status'],
        'knowledge_sources': json.loads(row['knowledge_sources_json'] or '[]'),
        'created_at': row['created_at'],
    }


def suggestion_to_dict(row) -> dict:
    if isinstance(row, dict):
        data = row
    else:
        data = dict(row)
    return {
        'id': data['id'],
        'assessment_run_id': data['assessment_run_id'],
        'history_session_id': data.get('history_session_id'),
        'ward_patient_id': data.get('ward_patient_id'),
        'diagnosis_name': data['diagnosis_name'],
        'category': data['category'],
        'priority_rank': data['priority_rank'],
        'supporting_findings': json.loads(data.get('supporting_findings_json') or '[]'),
        'missing_information': json.loads(data.get('missing_information_json') or '[]'),
        'contradicting_findings': json.loads(data.get('contradicting_findings_json') or '[]'),
        'inclusion_reason': data.get('inclusion_reason'),
        'confidence_indicator': data.get('confidence_indicator'),
        'knowledge_references': json.loads(data.get('knowledge_references_json') or '[]'),
        'clinical_findings_used': json.loads(data.get('clinical_findings_used_json') or '[]'),
        'ai_session_uuid': data.get('ai_session_uuid'),
        'status': data.get('status'),
    }


def decision_to_dict(row) -> dict:
    return {
        'id': row['id'],
        'suggestion_id': row['suggestion_id'],
        'diagnosis_name': row['diagnosis_name'],
        'original_suggestion_name': row['original_suggestion_name'],
        'physician_status': row['physician_status'],
        'physician_notes': row['physician_notes'],
        'modified_fields': json.loads(row['modified_fields_json'] or '{}'),
        'created_at': row['created_at'],
    }
