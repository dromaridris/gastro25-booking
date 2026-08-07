"""Follow-up planning engine and AI summary generator."""

from __future__ import annotations

import json
import time
from typing import Any

from app.engines import audit_engine
from app.modules.clinical_ai.ai_response_parser import AIResponseParser
from app.modules.clinical_ai.ai_session import AISessionManager
from app.modules.clinical_ai.config import ClinicalAIConfig
from app.modules.clinical_ai.constants import PROMPT_CLINICAL_REASONING
from app.modules.clinical_ai.models import AIProviderRequest
from app.modules.clinical_ai.prompt_blocks import PromptBlock, output_format_block, safety_guardrail_block
from app.modules.clinical_ai.prompt_engine import PromptEngine
from app.modules.clinical_ai.provider_factory import get_ai_provider
from app.modules.patient_journey.catalogue_seed import seed_follow_up_rules_if_empty
from app.modules.patient_journey.constants import CONFIDENCE_HIGH, CONFIDENCE_MEDIUM
from app.modules.patient_journey.guideline_linker import fetch_published_references
from app.modules.patient_journey.models import FollowUpRecommendationRule
from app.modules.patient_journey.permissions import require_journey_ai_use


class FollowUpEngine:
    """Suggests follow-up plans from configuration + clinical context — physician approval required."""

    def suggest(self, clinical_context: dict[str, Any]) -> list[dict[str, Any]]:
        seed_follow_up_rules_if_empty()
        working = clinical_context.get("working_diagnoses") or []
        if not working:
            mgmt = clinical_context.get("management_plan") or {}
            plan = mgmt.get("plan") or {}
            working = plan.get("working_diagnoses") or []

        rules = (
            FollowUpRecommendationRule.query.filter_by(status="active", is_archived=False)
            .order_by(FollowUpRecommendationRule.sort_order)
            .all()
        )

        suggestions: dict[str, dict[str, Any]] = {}
        for rule in rules:
            if rule.diagnosis_name and rule.diagnosis_name not in working:
                continue

            topic_keys = [rule.knowledge_topic_key] if rule.knowledge_topic_key else []
            stable_ids = [rule.knowledge_stable_id] if rule.knowledge_stable_id else []
            knowledge_refs, _ = fetch_published_references(topic_keys=topic_keys, stable_ids=stable_ids)
            if not knowledge_refs:
                knowledge_refs = list(clinical_context.get("knowledge_references") or [])[:1]

            key = rule.related_condition or rule.diagnosis_name or str(rule.id)
            suggestions[key] = {
                "related_condition": rule.related_condition or rule.diagnosis_name,
                "recommended_interval_days": rule.interval_days,
                "recommended_interval_text": rule.interval_text,
                "reason": rule.reason_template,
                "knowledge_references": knowledge_refs,
                "confidence_indicator": CONFIDENCE_HIGH if rule.interval_days else CONFIDENCE_MEDIUM,
            }

        follow_up_mgmt = [
            s
            for s in (clinical_context.get("management_plan") or {}).get("suggestions") or []
            if s.get("category") == "follow_up"
        ]
        for item in follow_up_mgmt:
            key = item.get("related_diagnosis") or item.get("description", "")[:40]
            if key not in suggestions:
                suggestions[key] = {
                    "related_condition": item.get("related_diagnosis"),
                    "recommended_interval_days": None,
                    "recommended_interval_text": "Per management plan",
                    "reason": item.get("description"),
                    "knowledge_references": item.get("knowledge_references") or [],
                    "confidence_indicator": CONFIDENCE_MEDIUM,
                }

        return list(suggestions.values())

    def build_summary_draft(self, clinical_context: dict[str, Any]) -> tuple[str, list[str]]:
        """Deterministic physician-reviewable summary draft."""
        working = clinical_context.get("working_diagnoses") or []
        previous_issue = working[0] if working else (clinical_context.get("intake") or {}).get("chief_complaint") or "Presenting complaint"

        completed_investigations = len(clinical_context.get("laboratory_summary") or []) + len(
            clinical_context.get("imaging_summary") or []
        )
        interpretation_findings = (clinical_context.get("interpretation") or {}).get("findings") or []
        mgmt_suggestions = (clinical_context.get("management_plan") or {}).get("suggestions") or []

        response_lines = [
            "Since last visit:",
            f"- Previous issue: {previous_issue}",
            f"- Completed investigations: {completed_investigations} result set(s) on record",
        ]

        if interpretation_findings:
            response_lines.append(
                f"- Key interpretation: {interpretation_findings[0].get('finding_title', 'See interpretation record')}"
            )

        if mgmt_suggestions:
            response_lines.append(
                f"- Management in place: {mgmt_suggestions[0].get('description', '')[:120]}"
            )

        missing: list[str] = []
        if not interpretation_findings:
            missing.append("No interpretation findings documented since last visit")
        if not mgmt_suggestions:
            missing.append("No approved management plan on record")
        if completed_investigations == 0:
            missing.append("No investigation results available for progress review")

        response_lines.append("- Remaining concerns: Review symptom trajectory and adherence to management plan")
        response_lines.append("- Suggested points for review: Response to treatment, alarm features, follow-up interval")

        return "\n".join(response_lines), missing


class FollowUpSummaryGenerator:
    """Uses Sprint 9A for AI-assisted summary — physician must approve final wording."""

    def __init__(self) -> None:
        self.session_manager = AISessionManager()
        self.response_parser = AIResponseParser()
        self.engine = FollowUpEngine()

    def generate(
        self,
        acting_user,
        *,
        encounter_id: int,
        patient_id: int,
        clinical_context: dict[str, Any],
    ) -> dict[str, Any]:
        require_journey_ai_use(acting_user)
        deterministic_text, missing = self.engine.build_summary_draft(clinical_context)

        cfg = ClinicalAIConfig.from_app()
        provider = get_ai_provider()
        prompt_engine = PromptEngine()
        prompt_engine.register_blocks(
            PROMPT_CLINICAL_REASONING,
            [
                safety_guardrail_block(),
                PromptBlock(
                    block_id="journey_summary_instruction",
                    category="task",
                    content=(
                        "Draft a follow-up summary for physician review. Do NOT determine outcome. "
                        "Do NOT decide discharge. Do NOT change management plan. "
                        "Summarize journey since last visit, highlight missing information and important changes."
                    ),
                ),
                PromptBlock(
                    block_id="clinical_context",
                    category="context",
                    content=json.dumps(clinical_context, indent=2),
                ),
                PromptBlock(
                    block_id="deterministic_summary",
                    category="context",
                    content=deterministic_text,
                ),
                output_format_block(),
            ],
        )

        ai_session = self.session_manager.create_session(
            user_id=acting_user.id,
            prompt_type=PROMPT_CLINICAL_REASONING,
            provider_key=provider.provider_key,
            patient_id=patient_id,
            encounter_id=encounter_id,
            department_id=getattr(acting_user, "department_id", 1),
        )
        self.session_manager.mark_running(ai_session)

        prompt_text = prompt_engine.build(
            PROMPT_CLINICAL_REASONING,
            context_payload={"clinical_context": clinical_context, "deterministic_summary": deterministic_text},
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
                action="patient_journey.ai_summary_generation",
                user=acting_user,
                target_type="clinical_ai_session",
                target_id=ai_session.id,
                details={
                    "session_uuid": ai_session.session_uuid,
                    "encounter_id": encounter_id,
                    "provider": provider.provider_key,
                    "duration_ms": duration_ms,
                },
            )
            return {
                "ai_session_uuid": ai_session.session_uuid,
                "provider_key": provider.provider_key,
                "model_name": provider_response.model,
                "draft_text": deterministic_text,
                "missing_information": missing,
                "knowledge_references": clinical_context.get("knowledge_references") or [],
                "parsed_response": parsed.to_dict(),
            }
        except Exception as exc:
            duration_ms = int((time.perf_counter() - started) * 1000)
            self.session_manager.fail_session(ai_session, error=str(exc), execution_duration_ms=duration_ms)
            raise
