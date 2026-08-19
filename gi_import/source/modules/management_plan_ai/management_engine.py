"""Deterministic management suggestion engine."""

from __future__ import annotations

from typing import Any

from app.modules.management_plan_ai.catalogue_seed import seed_management_rules_if_empty
from app.modules.management_plan_ai.constants import (
    CATEGORY_DISPLAY_ORDER,
    CONFIDENCE_HIGH,
    CONFIDENCE_LOW,
    CONFIDENCE_MEDIUM,
    PRIORITY_ESSENTIAL,
)
from app.modules.management_plan_ai.guideline_linker import fetch_published_references
from app.modules.management_plan_ai.models import ManagementPlanRule


class ManagementEngine:
    """Generates structured management suggestions from configuration + clinical context."""

    def generate(self, clinical_context: dict[str, Any]) -> list[dict[str, Any]]:
        seed_management_rules_if_empty()

        working = clinical_context.get("working_diagnoses") or []
        if not working:
            return []

        complaint_code = (clinical_context.get("intake") or {}).get("complaint_entry_code")
        interpretation_findings = clinical_context.get("interpretation_findings") or []
        lab_results = clinical_context.get("laboratory_results") or []

        rules = (
            ManagementPlanRule.query.filter_by(status="active", is_archived=False)
            .order_by(ManagementPlanRule.sort_order)
            .all()
        )

        suggestions: dict[str, dict[str, Any]] = {}
        for rule in rules:
            if rule.diagnosis_name not in working:
                continue
            if complaint_code and rule.complaint_code and rule.complaint_code != complaint_code:
                continue

            topic_keys = [rule.knowledge_topic_key] if rule.knowledge_topic_key else []
            stable_ids = [rule.knowledge_stable_id] if rule.knowledge_stable_id else []
            knowledge_refs, _ = fetch_published_references(topic_keys=topic_keys, stable_ids=stable_ids)
            if not knowledge_refs:
                knowledge_refs = list(clinical_context.get("knowledge_references") or [])[:1]

            supporting = self._supporting_evidence(rule, interpretation_findings, lab_results)
            confidence = CONFIDENCE_HIGH if rule.priority == PRIORITY_ESSENTIAL else CONFIDENCE_MEDIUM
            if not supporting:
                confidence = CONFIDENCE_LOW

            key = f"{rule.diagnosis_name}:{rule.category}:{rule.sort_order}"
            item = {
                "suggestion_key": key,
                "category": rule.category,
                "description": rule.description_template,
                "clinical_indication": rule.clinical_indication,
                "related_diagnosis": rule.diagnosis_name,
                "supporting_evidence": supporting,
                "knowledge_references": knowledge_refs,
                "guideline_references": [rule.guideline_reference] if rule.guideline_reference else [],
                "priority": rule.priority,
                "confidence_indicator": confidence,
                "version": rule.version,
                "sort_key": (
                    CATEGORY_DISPLAY_ORDER.index(rule.category)
                    if rule.category in CATEGORY_DISPLAY_ORDER
                    else 99,
                    rule.sort_order,
                ),
            }
            existing = suggestions.get(key)
            if existing is None:
                suggestions[key] = item

        ordered = sorted(suggestions.values(), key=lambda x: x["sort_key"])
        for item in ordered:
            item.pop("sort_key", None)
        return ordered

    def group_by_category(self, suggestions: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
        grouped = {cat: [] for cat in CATEGORY_DISPLAY_ORDER}
        for item in suggestions:
            grouped.setdefault(item["category"], []).append(item)
        return {k: v for k, v in grouped.items() if v}

    @staticmethod
    def _supporting_evidence(rule, interpretation_findings: list[dict], lab_results: list[dict]) -> list[str]:
        evidence: list[str] = []
        for finding in interpretation_findings:
            if rule.diagnosis_name in (finding.get("supporting_diagnoses") or []):
                title = finding.get("finding_title")
                if title:
                    evidence.append(f"Interpretation: {title}")
        for lab in lab_results:
            if lab.get("abnormal_flag") in ("low", "high"):
                evidence.append(f"Lab {lab.get('test_code')}: {lab.get('abnormal_flag')}")
        if rule.clinical_indication:
            evidence.append(rule.clinical_indication)
        return list(dict.fromkeys(evidence))[:5]
