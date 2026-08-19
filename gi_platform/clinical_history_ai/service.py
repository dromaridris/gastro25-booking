"""Clinical History AI orchestration — Gastro25 SQLite."""

from __future__ import annotations

import json
from typing import Any

from gi_platform import history_service
from gi_platform.audit_service import log_event
from gi_platform.clinical_history_ai.ai_generator import HistoryAIGenerator
from gi_platform.clinical_history_ai.catalogue_seed import seed_guided_history_questions_if_empty
from gi_platform.clinical_history_ai.constants import (
    AUDIT_PREFIX,
    DRAFT_STATUS_APPROVED,
    DRAFT_STATUS_DRAFT,
    DRAFT_STATUS_MODIFIED,
    DRAFT_STATUS_REJECTED,
    DRAFT_STATUS_REVIEWED,
    SESSION_STATUS_APPROVED,
    SESSION_STATUS_COMPOSING,
    SESSION_STATUS_DISCARDED,
    SESSION_STATUS_DRAFT_READY,
    SESSION_STATUS_QUESTIONING,
)
from gi_platform.clinical_history_ai.history_composer import HistoryComposer
from gi_platform.clinical_history_ai.permissions import require_history_document, require_history_view
from gi_platform.clinical_history_ai.question_engine import HistoryQuestionEngine


class NotFoundError(LookupError):
    pass


class ValidationError(ValueError):
    pass


def ensure_questions_seeded(db) -> int:
    return seed_guided_history_questions_if_empty(db)


def start_guided_session(
    db,
    *,
    role: str | None,
    user_id: int | None,
    history_session_id: int,
    ward_patient_id: int | None = None,
) -> dict:
    require_history_document(role=role)
    ensure_questions_seeded(db)

    hist = history_service.get_session(db, history_session_id)
    if not hist:
        raise NotFoundError(f'No history session {history_session_id}')

    existing = db.execute(
        """
        SELECT * FROM gi_guided_history_session
        WHERE history_session_id = ? AND status NOT IN (?, ?)
        ORDER BY id DESC LIMIT 1
        """,
        (history_session_id, SESSION_STATUS_DISCARDED, SESSION_STATUS_APPROVED),
    ).fetchone()
    if existing:
        return dict(existing)

    prior = db.execute(
        'SELECT id FROM gi_guided_history_session WHERE history_session_id = ?',
        (history_session_id,),
    ).fetchone()
    if prior:
        db.execute(
            """
            UPDATE gi_guided_history_session SET
                status = ?, ai_session_uuid = NULL, presented_question_ids_json = NULL,
                chief_complaint = ?, normalized_complaint = ?, complaint_code = ?,
                updated_at = datetime('now')
            WHERE id = ?
            """,
            (
                SESSION_STATUS_QUESTIONING,
                hist['chief_complaint'], hist['chief_complaint'], hist['complaint_code'],
                prior['id'],
            ),
        )
        db.execute('DELETE FROM gi_guided_history_answer WHERE session_id = ?', (prior['id'],))
        db.commit()
        return get_session(db, role=role, session_id=prior['id'])

    wp_id = ward_patient_id or hist['ward_patient_id']
    cur = db.execute(
        """
        INSERT INTO gi_guided_history_session (
            history_session_id, ward_patient_id, chief_complaint, normalized_complaint,
            complaint_code, status, created_by
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            history_session_id, wp_id,
            hist['chief_complaint'], hist['chief_complaint'],
            hist['complaint_code'], SESSION_STATUS_QUESTIONING, user_id,
        ),
    )
    db.commit()
    session_id = cur.lastrowid
    log_event(
        db, action=f'{AUDIT_PREFIX}.session_started',
        entity_type='guided_history_session', entity_id=session_id,
        user_id=user_id, details={'history_session_id': history_session_id},
    )
    return get_session(db, role=role, session_id=session_id)


def get_session(db, *, role: str | None, session_id: int) -> dict:
    require_history_view(role=role)
    row = db.execute(
        'SELECT * FROM gi_guided_history_session WHERE id = ?', (session_id,),
    ).fetchone()
    if not row:
        raise NotFoundError(f'No guided history session {session_id}')
    return dict(row)


def get_session_for_history(db, *, role: str | None, history_session_id: int) -> dict | None:
    require_history_view(role=role)
    row = db.execute(
        """
        SELECT * FROM gi_guided_history_session
        WHERE history_session_id = ? AND status != ?
        ORDER BY id DESC LIMIT 1
        """,
        (history_session_id, SESSION_STATUS_DISCARDED),
    ).fetchone()
    return dict(row) if row else None


def get_next_questions(
    db,
    *,
    role: str | None,
    user_id: int | None,
    session_id: int,
    limit: int = 5,
    specialty_code: str | None = None,
) -> list[dict[str, Any]]:
    session_row = get_session(db, role=role, session_id=session_id)
    engine = HistoryQuestionEngine()
    questions = engine.next_questions(db, session_row, limit=limit, specialty_code=specialty_code)
    log_event(
        db, action=f'{AUDIT_PREFIX}.questions_presented',
        entity_type='guided_history_session', entity_id=session_id,
        user_id=user_id, details={'question_ids': [q['question_id'] for q in questions]},
    )
    return questions


def save_answers(
    db,
    *,
    role: str | None,
    user_id: int | None,
    session_id: int,
    answers: dict[str, str],
) -> dict:
    session_row = get_session(db, role=role, session_id=session_id)
    require_history_document(role=role)

    for question_id, response in answers.items():
        if response is None or str(response).strip() == '':
            continue
        existing = db.execute(
            """
            SELECT id FROM gi_guided_history_answer
            WHERE session_id = ? AND question_id = ?
            """,
            (session_id, question_id),
        ).fetchone()
        if existing:
            db.execute(
                """
                UPDATE gi_guided_history_answer SET
                    response_value = ?, response_display = ?,
                    answered_at = datetime('now'), answered_by = ?
                WHERE id = ?
                """,
                (str(response), str(response), user_id, existing['id']),
            )
        else:
            db.execute(
                """
                INSERT INTO gi_guided_history_answer (
                    session_id, history_session_id, ward_patient_id,
                    question_id, response_value, response_display, answered_by
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id, session_row['history_session_id'], session_row['ward_patient_id'],
                    question_id, str(response), str(response), user_id,
                ),
            )
        if session_row['history_session_id']:
            history_service.save_answer(
                db, session_row['history_session_id'], question_id, answer_text=str(response),
            )

    db.commit()
    log_event(
        db, action=f'{AUDIT_PREFIX}.questions_answered',
        entity_type='guided_history_session', entity_id=session_id,
        user_id=user_id, details={'question_ids': list(answers.keys())},
    )
    return get_session(db, role=role, session_id=session_id)


def generate_history_draft(
    db,
    *,
    role: str | None,
    user_id: int | None,
    session_id: int,
) -> dict:
    session_row = get_session(db, role=role, session_id=session_id)
    require_history_document(role=role)

    answer_rows = db.execute(
        'SELECT * FROM gi_guided_history_answer WHERE session_id = ? ORDER BY id',
        (session_id,),
    ).fetchall()
    if not answer_rows:
        raise ValidationError('At least one answer is required before generating history.')

    composed = HistoryComposer().compose(
        db, session_row, [dict(a) for a in answer_rows],
        chief_complaint=session_row['chief_complaint'],
    )
    ai_result = HistoryAIGenerator(db).generate(
        role=role,
        user_id=user_id,
        ward_patient_id=session_row['ward_patient_id'],
        history_session_id=session_row['history_session_id'],
        composed_payload=composed,
    )

    db.execute(
        """
        UPDATE gi_guided_history_session SET
            status = ?, ai_session_uuid = ?, updated_at = datetime('now')
        WHERE id = ?
        """,
        (SESSION_STATUS_DRAFT_READY, ai_result['ai_session_uuid'], session_id),
    )

    sections = composed['sections']
    ai_narrative = ai_result['parsed_response'].get('narrative')
    if ai_narrative and composed['structured_findings'] and sections.get('history_of_present_illness'):
        sections = dict(sections)
        sections['history_of_present_illness'] = ai_narrative

    cur = db.execute(
        """
        INSERT INTO gi_guided_history_draft (
            session_id, status, sections_json, source_answer_ids_json,
            ai_session_uuid, missing_information_json, structured_findings_json,
            learning_notes_json, created_by
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            session_id, DRAFT_STATUS_DRAFT,
            json.dumps(sections),
            json.dumps(composed['source_answer_ids']),
            ai_result['ai_session_uuid'],
            json.dumps(composed['missing_information']),
            json.dumps(composed['structured_findings']),
            json.dumps(composed['learning_notes']),
            user_id,
        ),
    )
    db.commit()
    draft_id = cur.lastrowid
    log_event(
        db, action=f'{AUDIT_PREFIX}.generation_requested',
        entity_type='guided_history_draft', entity_id=draft_id,
        user_id=user_id,
        details={'session_id': session_id, 'ai_session_uuid': ai_result['ai_session_uuid']},
    )
    return get_draft(db, role=role, draft_id=draft_id)


def get_draft(db, *, role: str | None, draft_id: int) -> dict:
    require_history_view(role=role)
    row = db.execute('SELECT * FROM gi_guided_history_draft WHERE id = ?', (draft_id,)).fetchone()
    if not row:
        raise NotFoundError(f'No draft {draft_id}')
    return draft_to_dict(row)


def review_draft(db, *, role: str | None, draft_id: int) -> dict:
    draft = get_draft(db, role=role, draft_id=draft_id)
    db.execute(
        "UPDATE gi_guided_history_draft SET status = ? WHERE id = ?",
        (DRAFT_STATUS_REVIEWED, draft_id),
    )
    db.commit()
    return get_draft(db, role=role, draft_id=draft_id)


def edit_draft(db, *, role: str | None, user_id: int | None, draft_id: int, sections: dict) -> dict:
    draft = get_draft(db, role=role, draft_id=draft_id)
    require_history_document(role=role)
    merged = dict(draft['sections'])
    merged.update({k: v for k, v in sections.items() if v is not None})
    db.execute(
        """
        UPDATE gi_guided_history_draft SET
            sections_json = ?, physician_edited_text = ?, status = ?
        WHERE id = ?
        """,
        (json.dumps(merged), _sections_to_text(merged), DRAFT_STATUS_MODIFIED, draft_id),
    )
    db.commit()
    log_event(
        db, action=f'{AUDIT_PREFIX}.draft_modified',
        entity_type='guided_history_draft', entity_id=draft_id,
        user_id=user_id, details={'session_id': draft['session_id']},
    )
    return get_draft(db, role=role, draft_id=draft_id)


def approve_draft(db, *, role: str | None, user_id: int | None, draft_id: int) -> dict:
    draft = get_draft(db, role=role, draft_id=draft_id)
    require_history_document(role=role)
    db.execute(
        "UPDATE gi_guided_history_draft SET status = ? WHERE id = ?",
        (DRAFT_STATUS_APPROVED, draft_id),
    )
    db.execute(
        """
        UPDATE gi_guided_history_session SET status = ?, updated_at = datetime('now')
        WHERE id = ?
        """,
        (SESSION_STATUS_APPROVED, draft['session_id']),
    )
    session_row = db.execute(
        'SELECT * FROM gi_guided_history_session WHERE id = ?', (draft['session_id'],),
    ).fetchone()
    if session_row and session_row['history_session_id']:
        history_service.save_narrative(
            db, session_row['history_session_id'],
            _sections_to_text(draft['sections']),
            draft['sections'],
        )
    db.commit()
    log_event(
        db, action=f'{AUDIT_PREFIX}.draft_approved',
        entity_type='guided_history_draft', entity_id=draft_id,
        user_id=user_id,
        details={'session_id': draft['session_id'], 'ai_session_uuid': draft.get('ai_session_uuid')},
    )
    return get_draft(db, role=role, draft_id=draft_id)


def reject_draft(db, *, role: str | None, user_id: int | None, draft_id: int, reason: str | None = None) -> dict:
    draft = get_draft(db, role=role, draft_id=draft_id)
    db.execute(
        "UPDATE gi_guided_history_draft SET status = ? WHERE id = ?",
        (DRAFT_STATUS_REJECTED, draft_id),
    )
    db.commit()
    log_event(
        db, action=f'{AUDIT_PREFIX}.draft_rejected',
        entity_type='guided_history_draft', entity_id=draft_id,
        user_id=user_id, details={'session_id': draft['session_id'], 'reason': reason},
    )
    return get_draft(db, role=role, draft_id=draft_id)


def regenerate_draft(db, *, role: str | None, user_id: int | None, session_id: int) -> dict:
    require_history_document(role=role)
    db.execute(
        "UPDATE gi_guided_history_draft SET status = ? WHERE session_id = ? AND status != ?",
        (DRAFT_STATUS_REJECTED, session_id, DRAFT_STATUS_APPROVED),
    )
    db.commit()
    return generate_history_draft(db, role=role, user_id=user_id, session_id=session_id)


def discard_session(db, *, role: str | None, user_id: int | None, session_id: int) -> dict:
    require_history_document(role=role)
    db.execute(
        """
        UPDATE gi_guided_history_session SET status = ?, updated_at = datetime('now')
        WHERE id = ?
        """,
        (SESSION_STATUS_DISCARDED, session_id),
    )
    db.commit()
    log_event(
        db, action=f'{AUDIT_PREFIX}.session_discarded',
        entity_type='guided_history_session', entity_id=session_id, user_id=user_id,
    )
    return get_session(db, role=role, session_id=session_id)


def session_to_dict(db, session_row: dict) -> dict[str, Any]:
    latest = db.execute(
        """
        SELECT * FROM gi_guided_history_draft
        WHERE session_id = ? ORDER BY created_at DESC LIMIT 1
        """,
        (session_row['id'],),
    ).fetchone()
    return {
        'id': session_row['id'],
        'history_session_id': session_row['history_session_id'],
        'ward_patient_id': session_row['ward_patient_id'],
        'chief_complaint': session_row['chief_complaint'],
        'normalized_complaint': session_row['normalized_complaint'],
        'complaint_code': session_row['complaint_code'],
        'status': session_row['status'],
        'ai_session_uuid': session_row['ai_session_uuid'],
        'latest_draft': draft_to_dict(latest) if latest else None,
    }


def draft_to_dict(row) -> dict[str, Any]:
    if isinstance(row, dict):
        data = row
    else:
        data = dict(row)
    return {
        'id': data['id'],
        'session_id': data['session_id'],
        'status': data['status'],
        'sections': json.loads(data['sections_json'] or '{}'),
        'source_answer_ids': json.loads(data.get('source_answer_ids_json') or '[]'),
        'ai_session_uuid': data.get('ai_session_uuid'),
        'missing_information': json.loads(data.get('missing_information_json') or '[]'),
        'structured_findings': json.loads(data.get('structured_findings_json') or '[]'),
        'learning_notes': json.loads(data.get('learning_notes_json') or '{}'),
        'physician_edited_text': data.get('physician_edited_text'),
    }


def _sections_to_text(sections: dict[str, str | None]) -> str:
    parts = []
    for key, value in sections.items():
        if value:
            parts.append(f"{key.replace('_', ' ').title()}:\n{value}")
    return '\n\n'.join(parts)
