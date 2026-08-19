"""AI document generator using Sprint 9A infrastructure."""

from __future__ import annotations

import json
import time
from typing import Any

from app.engines import audit_engine
from app.modules.clinical_ai.ai_response_parser import AIResponseParser
from app.modules.clinical_ai.ai_session import AISessionManager
from app.modules.clinical_ai.config import ClinicalAIConfig
from app.modules.clinical_ai.constants import PROMPT_REPORT_ASSISTANCE
from app.modules.clinical_ai.models import AIProviderRequest
from app.modules.clinical_ai.prompt_blocks import PromptBlock, output_format_block, safety_guardrail_block
from app.modules.clinical_ai.prompt_engine import PromptEngine
from app.modules.clinical_ai.provider_factory import get_ai_provider
from app.modules.documentation_ai.permissions import require_documentation_use
from app.modules.documentation_ai.section_builder import SectionBuilder
from app.modules.documentation_ai.templates import DocumentationTemplate


class DocumentGenerator:
    """Generates structured document drafts — physician must approve before signing."""

    def __init__(self) -> None:
        self.section_builder = SectionBuilder()
        self.session_manager = AISessionManager()
        self.response_parser = AIResponseParser()

    def generate_sections(
        self, template: DocumentationTemplate, context: dict[str, Any]
    ) -> list[dict[str, Any]]:
        sections_def = sorted(template.sections, key=lambda s: s.get("order", 0))
        built: list[dict[str, Any]] = []
        for section_def in sections_def:
            key = section_def["key"]
            result = self.section_builder.build_section(key, context)
            built.append(
                {
                    "section_key": key,
                    "section_name": section_def.get("name", key),
                    "sort_order": section_def.get("order", 0),
                    "is_required": section_def.get("required", True),
                    **result,
                }
            )
        return built

    def run_ai_session(
        self,
        acting_user,
        *,
        encounter_id: int,
        patient_id: int,
        template: DocumentationTemplate,
        context: dict[str, Any],
        sections: list[dict[str, Any]],
    ) -> dict[str, Any]:
        require_documentation_use(acting_user)
        cfg = ClinicalAIConfig.from_app()
        provider = get_ai_provider()

        prompt_engine = PromptEngine()
        prompt_engine.register_blocks(
            PROMPT_REPORT_ASSISTANCE,
            [
                safety_guardrail_block(),
                PromptBlock(
                    block_id="documentation_instruction",
                    category="task",
                    content=(
                        "Assist with clinical documentation draft for physician review only. "
                        "Do NOT invent clinical information. Use only supplied structured context. "
                        "Do NOT finalize, sign, or modify official medical records. "
                        "Flag missing information clearly. Document type: "
                        f"{template.document_type}."
                    ),
                ),
                PromptBlock(block_id="clinical_context", category="context", content=json.dumps(context, indent=2)),
                PromptBlock(block_id="sections", category="context", content=json.dumps(sections, indent=2)),
                output_format_block(),
            ],
        )

        ai_session = self.session_manager.create_session(
            user_id=acting_user.id,
            prompt_type=PROMPT_REPORT_ASSISTANCE,
            provider_key=provider.provider_key,
            patient_id=patient_id,
            encounter_id=encounter_id,
            department_id=getattr(acting_user, "department_id", 1),
        )
        self.session_manager.mark_running(ai_session)

        prompt_text = prompt_engine.build(
            PROMPT_REPORT_ASSISTANCE,
            context_payload={"clinical_context": context, "sections": sections},
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
                ai_session,
                response=provider_response,
                execution_duration_ms=duration_ms,
                prompt_text=prompt_text,
                store_prompt=cfg.log_prompts,
                store_response=cfg.log_responses,
            )
            audit_engine.log(
                action="documentation_ai.ai_generation",
                user=acting_user,
                target_type="clinical_ai_session",
                target_id=ai_session.id,
                details={
                    "session_uuid": ai_session.session_uuid,
                    "encounter_id": encounter_id,
                    "template_key": template.template_key,
                    "provider": provider.provider_key,
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
