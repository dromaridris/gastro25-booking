"""AI Session lifecycle management."""

from __future__ import annotations

import uuid
from typing import Any

from app.extensions import db

from .constants import SESSION_COMPLETED, SESSION_FAILED, SESSION_PENDING, SESSION_RUNNING
from .models import AISessionRecord, AIProviderResponse


class AISessionManager:
    def create_session(
        self,
        *,
        user_id: int,
        prompt_type: str,
        provider_key: str,
        patient_id: int | None = None,
        encounter_id: int | None = None,
        model_name: str | None = None,
        department_id: int = 1,
    ) -> AISessionRecord:
        record = AISessionRecord(
            session_uuid=str(uuid.uuid4()),
            user_id=user_id,
            patient_id=patient_id,
            encounter_id=encounter_id,
            prompt_type=prompt_type,
            provider_key=provider_key,
            model_name=model_name,
            status=SESSION_PENDING,
            department_id=department_id,
            created_by_id=user_id,
        )
        db.session.add(record)
        db.session.commit()
        return record

    def mark_running(self, session: AISessionRecord) -> AISessionRecord:
        session.status = SESSION_RUNNING
        db.session.commit()
        return session

    def complete_session(
        self,
        session: AISessionRecord,
        *,
        response: AIProviderResponse,
        execution_duration_ms: int,
        prompt_text: str | None = None,
        store_prompt: bool = False,
        store_response: bool = False,
    ) -> AISessionRecord:
        session.status = SESSION_COMPLETED
        session.execution_duration_ms = execution_duration_ms
        session.model_name = response.model
        session.token_usage = response.token_usage
        session.response_metadata = {
            "finish_reason": response.finish_reason,
            "provider_key": response.provider_key,
        }
        if store_prompt:
            session.prompt_text = prompt_text
        if store_response:
            session.response_text = response.content
        db.session.commit()
        return session

    def fail_session(
        self,
        session: AISessionRecord,
        *,
        error: str,
        execution_duration_ms: int | None = None,
    ) -> AISessionRecord:
        session.status = SESSION_FAILED
        session.execution_duration_ms = execution_duration_ms
        session.response_metadata = {"error": error}
        db.session.commit()
        return session

    def get_by_uuid(self, session_uuid: str) -> AISessionRecord | None:
        return AISessionRecord.query.filter_by(session_uuid=session_uuid, is_archived=False).first()

    def to_dict(self, session: AISessionRecord, *, include_sensitive: bool = False) -> dict[str, Any]:
        data = {
            "session_uuid": session.session_uuid,
            "user_id": session.user_id,
            "patient_id": session.patient_id,
            "encounter_id": session.encounter_id,
            "prompt_type": session.prompt_type,
            "provider_key": session.provider_key,
            "model_name": session.model_name,
            "status": session.status,
            "execution_duration_ms": session.execution_duration_ms,
            "token_usage": session.token_usage,
            "response_metadata": session.response_metadata,
            "created_at": session.created_at.isoformat() if session.created_at else None,
        }
        if include_sensitive:
            data["prompt_text"] = session.prompt_text
            data["response_text"] = session.response_text
        return data
