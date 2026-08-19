"""Clinical Interpretation orchestration — Gastro25."""

from __future__ import annotations

import json
from typing import Any

from gi_platform.audit_service import log_event
from gi_platform.clinical_assessment import service as assessment_service
from gi_platform.clinical_interpretation.ai_generator import InterpretationAIGenerator
from gi_platform.clinical_interpretation.constants import (
    AUDIT_PREFIX, DECISION_ACCEPTED, DECISION_MANUAL, DECISION_REJECTED,
    FINDING_STATUS_SUGGESTED, RUN_STATUS_GENERATED, RUN_STATUS_REVIEWED,
)
from gi_platform.clinical_interpretation.context_builder import InterpretationContextBuilder
from gi_platform.clinical_interpretation.diagnostic_update import DiagnosticUpdateEngine
from gi_platform.clinical_interpretation.interpretation_engine import InterpretationEngine
from gi_platform.clinical_interpretation.permissions import require_interpretation_use, require_interpretation_view


class NotFoundError(LookupError):
    pass


class ValidationError(ValueError):
    pass


def generate_interpretation(db, *, role, user_id, history_session_id: int) -> dict:
    require_interpretation_use(role=role)
    assessment = assessment_service.get_latest_run(db, role=role, history_session_id=history_session_id)
    if not assessment:
        raise ValidationError('Differential assessment required before clinical interpretation.')

    context = InterpretationContextBuilder().build(db, history_session_id=history_session_id, role=role)
    if not context.get('laboratory_results'):
        raise ValidationError('No laboratory results available to interpret.')

    findings = InterpretationEngine().generate(context)
    hist = db.execute('SELECT ward_patient_id FROM gi_history_session WHERE id = ?', (history_session_id,)).fetchone()

    ai_result = InterpretationAIGenerator(db).generate(
        role=role, user_id=user_id, history_session_id=history_session_id,
        ward_patient_id=hist['ward_patient_id'] if hist else None,
        clinical_context=context, deterministic_findings=findings,
    )
    updates = DiagnosticUpdateEngine().generate(
        previous_differential=context.get('previous_differential_snapshot') or [],
        interpretation_findings=findings,
    )

    cur = db.execute(
        """
        INSERT INTO gi_clinical_interpretation_run (
            history_session_id, ward_patient_id, assessment_run_id,
            ai_session_uuid, provider_key, model_name, status,
            clinical_data_sources_json, previous_differential_snapshot_json,
            knowledge_sources_json, clinical_context_json, created_by
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            history_session_id, hist['ward_patient_id'] if hist else None, assessment['id'],
            ai_result['ai_session_uuid'], ai_result['provider_key'], ai_result['model_name'],
            RUN_STATUS_GENERATED,
            json.dumps(context.get('clinical_data_sources') or []),
            json.dumps(context.get('previous_differential_snapshot') or []),
            json.dumps(context.get('knowledge_sources') or []),
            json.dumps(context), user_id,
        ),
    )
    run_id = cur.lastrowid

    for item in findings:
        db.execute(
            """
            INSERT INTO gi_interpretation_finding (
                run_id, history_session_id, ward_patient_id, finding_title, source_type,
                source_data_json, explanation, significance, differential_impact,
                related_diagnosis, supporting_diagnoses_json, contradicting_diagnoses_json,
                missing_information_json, confidence_indicator, ai_session_uuid, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id, history_session_id, hist['ward_patient_id'] if hist else None,
                item['finding_title'], item['source_type'], json.dumps(item.get('source_data') or {}),
                item.get('explanation'), item.get('significance'), item.get('differential_impact'),
                item.get('related_diagnosis'),
                json.dumps(item.get('supporting_diagnoses') or []),
                json.dumps(item.get('contradicting_diagnoses') or []),
                json.dumps(item.get('missing_information') or []),
                item.get('confidence_indicator', 'medium'),
                ai_result['ai_session_uuid'], FINDING_STATUS_SUGGESTED,
            ),
        )

    for item in updates:
        db.execute(
            """
            INSERT INTO gi_differential_update_record (
                run_id, history_session_id, ward_patient_id, diagnosis_name,
                previous_confidence, previous_category, update_direction, reasoning,
                related_finding_title
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id, history_session_id, hist['ward_patient_id'] if hist else None,
                item['diagnosis_name'], item.get('previous_confidence'), item.get('previous_category'),
                item['update_direction'], item.get('reasoning'), item.get('related_finding_title'),
            ),
        )

    db.commit()
    log_event(
        db, action=f'{AUDIT_PREFIX}.generation_completed',
        entity_type='clinical_interpretation_run', entity_id=run_id, user_id=user_id,
        details={'finding_count': len(findings), 'update_count': len(updates)},
    )
    return get_run(db, role=role, run_id=run_id)


def get_run(db, *, role, run_id) -> dict:
    require_interpretation_view(role=role)
    row = db.execute('SELECT * FROM gi_clinical_interpretation_run WHERE id = ?', (run_id,)).fetchone()
    if not row:
        raise NotFoundError(f'No interpretation run {run_id}')
    return run_to_dict(row)


def get_interpretation_view(db, *, role, history_session_id) -> dict[str, Any]:
    row = db.execute(
        """
        SELECT * FROM gi_clinical_interpretation_run
        WHERE history_session_id = ? ORDER BY created_at DESC LIMIT 1
        """,
        (history_session_id,),
    ).fetchone()
    if not row:
        return {'run': None, 'findings': [], 'differential_updates': [], 'decisions': []}
    run = run_to_dict(row)
    findings = [finding_to_dict(r) for r in db.execute(
        'SELECT * FROM gi_interpretation_finding WHERE run_id = ? ORDER BY id', (run['id'],),
    ).fetchall()]
    updates = [update_to_dict(r) for r in db.execute(
        'SELECT * FROM gi_differential_update_record WHERE run_id = ? ORDER BY id', (run['id'],),
    ).fetchall()]
    decisions = [decision_to_dict(r) for r in db.execute(
        """
        SELECT * FROM gi_physician_interpretation_decision
        WHERE history_session_id = ? ORDER BY created_at DESC
        """,
        (history_session_id,),
    ).fetchall()]
    return {
        'run': run,
        'findings': findings,
        'differential_updates': updates,
        'decisions': decisions,
        'previous_differential_snapshot': run.get('previous_differential_snapshot') or [],
    }


def accept_finding(db, *, role, user_id, finding_id, notes=None):
    require_interpretation_use(role=role)
    f = db.execute('SELECT * FROM gi_interpretation_finding WHERE id = ?', (finding_id,)).fetchone()
    if not f:
        raise NotFoundError(f'No finding {finding_id}')
    return _record_decision(
        db, user_id=user_id, run_id=f['run_id'], finding_id=finding_id,
        history_session_id=f['history_session_id'], ward_patient_id=f['ward_patient_id'],
        finding_title=f['finding_title'], original_title=f['finding_title'],
        physician_status=DECISION_ACCEPTED, notes=notes,
    )


def reject_finding(db, *, role, user_id, finding_id, notes=None):
    require_interpretation_use(role=role)
    f = db.execute('SELECT * FROM gi_interpretation_finding WHERE id = ?', (finding_id,)).fetchone()
    if not f:
        raise NotFoundError(f'No finding {finding_id}')
    return _record_decision(
        db, user_id=user_id, run_id=f['run_id'], finding_id=finding_id,
        history_session_id=f['history_session_id'], ward_patient_id=f['ward_patient_id'],
        finding_title=f['finding_title'], original_title=f['finding_title'],
        physician_status=DECISION_REJECTED, notes=notes,
    )


def _record_decision(db, *, user_id, run_id, finding_id, history_session_id, ward_patient_id,
                     finding_title, original_title, physician_status, notes=None) -> dict:
    cur = db.execute(
        """
        INSERT INTO gi_physician_interpretation_decision (
            run_id, finding_id, history_session_id, ward_patient_id,
            finding_title, original_finding_title, physician_status, physician_notes, created_by
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            run_id, finding_id, history_session_id, ward_patient_id,
            finding_title, original_title, physician_status, notes, user_id,
        ),
    )
    db.commit()
    return decision_to_dict(db.execute(
        'SELECT * FROM gi_physician_interpretation_decision WHERE id = ?', (cur.lastrowid,),
    ).fetchone())


def run_to_dict(row) -> dict:
    return {
        'id': row['id'],
        'history_session_id': row['history_session_id'],
        'assessment_run_id': row['assessment_run_id'],
        'ai_session_uuid': row['ai_session_uuid'],
        'provider_key': row['provider_key'],
        'model_name': row['model_name'],
        'status': row['status'],
        'clinical_data_sources': json.loads(row['clinical_data_sources_json'] or '[]'),
        'previous_differential_snapshot': json.loads(row['previous_differential_snapshot_json'] or '[]'),
        'created_at': row['created_at'],
    }


def finding_to_dict(row) -> dict:
    return {
        'id': row['id'],
        'finding_title': row['finding_title'],
        'source_type': row['source_type'],
        'source_data': json.loads(row['source_data_json'] or '{}'),
        'explanation': row['explanation'],
        'significance': row['significance'],
        'differential_impact': row['differential_impact'],
        'related_diagnosis': row['related_diagnosis'],
        'supporting_diagnoses': json.loads(row['supporting_diagnoses_json'] or '[]'),
        'contradicting_diagnoses': json.loads(row['contradicting_diagnoses_json'] or '[]'),
        'missing_information': json.loads(row['missing_information_json'] or '[]'),
        'confidence_indicator': row['confidence_indicator'],
        'status': row['status'],
    }


def update_to_dict(row) -> dict:
    return {
        'id': row['id'],
        'diagnosis_name': row['diagnosis_name'],
        'previous_confidence': row['previous_confidence'],
        'previous_category': row['previous_category'],
        'update_direction': row['update_direction'],
        'reasoning': row['reasoning'],
        'related_finding_title': row['related_finding_title'],
    }


def decision_to_dict(row) -> dict:
    return {
        'id': row['id'],
        'finding_id': row['finding_id'],
        'finding_title': row['finding_title'],
        'physician_status': row['physician_status'],
        'physician_notes': row['physician_notes'],
        'created_at': row['created_at'],
    }
