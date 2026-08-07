"""AI recommendation generator using Sprint 9A infrastructure."""

from __future__ import annotations

import json
import time
from typing import Any

from app.engines import audit_engine
from app.modules.clinical_ai.ai_response_parser import AIResponseParser
from app.modules.clinical_ai.ai_session import AISessionManager
from app.modules.clinical_ai.config import ClinicalAIConfig
from app.modules.clinical_ai.constants import PROMPT_GUIDELINE_LOOKUP
from app.modules.clinical_ai.models import AIProviderRequest
from app.modules.clinical_ai.prompt_blocks import PromptBlock, output_format_block, safety_guardrail_block
from app.modules.clinical_ai.prompt_engine import PromptEngine
from app.modules.clinical_ai.provider_factory import get_ai_provider
from app.modules.investigation_planning.permissions import require_investigation_plan_use


class InvestigationRecommendationGenerator:
    """Uses 9A components — suggestions remain physician-reviewable only."""

    def __init__(self) -> None:
        self.session_manager = AISessionManager()
        self.response_parser = AIResponseParser()

    def generate(
        self,
        acting_user,
        *,
        encounter_id: int,
        patient_id: int,
        clinical_context: dict[str, Any],
        deterministic_suggestions: list[dict[str, Any]],
    ) -> dict[str, Any]:
        require_investigation_plan_use(acting_user)
        cfg = ClinicalAIConfig.from_app()
        provider = get_ai_provider()

        prompt_engine = PromptEngine()
        prompt_engine.register_blocks(
            PROMPT_GUIDELINE_LOOKUP,
            [
                safety_guardrail_block(),
                PromptBlock(
                    block_id="investigation_instruction",
                    category="task",
                    content=(
                        "Suggest investigations for physician review only. Do NOT order tests automatically. "
                        "Do NOT interpret results. Base suggestions on supplied clinical context, differential "
                        "diagnoses, and knowledge references. Group by initial assessment, confirmation, "
                        "exclusion, severity, and monitoring."
                    ),
                ),
                PromptBlock(
                    block_id="clinical_context",
                    category="context",
                    content=json.dumps(clinical_context, indent=2),
                ),
                PromptBlock(
                    block_id="deterministic_suggestions",
                    category="context",
                    content=json.dumps(deterministic_suggestions, indent=2),
                ),
                output_format_block(),
            ],
        )

        ai_session = self.session_manager.create_session(
            user_id=acting_user.id,
            prompt_type=PROMPT_GUIDELINE_LOOKUP,
            provider_key=provider.provider_key,
            patient_id=patient_id,
            encounter_id=encounter_id,
            department_id=getattr(acting_user, "department_id", 1),
        )
        self.session_manager.mark_running(ai_session)

        context_payload = {
            "clinical_context": clinical_context,
            "deterministic_suggestions": deterministic_suggestions,
        }
        prompt_text = prompt_engine.build(PROMPT_GUIDELINE_LOOKUP, context_payload=context_payload)
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
                ai_session,
                response=provider_response,
                execution_duration_ms=duration_ms,
                prompt_text=prompt_text,
                store_prompt=cfg.log_prompts,
                store_response=cfg.log_responses,
            )
            audit_engine.log(
                action="investigation_planning.ai_generation",
                user=acting_user,
                target_type="clinical_ai_session",
                target_id=ai_session.id,
                details={
                    "session_uuid": ai_session.session_uuid,
                    "encounter_id": encounter_id,
                    "provider": provider.provider_key,
                    "model": provider_response.model,
                    "duration_ms": duration_ms,
                },
            )
            return {
                "ai_session_uuid": ai_session.session_uuid,
                "provider_key": provider.provider_key,
                "model_name": provider_response.model,
                "parsed_response": parsed.to_dict(),
            }
        except Exception as exc:
            duration_ms = int((time.perf_counter() - started) * 1000)
            self.session_manager.fail_session(ai_session, error=str(exc), execution_duration_ms=duration_ms)
            raise
