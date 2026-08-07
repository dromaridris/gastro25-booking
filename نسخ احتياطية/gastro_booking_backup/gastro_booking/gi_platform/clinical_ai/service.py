"""Clinical AI orchestration — Gastro25 SQLite integration."""

from __future__ import annotations

import json
import time
from typing import Any

from gi_platform.audit_service import log_event
from gi_platform.clinical_ai.ai_response_parser import AIResponseParser
from gi_platform.clinical_ai.config import ClinicalAIConfig
from gi_platform.clinical_ai.constants import AUDIT_ACTION_PREFIX, ALL_PROMPT_TYPES, PROMPT_CLINICAL_REASONING
from gi_platform.clinical_ai.context_builder import ContextBuilder, ContextRequest, default_context_builder
from gi_platform.clinical_ai.models import AIProviderRequest, AIRequestAuditRecord
from gi_platform.clinical_ai.permissions import require_configure, require_use, require_view
from gi_platform.clinical_ai.prompt_engine import PromptEngine
from gi_platform.clinical_ai.provider_factory import create_ai_provider, get_ai_provider
from gi_platform.clinical_ai.session_manager import AISessionManager


class ClinicalAIService:
    def __init__(
        self,
        db,
        *,
        context_builder: ContextBuilder | None = None,
        prompt_engine: PromptEngine | None = None,
        session_manager: AISessionManager | None = None,
        response_parser: AIResponseParser | None = None,
        app_config: dict | None = None,
    ) -> None:
        self.db = db
        self.context_builder = context_builder or default_context_builder(db)
        self.prompt_engine = prompt_engine or PromptEngine()
        self.session_manager = session_manager or AISessionManager()
        self.response_parser = response_parser or AIResponseParser()
        self.app_config = app_config or {}

    def get_configuration(self, *, role: str | None) -> dict[str, Any]:
        require_view(role=role)
        cfg = ClinicalAIConfig.from_env(self.app_config)
        return {
            'config': cfg.to_dict(),
            'supported_prompt_types': list(ALL_PROMPT_TYPES),
            'available_context_sources': self.context_builder.available_sources(),
            'active_provider': get_ai_provider().provider_key,
        }

    def update_configuration_preview(self, *, role: str | None, overrides: dict[str, Any]) -> dict[str, Any]:
        require_configure(role=role)
        cfg = ClinicalAIConfig.from_env(self.app_config)
        data = cfg.to_dict()
        data['requested_overrides'] = overrides
        return data

    def execute_infrastructure_request(
        self,
        *,
        role: str | None,
        user_id: int | None,
        prompt_type: str,
        ward_patient_id: int | None = None,
        history_session_id: int | None = None,
        context_sources: list[str] | None = None,
        topic_keys: list[str] | None = None,
        object_types: list[str] | None = None,
        provider_key: str | None = None,
        user_question: str | None = None,
    ) -> dict[str, Any]:
        require_use(role=role)
        cfg = ClinicalAIConfig.from_env(self.app_config)
        provider = create_ai_provider(provider_key) if provider_key else get_ai_provider()

        session = self.session_manager.create_session(
            self.db,
            user_id=user_id,
            prompt_type=prompt_type,
            provider_key=provider.provider_key,
            ward_patient_id=ward_patient_id,
            history_session_id=history_session_id,
        )
        self.session_manager.mark_running(self.db, session)

        context_payload = self.context_builder.build(
            ContextRequest(
                ward_patient_id=ward_patient_id,
                history_session_id=history_session_id,
                sources=context_sources or [],
                topic_keys=topic_keys or [],
                object_types=object_types or [],
            )
        )
        prompt_text = self.prompt_engine.build(
            prompt_type,
            context_payload=context_payload,
            user_question=user_question,
        )
        started = time.perf_counter()

        try:
            provider_response = provider.complete(
                AIProviderRequest(
                    prompt=prompt_text,
                    max_tokens=cfg.max_tokens,
                    temperature=cfg.temperature,
                ),
                config=cfg,
            )
            duration_ms = int((time.perf_counter() - started) * 1000)
            parsed = self.response_parser.parse(provider_response.content)
            self.session_manager.complete_session(
                self.db,
                session,
                response=provider_response,
                execution_duration_ms=duration_ms,
                prompt_text=prompt_text,
                store_prompt=cfg.log_prompts,
                store_response=cfg.log_responses,
                parsed_response_json=json.dumps(parsed.to_dict()),
            )
            self._write_audit(
                user_id=user_id,
                session=session,
                provider_response=provider_response,
                duration_ms=duration_ms,
                status='completed',
                ward_patient_id=ward_patient_id,
            )
            log_event(
                self.db,
                action=f'{AUDIT_ACTION_PREFIX}.request_completed',
                entity_type='clinical_ai_session',
                entity_id=session.id,
                user_id=user_id,
                details={
                    'session_uuid': session.session_uuid,
                    'provider': provider_response.provider_key,
                    'model': provider_response.model,
                    'prompt_type': prompt_type,
                    'duration_ms': duration_ms,
                    'token_usage': provider_response.token_usage,
                },
            )
            return {
                'session': self.session_manager.to_dict(
                    self.session_manager.get_by_id(self.db, session.id),
                    include_sensitive=cfg.log_prompts or cfg.log_responses,
                ),
                'parsed_response': parsed.to_dict(),
                'context_sources_used': list(context_payload.keys()),
            }
        except Exception as exc:
            duration_ms = int((time.perf_counter() - started) * 1000)
            self.session_manager.fail_session(
                self.db, session, error=str(exc),
                execution_duration_ms=duration_ms, prompt_text=prompt_text,
            )
            self._write_audit(
                user_id=user_id,
                session=session,
                provider_response=None,
                duration_ms=duration_ms,
                status='failed',
                ward_patient_id=ward_patient_id,
            )
            log_event(
                self.db,
                action=f'{AUDIT_ACTION_PREFIX}.request_failed',
                entity_type='clinical_ai_session',
                entity_id=session.id,
                user_id=user_id,
                details={'session_uuid': session.session_uuid, 'error': str(exc)},
            )
            raise

    def ask_session(
        self,
        *,
        role: str | None,
        user_id: int | None,
        session_id: int,
        prompt: str,
        prompt_type: str = PROMPT_CLINICAL_REASONING,
    ) -> dict[str, Any]:
        """HTML UI helper — runs prompt engine on an existing open session."""
        sess = self.session_manager.get_by_id(self.db, session_id)
        if not sess:
            raise ValueError('Session not found')
        return self.execute_infrastructure_request(
            role=role,
            user_id=user_id,
            prompt_type=prompt_type,
            ward_patient_id=sess.ward_patient_id,
            history_session_id=sess.history_session_id,
            user_question=prompt,
        )

    def _write_audit(
        self,
        *,
        user_id: int | None,
        session,
        provider_response,
        duration_ms: int,
        status: str,
        ward_patient_id: int | None,
    ) -> None:
        record = AIRequestAuditRecord(
            session_uuid=session.session_uuid,
            user_id=user_id or 0,
            ward_patient_id=ward_patient_id,
            provider_key=provider_response.provider_key if provider_response else session.provider_key,
            model_name=provider_response.model if provider_response else session.model_name,
            prompt_type=session.prompt_type or '',
            execution_duration_ms=duration_ms,
            status=status,
        )
        if provider_response:
            record.token_usage = provider_response.token_usage
        self.db.execute(
            """
            INSERT INTO gi_clinical_ai_audit (
                session_uuid, user_id, ward_patient_id, provider_key, model_name,
                prompt_type, execution_duration_ms, token_usage_json, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.session_uuid, record.user_id, record.ward_patient_id,
                record.provider_key, record.model_name, record.prompt_type,
                record.execution_duration_ms, record.token_usage_json, record.status,
            ),
        )
        self.db.commit()
