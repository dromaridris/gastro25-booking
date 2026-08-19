"""Reusable Differential Diagnosis Engine."""

from __future__ import annotations

from typing import Any

from app.modules.clinical_assessment.constants import (
    CATEGORY_DISPLAY_ORDER,
    CONFIDENCE_HIGH,
    CONFIDENCE_LOW,
    CONFIDENCE_MEDIUM,
)
from app.modules.clinical_assessment.knowledge_linker import fetch_published_references
from app.modules.clinical_assessment.models import DiagnosisRuleDefinition


class DifferentialDiagnosisEngine:
    """Generates ranked, traceable differential suggestions from configuration + context."""

    def generate(self, clinical_context: dict[str, Any]) -> list[dict[str, Any]]:
        complaint_code = (clinical_context.get("intake") or {}).get("complaint_entry_code")
        if not complaint_code:
            return []

        answers_map = clinical_context.get("answers_map") or {}
        findings = clinical_context.get("structured_findings") or []
        rules = (
            DiagnosisRuleDefinition.query.filter_by(
                complaint_code=complaint_code, status="active", is_archived=False
            )
            .order_by(DiagnosisRuleDefinition.base_priority)
            .all()
        )

        suggestions: list[dict[str, Any]] = []
        for rule in rules:
            score, supporting, missing, contradicting, findings_used = self._score_rule(
                rule, answers_map, findings
            )
            if score <= 0:
                continue

            topic_keys = [rule.knowledge_topic_key] if rule.knowledge_topic_key else []
            stable_ids = [rule.knowledge_stable_id] if rule.knowledge_stable_id else []
            knowledge_refs, _ = fetch_published_references(
                topic_keys=topic_keys, stable_ids=stable_ids
            )
            if not knowledge_refs:
                knowledge_refs = list(clinical_context.get("knowledge_references") or [])[:1]

            suggestions.append(
                {
                    "diagnosis_name": rule.diagnosis_name,
                    "category": rule.category,
                    "priority_rank": rule.base_priority,
                    "score": score,
                    "supporting_findings": supporting,
                    "missing_information": missing,
                    "contradicting_findings": contradicting,
                    "inclusion_reason": rule.inclusion_reason,
                    "confidence_indicator": self._confidence_label(score),
                    "knowledge_references": knowledge_refs,
                    "clinical_findings_used": findings_used,
                    "version": rule.version,
                }
            )

        suggestions.sort(key=lambda item: (-item["score"], item["priority_rank"], item["diagnosis_name"]))
        return self._assign_display_ranks(suggestions)

    def group_by_category(self, suggestions: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
        grouped = {cat: [] for cat in CATEGORY_DISPLAY_ORDER}
        for item in suggestions:
            grouped.setdefault(item["category"], []).append(item)
        return {k: v for k, v in grouped.items() if v}

    @staticmethod
    def _score_rule(rule, answers_map: dict[str, str], findings: list[dict]) -> tuple:
        score = rule.base_confidence
        supporting: list[str] = []
        missing: list[str] = []
        contradicting: list[str] = []
        findings_used: list[dict] = []

        for pattern in rule.supporting_patterns:
            qid = pattern.get("question_id")
            if not qid:
                continue
            answer = answers_map.get(qid, "")
            allowed = {str(v).lower() for v in pattern.get("answer_in", [])}
            required = str(pattern.get("answer_equals", "")).lower()
            if allowed and answer in allowed:
                score += 0.12
                supporting.append(f"{qid}: {answer}")
                findings_used.extend([f for f in findings if f.get("question_id") == qid])
            elif required and answer == required:
                score += 0.12
                supporting.append(f"{qid}: {answer}")
                findings_used.extend([f for f in findings if f.get("question_id") == qid])
            elif allowed or required:
                score -= 0.05

        for pattern in rule.missing_patterns:
            qid = pattern.get("question_id")
            if not qid:
                continue
            answer = answers_map.get(qid, "")
            if not answer:
                missing.append(f"Missing answer for {qid}")
                score -= 0.03
            elif pattern.get("answer_equals") is not None and answer == str(pattern["answer_equals"]).lower():
                missing.append(f"{qid} not yet assessed as expected")

        for pattern in rule.contradicting_patterns:
            qid = pattern.get("question_id")
            if not qid:
                continue
            answer = answers_map.get(qid, "")
            if str(pattern.get("answer_equals", "")).lower() == answer:
                contradicting.append(f"{qid}: {answer}")
                score -= 0.2

        if score <= 0.15:
            return 0, supporting, missing, contradicting, findings_used
        return min(score, 1.0), supporting, missing, contradicting, findings_used

    @staticmethod
    def _confidence_label(score: float) -> str:
        if score >= 0.75:
            return CONFIDENCE_HIGH
        if score >= 0.45:
            return CONFIDENCE_MEDIUM
        return CONFIDENCE_LOW

    @staticmethod
    def _assign_display_ranks(suggestions: list[dict[str, Any]]) -> list[dict[str, Any]]:
        rank = 1
        for item in suggestions:
            item["priority_rank"] = rank
            rank += 1
        return suggestions
