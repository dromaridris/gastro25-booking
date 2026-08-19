"""Follow-up engine + AI summary — Gastro25."""

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
from gi_platform.patient_journey.catalogue_seed import seed_follow_up_rules_if_empty
from gi_platform.patient_journey.constants import CONFIDENCE_HIGH, CONFIDENCE_MEDIUM
from gi_platform.patient_journey.permissions import require_journey_use


class FollowUpEngine:
    def suggest(self, db, clinical_context: dict[str, Any]) -> list[dict[str, Any]]:
        seed_follow_up_rules_if_empty(db)
        working = clinical_context.get('working_diagnoses') or []
        rules = db.execute(
            """
            SELECT * FROM gi_follow_up_recommendation_rule
            WHERE status = 'active' OR status IS NULL
            ORDER BY sort_order
            """,
        ).fetchall()

        suggestions: dict[str, dict[str, Any]] = {}
        for rule in rules:
            r = dict(rule)
            if r['diagnosis_name'] and r['diagnosis_name'] not in working:
                continue
            key = r['related_condition'] or r['diagnosis_name'] or str(r['id'])
            suggestions[key] = {
                'related_condition': r['related_condition'] or r['diagnosis_name'],
                'recommended_interval_days': r['interval_days'],
                'recommended_interval_text': r['interval_text'],
                'reason': r['reason_template'],
                'knowledge_references': [],
                'confidence_indicator': CONFIDENCE_HIGH if r['interval_days'] else CONFIDENCE_MEDIUM,
            }

        for item in (clinical_context.get('management_plan') or {}).get('suggestions') or []:
            if item.get('category') != 'follow_up':
                continue
            key = item.get('related_diagnosis') or item.get('description', '')[:40]
            if key not in suggestions:
                suggestions[key] = {
                    'related_condition': item.get('related_diagnosis'),
                    'recommended_interval_days': None,
                    'recommended_interval_text': 'Per management plan',
                    'reason': item.get('description'),
                    'knowledge_references': [],
                    'confidence_indicator': CONFIDENCE_MEDIUM,
                }
        return list(suggestions.values())

    def build_summary_draft(self, clinical_context: dict[str, Any]) -> tuple[str, list[str]]:
        working = clinical_context.get('working_diagnoses') or []
        previous_issue = working[0] if working else (clinical_context.get('intake') or {}).get('chief_complaint') or 'Presenting complaint'
        completed = len(clinical_context.get('laboratory_summary') or [])
        interpretation_findings = (clinical_context.get('interpretation') or {}).get('findings') or []
        mgmt = (clinical_context.get('management_plan') or {}).get('suggestions') or []

        lines = [
            'Since last visit:',
            f'- Previous issue: {previous_issue}',
            f'- Completed investigations: {completed} result(s) on record',
        ]
        if interpretation_findings:
            lines.append(f"- Key interpretation: {interpretation_findings[0].get('finding_title', 'See record')}")
        if mgmt:
            lines.append(f"- Management in place: {mgmt[0].get('description', '')[:120]}")

        missing: list[str] = []
        if not interpretation_findings:
            missing.append('No interpretation findings documented')
        if not mgmt:
            missing.append('No management plan on record')
        if completed == 0:
            missing.append('No investigation results available')

        lines.append('- Remaining concerns: Review symptom trajectory and adherence to plan')
        return '\n'.join(lines), missing


class FollowUpSummaryGenerator:
    def __init__(self, db) -> None:
        self.db = db
        self.session_manager = AISessionManager()
        self.response_parser = AIResponseParser()
        self.engine = FollowUpEngine()

    def generate(
        self, *, role, user_id, history_session_id, ward_patient_id, clinical_context: dict[str, Any],
    ) -> dict[str, Any]:
        require_journey_use(role=role)
        deterministic_text, missing = self.engine.build_summary_draft(clinical_context)
        cfg = ClinicalAIConfig.from_env()
        provider = get_ai_provider()
        prompt_engine = PromptEngine()
        prompt_engine.register_blocks(
            PROMPT_CLINICAL_REASONING,
            [
                safety_guardrail_block(),
                PromptBlock(
                    block_id='journey_summary_instruction', category='task',
                    content='Draft follow-up summary for physician review. Do NOT decide discharge or change plan.',
                ),
                PromptBlock(block_id='clinical_context', category='context',
                            content=json.dumps(clinical_context, indent=2)),
                PromptBlock(block_id='deterministic_summary', category='context', content=deterministic_text),
                output_format_block(),
            ],
        )
        ai_session = self.session_manager.create_session(
            self.db, user_id=user_id, prompt_type=PROMPT_CLINICAL_REASONING,
            provider_key=provider.provider_key, ward_patient_id=ward_patient_id,
            history_session_id=history_session_id,
        )
        self.session_manager.mark_running(self.db, ai_session)
        prompt_text = prompt_engine.build(
            PROMPT_CLINICAL_REASONING,
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
                self.db, action='patient_journey.ai_summary_generation',
                entity_type='clinical_ai_session', entity_id=ai_session.id, user_id=user_id,
                details={'history_session_id': history_session_id},
            )
            return {
                'ai_session_uuid': ai_session.session_uuid,
                'provider_key': provider.provider_key,
                'model_name': provider_response.model,
                'draft_text': deterministic_text,
                'missing_information': missing,
                'knowledge_references': [],
                'parsed_response': parsed.to_dict(),
            }
        except Exception as exc:
            self.session_manager.fail_session(
                self.db, ai_session, error=str(exc),
                execution_duration_ms=int((time.perf_counter() - started) * 1000),
                prompt_text=prompt_text,
            )
            raise
