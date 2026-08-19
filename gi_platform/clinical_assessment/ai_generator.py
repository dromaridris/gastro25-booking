"""Assessment AI generation via clinical_ai stack."""

from __future__ import annotations

import json
import time
from typing import Any

from gi_platform.audit_service import log_event
from gi_platform.clinical_ai.ai_response_parser import AIResponseParser
from gi_platform.clinical_ai.config import ClinicalAIConfig
from gi_platform.clinical_ai.constants import PROMPT_DIFFERENTIAL_DIAGNOSIS
from gi_platform.clinical_ai.models import AIProviderRequest
from gi_platform.clinical_ai.prompt_blocks import PromptBlock, output_format_block, safety_guardrail_block
from gi_platform.clinical_ai.prompt_engine import PromptEngine
from gi_platform.clinical_ai.provider_factory import get_ai_provider
from gi_platform.clinical_ai.session_manager import AISessionManager
from gi_platform.clinical_assessment.permissions import require_assessment_use


class AssessmentAIGenerator:
    def __init__(self, db) -> None:
        self.db = db
        self.session_manager = AISessionManager()
        self.response_parser = AIResponseParser()

    def generate(
        self,
        *,
        role: str | None,
        user_id: int | None,
        history_session_id: int,
        ward_patient_id: int | None,
        clinical_context: dict[str, Any],
        deterministic_suggestions: list[dict[str, Any]],
    ) -> dict[str, Any]:
        require_assessment_use(role=role)
        cfg = ClinicalAIConfig.from_env()
        provider = get_ai_provider()

        prompt_engine = PromptEngine()
        prompt_engine.register_blocks(
            PROMPT_DIFFERENTIAL_DIAGNOSIS,
            [
                safety_guardrail_block(),
                PromptBlock(
                    block_id='differential_instruction', category='task',
                    content=(
                        'Organize possible differential diagnoses for physician review only. '
                        'Do NOT confirm diagnosis or recommend treatment.'
                    ),
                ),
                PromptBlock(block_id='clinical_context', category='context',
                            content=json.dumps(clinical_context, indent=2)),
                PromptBlock(block_id='deterministic_suggestions', category='context',
                            content=json.dumps(deterministic_suggestions, indent=2)),
                output_format_block(),
            ],
        )

        ai_session = self.session_manager.create_session(
            self.db, user_id=user_id, prompt_type=PROMPT_DIFFERENTIAL_DIAGNOSIS,
            provider_key=provider.provider_key, ward_patient_id=ward_patient_id,
            history_session_id=history_session_id,
        )
        self.session_manager.mark_running(self.db, ai_session)
        prompt_text = prompt_engine.build(
            PROMPT_DIFFERENTIAL_DIAGNOSIS,
            context_payload={'clinical_context': clinical_context},
        )
        started = time.perf_counter()
        try:
            provider_response = provider.complete(
                AIProviderRequest(prompt=prompt_text, max_tokens=cfg.max_tokens, temperature=cfg.temperature),
                config=cfg,
            )
            duration_ms = int((time.perf_counter() - started) * 1000)
            parsed = self.response_parser.parse(provider_response.content)
            self.session_manager.complete_session(
                self.db, ai_session, response=provider_response,
                execution_duration_ms=duration_ms, prompt_text=prompt_text,
                store_prompt=cfg.log_prompts, store_response=cfg.log_responses,
                parsed_response_json=json.dumps(parsed.to_dict()),
            )
            log_event(
                self.db, action='clinical_assessment.ai_generation',
                entity_type='clinical_ai_session', entity_id=ai_session.id, user_id=user_id,
                details={'session_uuid': ai_session.session_uuid, 'history_session_id': history_session_id},
            )
            return {
                'ai_session_uuid': ai_session.session_uuid,
                'provider_key': provider.provider_key,
                'model_name': provider_response.model,
                'parsed_response': parsed.to_dict(),
            }
        except Exception as exc:
            self.session_manager.fail_session(
                self.db, ai_session, error=str(exc),
                execution_duration_ms=int((time.perf_counter() - started) * 1000),
                prompt_text=prompt_text,
            )
            raise
