"""Investigation Suggestion Engine."""

from __future__ import annotations

from typing import Any

from app.modules.investigation_planning.constants import (
    CONFIDENCE_HIGH,
    CONFIDENCE_LOW,
    CONFIDENCE_MEDIUM,
    WORKUP_GROUP_ORDER,
)
from app.modules.investigation_planning.evidence_linker import fetch_published_references
from app.modules.investigation_planning.models import (
    InvestigationLibraryEntry,
    InvestigationRecommendationRule,
)


class InvestigationSuggestionEngine:
    """Generates structured investigation suggestions from configuration + context."""

    def generate(self, clinical_context: dict[str, Any]) -> list[dict[str, Any]]:
        complaint_code = (clinical_context.get("intake") or {}).get("complaint_entry_code")
        differential = clinical_context.get("differential_diagnoses") or []
        existing_codes = set(clinical_context.get("existing_investigation_codes") or [])
        existing_codes |= set(clinical_context.get("existing_result_codes") or [])

        diagnosis_names = {d.get("diagnosis_name") for d in differential if d.get("diagnosis_name")}
        rules = InvestigationRecommendationRule.query.filter_by(is_archived=False).order_by(
            InvestigationRecommendationRule.sort_order
        ).all()

        suggestions: dict[str, dict[str, Any]] = {}
        for rule in rules:
            if complaint_code and rule.complaint_code and rule.complaint_code != complaint_code:
                continue
            if rule.diagnosis_name and rule.diagnosis_name not in diagnosis_names:
                continue

            entry = InvestigationLibraryEntry.query.filter_by(
                investigation_id=rule.investigation_id, status="active", is_archived=False
            ).first()
            if entry is None:
                continue

            duplicate_skipped = False
            if entry.catalogue_code and entry.catalogue_code in existing_codes:
                duplicate_skipped = True

            topic_keys = [entry.knowledge_topic_key] if entry.knowledge_topic_key else []
            stable_ids = [entry.knowledge_stable_id] if entry.knowledge_stable_id else []
            knowledge_refs, _ = fetch_published_references(topic_keys=topic_keys, stable_ids=stable_ids)
            if not knowledge_refs:
                knowledge_refs = list(clinical_context.get("knowledge_references") or [])[:1]

            confidence = CONFIDENCE_HIGH if rule.priority == "essential" else CONFIDENCE_MEDIUM
            if duplicate_skipped:
                confidence = CONFIDENCE_LOW

            item = {
                "investigation_id": entry.investigation_id,
                "investigation_name": entry.name,
                "category": entry.category,
                "priority": rule.priority,
                "workup_group": rule.workup_group,
                "reason": rule.reason_template,
                "related_diagnosis": rule.related_diagnosis,
                "clinical_purpose": (entry.indications[0] if entry.indications else rule.reason_template),
                "missing_info_addressed": rule.missing_info_addressed,
                "knowledge_references": knowledge_refs,
                "confidence_indicator": confidence,
                "duplicate_skipped": duplicate_skipped,
                "version": entry.version,
                "sort_key": (WORKUP_GROUP_ORDER.index(rule.workup_group)
                             if rule.workup_group in WORKUP_GROUP_ORDER else 99,
                             rule.sort_order),
            }
            existing = suggestions.get(entry.investigation_id)
            if existing is None or item["sort_key"] < existing["sort_key"]:
                suggestions[entry.investigation_id] = item

        ranked = sorted(suggestions.values(), key=lambda x: (x["sort_key"], x["investigation_name"]))
        for index, item in enumerate(ranked, start=1):
            item["display_rank"] = index
            item.pop("sort_key", None)
        return ranked

    def group_by_workup(self, suggestions: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
        grouped = {group: [] for group in WORKUP_GROUP_ORDER}
        for item in suggestions:
            grouped.setdefault(item["workup_group"], []).append(item)
        return {k: v for k, v in grouped.items() if v}
