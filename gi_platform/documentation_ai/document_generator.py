"""AI document generator — Gastro25."""

from __future__ import annotations

import json
import time
from typing import Any

from gi_platform.audit_service import log_event
from gi_platform.clinical_ai.ai_response_parser import AIResponseParser
from gi_platform.clinical_ai.config import ClinicalAIConfig
from gi_platform.clinical_ai.constants import PROMPT_REPORT_ASSISTANCE
from gi_platform.clinical_ai.models import AIProviderRequest
from gi_platform.clinical_ai.prompt_blocks import PromptBlock, output_format_block, safety_guardrail_block
from gi_platform.clinical_ai.prompt_engine import PromptEngine
from gi_platform.clinical_ai.provider_factory import get_ai_provider
from gi_platform.clinical_ai.session_manager import AISessionManager
from gi_platform.documentation_ai.permissions import require_documentation_use
from gi_platform.documentation_ai.section_builder import SectionBuilder


class DocumentGenerator:
    def __init__(self) -> None:
        self.section_builder = SectionBuilder()
        self.session_manager = AISessionManager()
        self.response_parser = AIResponseParser()

    def generate_sections(self, template: dict[str, Any], context: dict[str, Any]) -> list[dict[str, Any]]:
        sections_def = sorted(template['sections'], key=lambda s: s.get('order', 0))
        built: list[dict[str, Any]] = []
        for section_def in sections_def:
            key = section_def['key']
            result = self.section_builder.build_section(key, context)
            built.append({
                'section_key': key,
                'section_name': section_def.get('name', key),
                'sort_order': section_def.get('order', 0),
                'is_required': section_def.get('required', True),
                **result,
            })
        return built

    def run_ai_session(
        self, db, *, role, user_id, history_session_id, ward_patient_id,
        template: dict[str, Any], context: dict[str, Any], sections: list[dict[str, Any]],
    ) -> dict[str, Any]:
        require_documentation_use(role=role)
        cfg = ClinicalAIConfig.from_env()
        provider = get_ai_provider()
        prompt_engine = PromptEngine()
        prompt_engine.register_blocks(
            PROMPT_REPORT_ASSISTANCE,
            [
                safety_guardrail_block(),
                PromptBlock(
                    block_id='documentation_instruction', category='task',
                    content=(
                        'Assist with clinical documentation draft for physician review only. '
                        'Do NOT invent clinical information. Document type: '
                        f"{template['document_type']}."
                    ),
                ),
                PromptBlock(block_id='clinical_context', category='context',
                            content=json.dumps(context, indent=2)),
                PromptBlock(block_id='sections', category='context',
                            content=json.dumps(sections, indent=2)),
                output_format_block(),
            ],
        )
        ai_session = self.session_manager.create_session(
            db, user_id=user_id, prompt_type=PROMPT_REPORT_ASSISTANCE,
            provider_key=provider.provider_key, ward_patient_id=ward_patient_id,
            history_session_id=history_session_id,
        )
        self.session_manager.mark_running(db, ai_session)
        prompt_text = prompt_engine.build(
            PROMPT_REPORT_ASSISTANCE,
            context_payload={'clinical_context': context, 'sections': sections},
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
                db, ai_session, response=provider_response,
                execution_duration_ms=duration_ms, prompt_text=prompt_text,
                store_prompt=cfg.log_prompts, store_response=cfg.log_responses,
                parsed_response_json=json.dumps(parsed.to_dict()),
            )
            log_event(
                db, action='documentation_ai.ai_generation',
                entity_type='clinical_ai_session', entity_id=ai_session.id, user_id=user_id,
                details={
                    'session_uuid': ai_session.session_uuid,
                    'history_session_id': history_session_id,
                    'template_key': template['template_key'],
                },
            )
            return {
                'ai_session_uuid': ai_session.session_uuid,
                'provider_key': provider.provider_key,
                'model_name': provider_response.model,
                'parsed_response': parsed.to_dict(),
            }
        except Exception as exc:
            self.session_manager.fail_session(
                db, ai_session, error=str(exc),
                execution_duration_ms=int((time.perf_counter() - started) * 1000),
                prompt_text=prompt_text,
            )
            raise
