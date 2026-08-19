"""Deterministic clinical data interpretation engine."""

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
from app.modules.clinical_interpretation.constants import (
    CONFIDENCE_HIGH,
    CONFIDENCE_LOW,
    CONFIDENCE_MEDIUM,
    SOURCE_IMAGING,
    SOURCE_LABORATORY,
    SOURCE_PROCEDURE_REPORT,
)
from app.modules.clinical_interpretation.evidence_linker import fetch_published_references
from app.modules.clinical_interpretation.permissions import require_interpretation_use


_LAB_SIGNALS: dict[str, dict[str, Any]] = {
    "lab.hb": {
        "low": {
            "finding": "Low haemoglobin",
            "significance": "Anaemia may indicate chronic or acute blood loss, marrow suppression, or nutritional deficiency.",
            "supports": ["Upper gastrointestinal bleeding", "Peptic ulcer bleeding", "Peptic ulcer disease"],
            "contradicts": ["Functional dyspepsia"],
            "missing": ["Repeat FBC trend", "Iron studies", "Source of bleeding assessment"],
        },
        "high": {
            "finding": "Elevated haemoglobin",
            "significance": "Polycythaemia may reflect dehydration or secondary causes requiring further evaluation.",
            "supports": [],
            "contradicts": [],
            "missing": ["Hydration status", "Repeat haemoglobin"],
        },
    },
    "lab.wbc": {
        "high": {
            "finding": "Leucocytosis",
            "significance": "Raised white cell count may indicate infection, inflammation, or stress response.",
            "supports": ["Peptic ulcer disease"],
            "contradicts": ["Functional dyspepsia"],
            "missing": ["Infection source assessment", "CRP trend"],
        },
    },
    "lab.plt": {
        "low": {
            "finding": "Thrombocytopenia",
            "significance": "Low platelets increase bleeding risk and may accompany significant GI haemorrhage.",
            "supports": ["Upper gastrointestinal bleeding", "Peptic ulcer bleeding"],
            "contradicts": [],
            "missing": ["Coagulation profile", "Platelet trend"],
        },
    },
}


_IMAGING_KEYWORDS: list[dict[str, Any]] = [
    {
        "keywords": ["ulcer", "erosion", "mucosal defect"],
        "finding": "Mucosal ulceration on imaging/endoscopy correlate",
        "significance": "Ulceration supports an organic upper GI cause rather than purely functional symptoms.",
        "supports": ["Peptic ulcer disease", "Peptic ulcer bleeding"],
        "contradicts": ["Functional dyspepsia"],
    },
    {
        "keywords": ["mass", "malignancy", "tumour", "tumor", "obstruction"],
        "finding": "Suspicious structural lesion",
        "significance": "Structural lesion requires urgent tissue diagnosis and staging work-up.",
        "supports": [],
        "contradicts": ["Functional dyspepsia"],
        "missing": ["Histology", "Staging imaging"],
    },
    {
        "keywords": ["reflux", "oesophagitis", "esophagitis", "barrett"],
        "finding": "Oesophageal mucosal injury pattern",
        "significance": "Mucosal injury supports gastro-oesophageal reflux or related oesophageal pathology.",
        "supports": ["Gastro-oesophageal reflux disease"],
        "contradicts": [],
    },
    {
        "keywords": ["varices", "portal hypertension", "splenomegaly"],
        "finding": "Portal hypertension stigmata",
        "significance": "Varices or portal hypertension signs increase concern for variceal bleeding.",
        "supports": ["Variceal haemorrhage", "Upper gastrointestinal bleeding"],
        "contradicts": ["Functional dyspepsia"],
    },
]


class InterpretationEngine:
    """Generates structured interpretation drafts from clinical data and context."""

    def generate(self, clinical_context: dict[str, Any]) -> list[dict[str, Any]]:
        findings: list[dict[str, Any]] = []
        differential = clinical_context.get("differential_diagnoses") or []
        diagnosis_names = {d.get("diagnosis_name") for d in differential if d.get("diagnosis_name")}

        for lab in clinical_context.get("laboratory_results") or []:
            item = self._interpret_lab(lab, diagnosis_names, clinical_context)
            if item:
                findings.append(item)

        for imaging in clinical_context.get("imaging_results") or []:
            item = self._interpret_imaging(imaging, diagnosis_names, clinical_context)
            if item:
                findings.append(item)

        for report in clinical_context.get("procedure_reports") or []:
            item = self._interpret_procedure_report(report, diagnosis_names, clinical_context)
            if item:
                findings.append(item)

        return findings

    def _interpret_lab(
        self, lab: dict[str, Any], diagnosis_names: set[str], context: dict[str, Any]
    ) -> dict[str, Any] | None:
        flag = lab.get("abnormal_flag")
        if flag not in ("low", "high"):
            return None

        test_code = lab.get("test_code") or ""
        signal = _LAB_SIGNALS.get(test_code, {}).get(flag)
        if signal is None:
            signal = {
                "finding": f"Abnormal {lab.get('test_name', test_code)} ({flag})",
                "significance": self._lab_significance_text(lab, flag),
                "supports": [],
                "contradicts": [],
                "missing": ["Clinical correlation with symptoms and other investigations"],
            }

        supporting = [d for d in signal.get("supports", []) if d in diagnosis_names or not diagnosis_names]
        contradicting = [d for d in signal.get("contradicts", []) if d in diagnosis_names]
        knowledge_refs = self._knowledge_for_diagnoses(supporting or list(diagnosis_names)[:2], context)

        value_text = self._format_lab_value(lab)
        explanation = (
            f"{signal['finding']} ({value_text}). {signal['significance']} "
            f"This result should be interpreted alongside the presenting history and differential assessment."
        )

        return {
            "finding_title": signal["finding"],
            "source_type": SOURCE_LABORATORY,
            "source_data": {
                "result_set_id": lab.get("result_set_id"),
                "test_code": test_code,
                "test_name": lab.get("test_name"),
                "value": value_text,
                "abnormal_flag": flag,
                "reference_range": self._reference_range_text(lab),
            },
            "explanation": explanation,
            "significance": signal["significance"],
            "differential_impact": self._impact_text(supporting, contradicting),
            "related_diagnosis": supporting[0] if supporting else None,
            "supporting_diagnoses": supporting,
            "contradicting_diagnoses": contradicting,
            "missing_information": signal.get("missing") or [],
            "knowledge_references": knowledge_refs,
            "confidence_indicator": CONFIDENCE_HIGH if supporting else CONFIDENCE_MEDIUM,
            "version": 1,
        }

    def _interpret_imaging(
        self, imaging: dict[str, Any], diagnosis_names: set[str], context: dict[str, Any]
    ) -> dict[str, Any] | None:
        text = " ".join(
            filter(
                None,
                [imaging.get("findings_summary") or "", imaging.get("impression") or ""],
            )
        ).lower()
        if not text.strip():
            return None

        matched = None
        for rule in _IMAGING_KEYWORDS:
            if any(kw in text for kw in rule["keywords"]):
                matched = rule
                break

        if matched is None:
            matched = {
                "finding": f"Imaging finding: {imaging.get('study_name', 'study')}",
                "significance": "Imaging findings require clinical correlation with symptoms and laboratory data.",
                "supports": [],
                "contradicts": [],
                "missing": ["Correlate with endoscopy or histology where indicated"],
            }

        supporting = [d for d in matched.get("supports", []) if d in diagnosis_names or not diagnosis_names]
        contradicting = [d for d in matched.get("contradicts", []) if d in diagnosis_names]
        knowledge_refs = self._knowledge_for_diagnoses(supporting or list(diagnosis_names)[:2], context)

        explanation = (
            f"{matched['finding']}. {matched['significance']} "
            f"Findings: {(imaging.get('findings_summary') or '')[:200]}. "
            f"Impression: {(imaging.get('impression') or '')[:200]}."
        ).strip()

        return {
            "finding_title": matched["finding"],
            "source_type": SOURCE_IMAGING,
            "source_data": {
                "study_id": imaging.get("study_id"),
                "study_name": imaging.get("study_name"),
                "body_region": imaging.get("body_region"),
                "findings_summary": imaging.get("findings_summary"),
                "impression": imaging.get("impression"),
            },
            "explanation": explanation,
            "significance": matched["significance"],
            "differential_impact": self._impact_text(supporting, contradicting),
            "related_diagnosis": supporting[0] if supporting else None,
            "supporting_diagnoses": supporting,
            "contradicting_diagnoses": contradicting,
            "missing_information": matched.get("missing") or [],
            "knowledge_references": knowledge_refs,
            "confidence_indicator": CONFIDENCE_MEDIUM if supporting else CONFIDENCE_LOW,
            "version": 1,
        }

    def _interpret_procedure_report(
        self, report: dict[str, Any], diagnosis_names: set[str], context: dict[str, Any]
    ) -> dict[str, Any] | None:
        impression = report.get("impression") or ""
        findings = report.get("findings") or ""
        text = f"{findings} {impression}".lower()
        if not text.strip():
            return None

        matched = None
        for rule in _IMAGING_KEYWORDS:
            if any(kw in text for kw in rule["keywords"]):
                matched = rule
                break

        title = matched["finding"] if matched else f"Procedure report: {report.get('template_key', 'report')}"
        significance = (
            matched["significance"]
            if matched
            else "Procedure findings should be integrated with the clinical assessment and investigation plan."
        )
        supporting = [d for d in (matched or {}).get("supports", []) if d in diagnosis_names or not diagnosis_names]
        contradicting = [d for d in (matched or {}).get("contradicts", []) if d in diagnosis_names]
        knowledge_refs = self._knowledge_for_diagnoses(supporting or list(diagnosis_names)[:2], context)

        return {
            "finding_title": title,
            "source_type": SOURCE_PROCEDURE_REPORT,
            "source_data": {
                "document_id": report.get("document_id"),
                "template_key": report.get("template_key"),
                "impression": impression,
                "findings": findings,
            },
            "explanation": f"{title}. {significance} Impression: {str(impression)[:240]}.",
            "significance": significance,
            "differential_impact": self._impact_text(supporting, contradicting),
            "related_diagnosis": supporting[0] if supporting else None,
            "supporting_diagnoses": supporting,
            "contradicting_diagnoses": contradicting,
            "missing_information": (matched or {}).get("missing") or ["Follow-up plan per procedure report"],
            "knowledge_references": knowledge_refs,
            "confidence_indicator": CONFIDENCE_HIGH if supporting else CONFIDENCE_MEDIUM,
            "version": 1,
        }

    @staticmethod
    def _knowledge_for_diagnoses(diagnoses: list[str], context: dict[str, Any]) -> list[dict[str, Any]]:
        refs = list(context.get("knowledge_references") or [])
        if refs:
            return refs[:2]
        topic_keys = [f"kl.{name.lower().replace(' ', '.')[:40]}" for name in diagnoses[:2]]
        knowledge_refs, _ = fetch_published_references(topic_keys=topic_keys)
        return knowledge_refs

    @staticmethod
    def _format_lab_value(lab: dict[str, Any]) -> str:
        if lab.get("numeric_value") is not None:
            unit = lab.get("unit") or ""
            return f"{lab['numeric_value']}{(' ' + unit) if unit else ''}"
        return lab.get("text_value") or "—"

    @staticmethod
    def _reference_range_text(lab: dict[str, Any]) -> str:
        low, high = lab.get("reference_low"), lab.get("reference_high")
        if low is not None and high is not None:
            unit = lab.get("unit") or ""
            return f"{low}–{high}{(' ' + unit) if unit else ''}"
        return lab.get("reference_text") or "—"

    @staticmethod
    def _lab_significance_text(lab: dict[str, Any], flag: str) -> str:
        name = lab.get("test_name") or lab.get("test_code") or "result"
        direction = "below" if flag == "low" else "above"
        return f"{name} is {direction} reference range and may be clinically relevant to the current differential."

    @staticmethod
    def _impact_text(supporting: list[str], contradicting: list[str]) -> str:
        parts = []
        if supporting:
            parts.append(f"May increase likelihood of: {', '.join(supporting)}.")
        if contradicting:
            parts.append(f"May decrease likelihood of: {', '.join(contradicting)}.")
        if not parts:
            return "Clinical significance requires physician review in full context."
        return " ".join(parts)


class InterpretationAIGenerator:
    """Uses Sprint 9A infrastructure — interpretations remain physician-reviewable drafts only."""

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
        deterministic_findings: list[dict[str, Any]],
    ) -> dict[str, Any]:
        require_interpretation_use(acting_user)
        cfg = ClinicalAIConfig.from_app()
        provider = get_ai_provider()

        prompt_engine = PromptEngine()
        prompt_engine.register_blocks(
            PROMPT_CLINICAL_REASONING,
            [
                safety_guardrail_block(),
                PromptBlock(
                    block_id="interpretation_instruction",
                    category="task",
                    content=(
                        "Interpret newly available clinical data for physician review only. "
                        "Do NOT confirm diagnosis. Do NOT change physician diagnosis. "
                        "Do NOT order investigations or modify patient records. "
                        "Explain clinical relevance of laboratory trends, abnormal values, imaging, "
                        "and procedure findings in context of history and differential."
                    ),
                ),
                PromptBlock(
                    block_id="clinical_context",
                    category="context",
                    content=json.dumps(clinical_context, indent=2),
                ),
                PromptBlock(
                    block_id="deterministic_findings",
                    category="context",
                    content=json.dumps(deterministic_findings, indent=2),
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

        context_payload = {
            "clinical_context": clinical_context,
            "deterministic_findings": deterministic_findings,
        }
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
                ai_session,
                response=provider_response,
                execution_duration_ms=duration_ms,
                prompt_text=prompt_text,
                store_prompt=cfg.log_prompts,
                store_response=cfg.log_responses,
            )
            audit_engine.log(
                action="clinical_interpretation.ai_generation",
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
