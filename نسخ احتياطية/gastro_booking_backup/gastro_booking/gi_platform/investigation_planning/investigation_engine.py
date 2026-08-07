"""Investigation Suggestion Engine — Gastro25 SQLite."""

from __future__ import annotations

import json
from typing import Any

from gi_platform.investigation_planning.constants import (
    CONFIDENCE_HIGH, CONFIDENCE_LOW, CONFIDENCE_MEDIUM, WORKUP_GROUP_ORDER,
)


class InvestigationSuggestionEngine:
    def generate(self, db, clinical_context: dict[str, Any]) -> list[dict[str, Any]]:
        complaint_code = (clinical_context.get('intake') or {}).get('complaint_entry_code')
        differential = clinical_context.get('differential_diagnoses') or []
        existing_codes = set(clinical_context.get('existing_investigation_codes') or [])
        existing_codes |= set(clinical_context.get('existing_result_codes') or [])

        diagnosis_names = {d.get('diagnosis_name') for d in differential if d.get('diagnosis_name')}
        rules = db.execute(
            """
            SELECT * FROM gi_investigation_recommendation_rule
            WHERE status = 'active' OR status IS NULL
            ORDER BY sort_order
            """,
        ).fetchall()

        library = {
            r['investigation_id']: r
            for r in db.execute(
                "SELECT * FROM gi_investigation_library_entry WHERE status = 'active'",
            ).fetchall()
        }

        suggestions: dict[str, dict[str, Any]] = {}
        for rule in rules:
            if complaint_code and rule['complaint_code'] and rule['complaint_code'] != complaint_code:
                continue
            if rule['diagnosis_name'] and rule['diagnosis_name'] not in diagnosis_names:
                continue

            entry = library.get(rule['investigation_id'])
            if entry is None:
                continue

            indications = json.loads(entry['indications_json'] or '[]')
            duplicate_skipped = bool(entry['catalogue_code'] and entry['catalogue_code'] in existing_codes)
            confidence = CONFIDENCE_HIGH if rule['priority'] == 'essential' else CONFIDENCE_MEDIUM
            if duplicate_skipped:
                confidence = CONFIDENCE_LOW

            item = {
                'investigation_id': entry['investigation_id'],
                'investigation_name': entry['name'],
                'category': entry['category'],
                'priority': rule['priority'],
                'workup_group': rule['workup_group'],
                'reason': rule['reason_template'],
                'related_diagnosis': rule['related_diagnosis'],
                'clinical_purpose': indications[0] if indications else rule['reason_template'],
                'missing_info_addressed': rule['missing_info_addressed'],
                'knowledge_references': [],
                'confidence_indicator': confidence,
                'duplicate_skipped': duplicate_skipped,
                'version': entry['version'] if 'version' in entry.keys() else 1,
                'sort_key': (
                    WORKUP_GROUP_ORDER.index(rule['workup_group'])
                    if rule['workup_group'] in WORKUP_GROUP_ORDER else 99,
                    rule['sort_order'],
                ),
            }
            existing = suggestions.get(entry['investigation_id'])
            if existing is None or item['sort_key'] < existing['sort_key']:
                suggestions[entry['investigation_id']] = item

        ranked = sorted(suggestions.values(), key=lambda x: (x['sort_key'], x['investigation_name']))
        for index, item in enumerate(ranked, start=1):
            item['display_rank'] = index
            item.pop('sort_key', None)
        return ranked

    def group_by_workup(self, suggestions: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
        grouped = {group: [] for group in WORKUP_GROUP_ORDER}
        for item in suggestions:
            grouped.setdefault(item['workup_group'], []).append(item)
        return {k: v for k, v in grouped.items() if v}
