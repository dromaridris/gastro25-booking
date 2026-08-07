"""Clinical AI orchestration services — infrastructure only."""

from __future__ import annotations

import time
from typing import Any

from app.engines import audit_engine
from app.extensions import db

from .ai_response_parser import AIResponseParser
from .ai_session import AISessionManager
from .config import ClinicalAIConfig
from .constants import AUDIT_ACTION_PREFIX, ALL_PROMPT_TYPES
from .context_builder import ContextBuilder, ContextRequest, default_context_builder
from .models import AIProviderRequest, AIRequestAuditRecord
from .permissions import require_configure, require_use, require_view
from .prompt_engine import PromptEngine
from .provider_factory import get_ai_provider


class ClinicalAIService:
    """
    Reusable AI infrastructure orchestrator.

    Sprint 9A: no medical reasoning, diagnosis, or treatment logic.
    """

    def __init__(
        self,
        *,
        context_builder: ContextBuilder | None = None,
        prompt_engine: PromptEngine | None = None,
        session_manager: AISessionManager | None = None,
        response_parser: AIResponseParser | None = None,
    ) -> None:
        self.context_builder = context_builder or default_context_builder()
        self.prompt_engine = prompt_engine or PromptEngine()
        self.session_manager = session_manager or AISessionManager()
        self.response_parser = response_parser or AIResponseParser()

    def get_configuration(self, user) -> dict[str, Any]:
        require_view(user)
        cfg = ClinicalAIConfig.from_app()
        return {
            "config": cfg.to_dict(),
            "supported_prompt_types": list(ALL_PROMPT_TYPES),
            "available_context_sources": self.context_builder.available_sources(),
            "active_provider": get_ai_provider().provider_key,
        }

    def update_configuration_preview(self, user, overrides: dict[str, Any]) -> dict[str, Any]:
        """HoD-only configuration inspection. Persisting provider secrets is out of scope for 9A."""
        require_configure(user)
        cfg = ClinicalAIConfig.from_app()
        data = cfg.to_dict()
        data["requested_overrides"] = overrides
        return data

    def execute_infrastructure_request(
        self,
        user,
        *,
        prompt_type: str,
        patient_id: int | None = None,
        encounter_id: int | None = None,
        context_sources: list[str] | None = None,
        topic_keys: list[str] | None = None,
        object_types: list[str] | None = None,
        provider_key: str | None = None,
    ) -> dict[str, Any]:
        """
        Run a provider call using assembled context + prompt blocks.

        Returns structured session metadata and parsed response shell.
        """
        require_use(user)
        cfg = ClinicalAIConfig.from_app()
        if provider_key:
            from .provider_factory import create_ai_provider

            provider = create_ai_provider(provider_key)
        else:
            provider = get_ai_provider()

        session = self.session_manager.create_session(
            user_id=user.id,
            prompt_type=prompt_type,
            provider_key=provider.provider_key,
            patient_id=patient_id,
            encounter_id=encounter_id,
            department_id=getattr(user, "department_id", 1),
        )
        self.session_manager.mark_running(session)

        context_payload = self.context_builder.build(
            ContextRequest(
                patient_id=patient_id,
                encounter_id=encounter_id,
                sources=context_sources or [],
                topic_keys=topic_keys or [],
                object_types=object_types or [],
            )
        )
        prompt_text = self.prompt_engine.build(prompt_type, context_payload=context_payload)
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
                session,
                response=provider_response,
                execution_duration_ms=duration_ms,
                prompt_text=prompt_text,
                store_prompt=cfg.log_prompts,
                store_response=cfg.log_responses,
            )
            self._write_audit(
                user=user,
                session=session,
                provider_response=provider_response,
                duration_ms=duration_ms,
                status="completed",
                patient_id=patient_id,
            )
            audit_engine.log(
                f"{AUDIT_ACTION_PREFIX}.request_completed",
                user=user,
                target_type="clinical_ai_session",
                target_id=session.id,
                details={
                    "session_uuid": session.session_uuid,
                    "provider": provider_response.provider_key,
                    "model": provider_response.model,
                    "prompt_type": prompt_type,
                    "duration_ms": duration_ms,
                    "token_usage": provider_response.token_usage,
                },
            )
            return {
                "session": self.session_manager.to_dict(
                    session, include_sensitive=cfg.log_prompts or cfg.log_responses
                ),
                "parsed_response": parsed.to_dict(),
                "context_sources_used": list(context_payload.keys()),
            }
        except Exception as exc:
            duration_ms = int((time.perf_counter() - started) * 1000)
            self.session_manager.fail_session(session, error=str(exc), execution_duration_ms=duration_ms)
            self._write_audit(
                user=user,
                session=session,
                provider_response=None,
                duration_ms=duration_ms,
                status="failed",
                patient_id=patient_id,
            )
            audit_engine.log(
                f"{AUDIT_ACTION_PREFIX}.request_failed",
                user=user,
                target_type="clinical_ai_session",
                target_id=session.id,
                details={"session_uuid": session.session_uuid, "error": str(exc)},
            )
            raise

    def _write_audit(
        self,
        *,
        user,
        session,
        provider_response,
        duration_ms: int,
        status: str,
        patient_id: int | None,
    ) -> None:
        record = AIRequestAuditRecord(
            session_uuid=session.session_uuid,
            user_id=user.id,
            patient_id=patient_id,
            provider_key=provider_response.provider_key if provider_response else session.provider_key,
            model_name=provider_response.model if provider_response else session.model_name,
            prompt_type=session.prompt_type,
            execution_duration_ms=duration_ms,
            status=status,
            department_id=getattr(user, "department_id", 1),
            created_by_id=user.id,
        )
        if provider_response:
            record.token_usage = provider_response.token_usage
        db.session.add(record)
        db.session.commit()
