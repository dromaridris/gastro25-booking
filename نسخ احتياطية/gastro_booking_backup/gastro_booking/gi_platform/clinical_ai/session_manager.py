"""AI Session lifecycle — SQLite adapter for gi_ai_session."""

from __future__ import annotations

import json
import uuid
from typing import Any

from gi_platform.clinical_ai.constants import (
    SESSION_COMPLETED, SESSION_FAILED, SESSION_OPEN, SESSION_PENDING, SESSION_RUNNING,
)
from gi_platform.clinical_ai.models import AISessionRecord, AIProviderResponse


def _row_to_session(row) -> AISessionRecord | None:
    if not row:
        return None
    keys = row.keys() if hasattr(row, 'keys') else ()
    return AISessionRecord(
        id=row['id'],
        session_uuid=row['session_uuid'] if 'session_uuid' in keys and row['session_uuid'] else str(row['id']),
        ward_patient_id=row['ward_patient_id'],
        history_session_id=row['history_session_id'] if 'history_session_id' in keys else None,
        created_by=row['created_by'],
        session_type=row['session_type'],
        prompt_type=row['prompt_type'] if 'prompt_type' in keys else None,
        provider_key=row['provider_key'] if 'provider_key' in keys and row['provider_key'] else 'stub',
        model_name=row['model_name'] if 'model_name' in keys else None,
        status=row['status'],
        execution_duration_ms=row['execution_duration_ms'] if 'execution_duration_ms' in keys else None,
        token_usage_json=row['token_usage_json'] if 'token_usage_json' in keys else None,
        response_metadata_json=row['response_metadata_json'] if 'response_metadata_json' in keys else None,
        prompt_text=row['prompt_text'] if 'prompt_text' in keys else None,
        response_text=row['response_text'] if 'response_text' in keys else None,
        created_at=row['created_at'],
        updated_at=row['updated_at'] if 'updated_at' in keys else None,
    )


class AISessionManager:
    def create_session(
        self,
        db,
        *,
        user_id: int | None = None,
        prompt_type: str | None = None,
        provider_key: str = 'stub',
        ward_patient_id: int | None = None,
        history_session_id: int | None = None,
        model_name: str | None = None,
        session_type: str = 'clinical_ai',
        status: str = SESSION_PENDING,
    ) -> AISessionRecord:
        session_uuid = str(uuid.uuid4())
        cur = db.execute(
            """
            INSERT INTO gi_ai_session (
                session_uuid, ward_patient_id, history_session_id, session_type,
                prompt_type, provider_key, model_name, status, created_by
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session_uuid, ward_patient_id, history_session_id, session_type,
                prompt_type, provider_key, model_name, status, user_id,
            ),
        )
        db.commit()
        return self.get_by_id(db, cur.lastrowid)

    def create_open_session(
        self,
        db,
        *,
        ward_patient_id: int | None = None,
        created_by: int | None = None,
        session_type: str = 'clinical_ai',
    ) -> AISessionRecord:
        return self.create_session(
            db,
            user_id=created_by,
            ward_patient_id=ward_patient_id,
            session_type=session_type,
            status=SESSION_OPEN,
        )

    def mark_running(self, db, session: AISessionRecord) -> AISessionRecord:
        db.execute(
            """
            UPDATE gi_ai_session SET status = ?, updated_at = datetime('now') WHERE id = ?
            """,
            (SESSION_RUNNING, session.id),
        )
        db.commit()
        session.status = SESSION_RUNNING
        return session

    def complete_session(
        self,
        db,
        session: AISessionRecord,
        *,
        response: AIProviderResponse,
        execution_duration_ms: int,
        prompt_text: str | None = None,
        store_prompt: bool = False,
        store_response: bool = False,
        parsed_response_json: str | None = None,
    ) -> AISessionRecord:
        token_usage_json = json.dumps(response.token_usage or {})
        response_metadata_json = json.dumps({
            'finish_reason': response.finish_reason,
            'provider_key': response.provider_key,
        })
        db.execute(
            """
            UPDATE gi_ai_session SET
                status = ?, execution_duration_ms = ?, model_name = ?,
                token_usage_json = ?, response_metadata_json = ?,
                prompt_text = ?, response_text = ?, updated_at = datetime('now')
            WHERE id = ?
            """,
            (
                SESSION_COMPLETED, execution_duration_ms, response.model,
                token_usage_json, response_metadata_json,
                prompt_text if store_prompt else None,
                response.content if store_response else None,
                session.id,
            ),
        )
        tokens_in = int((response.token_usage or {}).get('prompt_tokens', 0))
        tokens_out = int((response.token_usage or {}).get('completion_tokens', 0))
        db.execute(
            """
            INSERT INTO gi_ai_request_log (
                session_id, prompt_text, response_text, provider,
                tokens_in, tokens_out, prompt_type, execution_duration_ms,
                parsed_response_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session.id,
                prompt_text or '',
                response.content,
                response.provider_key,
                tokens_in,
                tokens_out,
                session.prompt_type,
                execution_duration_ms,
                parsed_response_json,
            ),
        )
        db.commit()
        return self.get_by_id(db, session.id)

    def fail_session(
        self,
        db,
        session: AISessionRecord,
        *,
        error: str,
        execution_duration_ms: int | None = None,
        prompt_text: str | None = None,
    ) -> AISessionRecord:
        response_metadata_json = json.dumps({'error': error})
        db.execute(
            """
            UPDATE gi_ai_session SET
                status = ?, execution_duration_ms = ?,
                response_metadata_json = ?, updated_at = datetime('now')
            WHERE id = ?
            """,
            (SESSION_FAILED, execution_duration_ms, response_metadata_json, session.id),
        )
        if prompt_text:
            db.execute(
                """
                INSERT INTO gi_ai_request_log (session_id, prompt_text, response_text, provider, prompt_type)
                VALUES (?, ?, ?, ?, ?)
                """,
                (session.id, prompt_text, f'[Error] {error}', session.provider_key, session.prompt_type),
            )
        db.commit()
        session.status = SESSION_FAILED
        return session

    def get_by_id(self, db, session_id: int) -> AISessionRecord | None:
        row = db.execute('SELECT * FROM gi_ai_session WHERE id = ?', (session_id,)).fetchone()
        return _row_to_session(row)

    def get_by_uuid(self, db, session_uuid: str) -> AISessionRecord | None:
        row = db.execute(
            'SELECT * FROM gi_ai_session WHERE session_uuid = ?', (session_uuid,),
        ).fetchone()
        return _row_to_session(row)

    def list_for_patient(self, db, ward_patient_id: int) -> list[AISessionRecord]:
        rows = db.execute(
            'SELECT * FROM gi_ai_session WHERE ward_patient_id = ? ORDER BY created_at DESC',
            (ward_patient_id,),
        ).fetchall()
        return [_row_to_session(r) for r in rows if _row_to_session(r)]

    def list_recent(self, db, limit: int = 50) -> list[AISessionRecord]:
        rows = db.execute(
            'SELECT * FROM gi_ai_session ORDER BY created_at DESC LIMIT ?', (limit,),
        ).fetchall()
        return [_row_to_session(r) for r in rows if _row_to_session(r)]

    def list_logs(self, db, session_id: int) -> list:
        return db.execute(
            'SELECT * FROM gi_ai_request_log WHERE session_id = ? ORDER BY id', (session_id,),
        ).fetchall()

    def to_dict(self, session: AISessionRecord, *, include_sensitive: bool = False) -> dict[str, Any]:
        data = {
            'id': session.id,
            'session_uuid': session.session_uuid,
            'ward_patient_id': session.ward_patient_id,
            'history_session_id': session.history_session_id,
            'created_by': session.created_by,
            'prompt_type': session.prompt_type,
            'provider_key': session.provider_key,
            'model_name': session.model_name,
            'status': session.status,
            'execution_duration_ms': session.execution_duration_ms,
            'token_usage': session.token_usage,
            'response_metadata': session.response_metadata,
            'created_at': session.created_at,
            'updated_at': session.updated_at,
        }
        if include_sensitive:
            data['prompt_text'] = session.prompt_text
            data['response_text'] = session.response_text
        return data
