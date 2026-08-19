"""Differential diagnosis engine — SQLite rules + CDS fallback."""

from __future__ import annotations

import json
from typing import Any

from gi_platform.clinical_assessment.constants import (
    CATEGORY_DISPLAY_ORDER,
    CONFIDENCE_HIGH,
    CONFIDENCE_LOW,
    CONFIDENCE_MEDIUM,
    CONSIDERATION_TO_CATEGORY,
)


class DifferentialDiagnosisEngine:
    def generate(self, db, clinical_context: dict[str, Any]) -> list[dict[str, Any]]:
        complaint_code = (clinical_context.get('intake') or {}).get('complaint_entry_code')
        if not complaint_code:
            return []

        answers_map = clinical_context.get('answers_map') or {}
        findings = clinical_context.get('structured_findings') or []

        rules = db.execute(
            """
            SELECT * FROM gi_diagnosis_rule
            WHERE complaint_code = ? AND status = 'active'
            ORDER BY base_priority
            """,
            (complaint_code,),
        ).fetchall()

        suggestions: list[dict[str, Any]] = []
        if rules:
            for rule in rules:
                score, supporting, missing, contradicting, findings_used = self._score_rule(
                    rule, answers_map, findings,
                )
                if score <= 0:
                    continue
                suggestions.append({
                    'diagnosis_name': rule['diagnosis_name'],
                    'category': rule['category'],
                    'priority_rank': rule['base_priority'],
                    'score': score,
                    'supporting_findings': supporting,
                    'missing_information': missing,
                    'contradicting_findings': contradicting,
                    'inclusion_reason': rule['inclusion_reason'],
                    'confidence_indicator': self._confidence_label(score),
                    'knowledge_references': [],
                    'clinical_findings_used': findings_used,
                    'version': 1,
                })

        # Always enrich from CDS priors when available — rules alone are sparse.
        cds_items = self._from_cds(db, clinical_context)
        suggestions = self._merge_by_name(suggestions, cds_items)

        if not suggestions:
            suggestions = self._from_disease_catalogue(db, complaint_code)

        suggestions.sort(key=lambda item: (-item.get('score', 0), item['priority_rank'], item['diagnosis_name']))
        return self._assign_display_ranks(suggestions)

    @staticmethod
    def _merge_by_name(primary: list[dict], secondary: list[dict]) -> list[dict]:
        by_name: dict[str, dict] = {}
        for item in primary + secondary:
            key = (item.get('diagnosis_name') or '').strip().lower()
            if not key:
                continue
            if key not in by_name or float(item.get('score') or 0) > float(by_name[key].get('score') or 0):
                by_name[key] = item
        return list(by_name.values())

    def _from_cds(self, db, clinical_context: dict[str, Any]) -> list[dict[str, Any]]:
        session_id = clinical_context.get('history_session_id')
        complaint = (clinical_context.get('intake') or {}).get('complaint_entry_code')
        if not session_id or not complaint:
            return []
        try:
            from gi_platform.decision_support.adapters import build_context_from_session
            from gi_platform.decision_support.service import get_decision_support_service

            ctx = build_context_from_session(db, session_id=session_id, complaint_code=complaint)
            result = get_decision_support_service(db).assess(ctx)
        except Exception:
            return []
        out = []
        for i, dx in enumerate(result.differential, 1):
            cat = CONSIDERATION_TO_CATEGORY.get(dx.consideration_level, 'important_alternative')
            out.append({
                'diagnosis_name': dx.name,
                'category': cat,
                'priority_rank': i * 10,
                'score': 0.8 if dx.consideration_level == 'strong_consideration' else 0.5,
                'supporting_findings': [dx.consideration_label],
                'missing_information': [],
                'contradicting_findings': [],
                'inclusion_reason': dx.consideration_label or 'From clinical decision support priors.',
                'confidence_indicator': self._confidence_label(0.8 if i <= 2 else 0.4),
                'knowledge_references': [],
                'clinical_findings_used': [],
                'version': 1,
            })
        return out

    def _from_disease_catalogue(self, db, complaint_code: str) -> list[dict[str, Any]]:
        """Last-resort differential from published disease objects linked to the complaint."""
        rows = db.execute(
            """
            SELECT title, body_json FROM gi_knowledge_object
            WHERE object_type = 'disease' AND status = 'published'
              AND (
                json_extract(body_json, '$.complaint_code') = ?
                OR body_json LIKE ?
              )
            ORDER BY title LIMIT 8
            """,
            (complaint_code, f'%{complaint_code}%'),
        ).fetchall()
        if not rows:
            rows = db.execute(
                """
                SELECT title, body_json FROM gi_knowledge_object
                WHERE object_type = 'disease' AND status = 'published'
                ORDER BY title LIMIT 5
                """
            ).fetchall()
        out = []
        for i, row in enumerate(rows, 1):
            body = json.loads(row['body_json'] or '{}')
            out.append({
                'diagnosis_name': row['title'] or body.get('diagnosis_code') or f'Diagnosis {i}',
                'category': 'important_alternative' if i > 2 else 'most_likely',
                'priority_rank': i * 10,
                'score': max(0.35, 0.7 - (i * 0.05)),
                'supporting_findings': ['Catalogue disease linked to presenting complaint'],
                'missing_information': ['Refine with more history answers'],
                'contradicting_findings': [],
                'inclusion_reason': 'Knowledge-catalogue differential for this complaint.',
                'confidence_indicator': self._confidence_label(0.45),
                'knowledge_references': [],
                'clinical_findings_used': [],
                'version': 1,
            })
        return out

    def group_by_category(self, suggestions: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
        grouped = {cat: [] for cat in CATEGORY_DISPLAY_ORDER}
        for item in suggestions:
            grouped.setdefault(item['category'], []).append(item)
        return {k: v for k, v in grouped.items() if v}

    @staticmethod
    def _score_rule(rule, answers_map: dict[str, str], findings: list[dict]) -> tuple:
        score = float(rule['base_confidence'])
        supporting, missing, contradicting, findings_used = [], [], [], []
        sup = json.loads(rule['supporting_patterns_json'] or '[]')
        miss = json.loads(rule['missing_patterns_json'] or '[]')
        contra = json.loads(rule['contradicting_patterns_json'] or '[]')

        for pattern in sup:
            qid = pattern.get('question_id')
            if not qid:
                continue
            answer = answers_map.get(qid, '') or answers_map.get(str(qid).lower(), '')
            allowed = {str(v).lower() for v in pattern.get('answer_in', [])}
            required = str(pattern.get('answer_equals', '')).lower()
            if allowed and answer in allowed:
                score += 0.12
                supporting.append(f'{qid}: {answer}')
            elif required and answer == required:
                score += 0.12
                supporting.append(f'{qid}: {answer}')

        for pattern in miss:
            qid = pattern.get('question_id')
            if qid and not (answers_map.get(qid) or answers_map.get(str(qid).lower())):
                missing.append(f'Missing answer for {qid}')
                score -= 0.03

        for pattern in contra:
            qid = pattern.get('question_id')
            answer = answers_map.get(qid or '', '') or answers_map.get(str(qid or '').lower(), '')
            if str(pattern.get('answer_equals', '')).lower() == answer:
                contradicting.append(f'{qid}: {answer}')
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
        for rank, item in enumerate(suggestions, 1):
            item['priority_rank'] = rank
        return suggestions
