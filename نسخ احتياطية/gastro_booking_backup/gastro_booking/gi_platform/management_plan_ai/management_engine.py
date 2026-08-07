"""Deterministic management suggestion engine — Gastro25."""

from __future__ import annotations

from typing import Any

from gi_platform.management_plan_ai.catalogue_seed import seed_management_rules_if_empty
from gi_platform.management_plan_ai.constants import (
    CATEGORY_DISPLAY_ORDER, CONFIDENCE_HIGH, CONFIDENCE_LOW, CONFIDENCE_MEDIUM, PRIORITY_ESSENTIAL,
)


class ManagementEngine:
    def generate(self, db, clinical_context: dict[str, Any]) -> list[dict[str, Any]]:
        seed_management_rules_if_empty(db)

        working = clinical_context.get('working_diagnoses') or []
        if not working:
            return []

        complaint_code = (clinical_context.get('intake') or {}).get('complaint_entry_code')
        interpretation_findings = clinical_context.get('interpretation_findings') or []
        lab_results = clinical_context.get('laboratory_results') or []

        rules = db.execute(
            """
            SELECT * FROM gi_management_plan_rule
            WHERE status = 'active' OR status IS NULL
            ORDER BY sort_order
            """,
        ).fetchall()

        suggestions: dict[str, dict[str, Any]] = {}
        for rule in rules:
            r = dict(rule)
            if r['diagnosis_name'] not in working:
                continue
            if complaint_code and r['complaint_code'] and r['complaint_code'] != complaint_code:
                continue

            supporting = self._supporting_evidence(r, interpretation_findings, lab_results)
            confidence = CONFIDENCE_HIGH if r['priority'] == PRIORITY_ESSENTIAL else CONFIDENCE_MEDIUM
            if not supporting:
                confidence = CONFIDENCE_LOW

            key = f"{r['diagnosis_name']}:{r['category']}:{r['sort_order']}"
            suggestions[key] = {
                'suggestion_key': key,
                'category': r['category'],
                'description': r['description_template'],
                'clinical_indication': r['clinical_indication'],
                'related_diagnosis': r['diagnosis_name'],
                'supporting_evidence': supporting,
                'knowledge_references': [],
                'guideline_references': [r['guideline_reference']] if r.get('guideline_reference') else [],
                'priority': r['priority'],
                'confidence_indicator': confidence,
                'version': 1,
                'sort_key': (
                    CATEGORY_DISPLAY_ORDER.index(r['category'])
                    if r['category'] in CATEGORY_DISPLAY_ORDER else 99,
                    r['sort_order'],
                ),
            }

        ordered = sorted(suggestions.values(), key=lambda x: x['sort_key'])
        for item in ordered:
            item.pop('sort_key', None)
        return ordered

    def group_by_category(self, suggestions: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
        grouped = {cat: [] for cat in CATEGORY_DISPLAY_ORDER}
        for item in suggestions:
            grouped.setdefault(item['category'], []).append(item)
        return {k: v for k, v in grouped.items() if v}

    @staticmethod
    def _supporting_evidence(rule: dict, interpretation_findings: list[dict], lab_results: list[dict]) -> list[str]:
        evidence: list[str] = []
        for finding in interpretation_findings:
            if rule['diagnosis_name'] in (finding.get('supporting_diagnoses') or []):
                title = finding.get('finding_title')
                if title:
                    evidence.append(f'Interpretation: {title}')
        for lab in lab_results:
            if lab.get('abnormal_flag') in ('low', 'high'):
                evidence.append(f"Lab {lab.get('test_code')}: {lab.get('abnormal_flag')}")
        if rule.get('clinical_indication'):
            evidence.append(rule['clinical_indication'])
        return list(dict.fromkeys(evidence))[:5]
