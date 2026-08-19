"""AI history generation using Clinical AI infrastructure."""

from __future__ import annotations

import json
import time
from typing import Any

from gi_platform.audit_service import log_event
from gi_platform.clinical_ai.ai_response_parser import AIResponseParser
from gi_platform.clinical_ai.config import ClinicalAIConfig
from gi_platform.clinical_ai.constants import PROMPT_CLINICAL_REASONING
from gi_platform.clinical_ai.models import AIProviderRequest
from gi_platform.clinical_ai.prompt_blocks import PromptBlock, output_format_block, safety_guardrail_block
from gi_platform.clinical_ai.prompt_engine import PromptEngine
from gi_platform.clinical_ai.provider_factory import get_ai_provider
from gi_platform.clinical_ai.session_manager import AISessionManager
from gi_platform.clinical_history_ai.permissions import require_ai_generation


class HistoryAIGenerator:
    def __init__(self, db) -> None:
        self.db = db
        self.session_manager = AISessionManager()
        self.response_parser = AIResponseParser()

    def generate(
        self,
        *,
        role: str | None,
        user_id: int | None,
        ward_patient_id: int | None,
        history_session_id: int | None,
        composed_payload: dict[str, Any],
    ) -> dict[str, Any]:
        require_ai_generation(role=role)
        cfg = ClinicalAIConfig.from_env()
        provider = get_ai_provider()

        prompt_engine = PromptEngine()
        prompt_engine.register_blocks(
            PROMPT_CLINICAL_REASONING,
            [
                safety_guardrail_block(),
                PromptBlock(
                    block_id='history_instruction',
                    category='task',
                    content=(
                        'Convert ONLY the supplied structured findings into professional medical '
                        'documentation. Do NOT invent symptoms, findings, or history not present '
                        'in the structured data. Leave sections empty if no data was recorded.'
                    ),
                ),
                PromptBlock(
                    block_id='structured_findings',
                    category='context',
                    content=json.dumps(composed_payload, indent=2),
                ),
                output_format_block(),
            ],
        )

        ai_session = self.session_manager.create_session(
            self.db,
            user_id=user_id,
            prompt_type=PROMPT_CLINICAL_REASONING,
            provider_key=provider.provider_key,
            ward_patient_id=ward_patient_id,
            history_session_id=history_session_id,
        )
        self.session_manager.mark_running(self.db, ai_session)

        context_payload = {'structured_findings': composed_payload}
        prompt_text = prompt_engine.build(PROMPT_CLINICAL_REASONING, context_payload=context_payload)
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
                ai_session,
                response=provider_response,
                execution_duration_ms=duration_ms,
                prompt_text=prompt_text,
                store_prompt=cfg.log_prompts,
                store_response=cfg.log_responses,
                parsed_response_json=json.dumps(parsed.to_dict()),
            )
            log_event(
                self.db,
                action='clinical_history_ai.generation_requested',
                entity_type='clinical_ai_session',
                entity_id=ai_session.id,
                user_id=user_id,
                details={
                    'session_uuid': ai_session.session_uuid,
                    'history_session_id': history_session_id,
                    'duration_ms': duration_ms,
                },
            )
            return {
                'ai_session_uuid': ai_session.session_uuid,
                'parsed_response': parsed.to_dict(),
                'raw_content': provider_response.content,
            }
        except Exception as exc:
            duration_ms = int((time.perf_counter() - started) * 1000)
            self.session_manager.fail_session(
                self.db, ai_session, error=str(exc),
                execution_duration_ms=duration_ms, prompt_text=prompt_text,
            )
            raise
