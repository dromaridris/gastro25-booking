"""Assessment context builder — Gastro25."""

from __future__ import annotations

import json
from typing import Any

from gi_platform import history_service
from gi_platform.clinical_history_ai.constants import DRAFT_STATUS_APPROVED, SESSION_STATUS_APPROVED


class AssessmentContextBuilder:
    def build(self, db, *, history_session_id: int) -> dict[str, Any]:
        hist = history_service.get_session(db, history_session_id)
        if not hist:
            raise ValueError(f'No history session {history_session_id}')

        structured_findings: list[dict] = []
        history_sections: dict[str, str | None] = {}

        gh = db.execute(
            """
            SELECT * FROM gi_guided_history_session
            WHERE history_session_id = ? AND status = ?
            ORDER BY id DESC LIMIT 1
            """,
            (history_session_id, SESSION_STATUS_APPROVED),
        ).fetchone()

        if gh:
            draft = db.execute(
                """
                SELECT * FROM gi_guided_history_draft
                WHERE session_id = ? AND status = ?
                ORDER BY created_at DESC LIMIT 1
                """,
                (gh['id'], DRAFT_STATUS_APPROVED),
            ).fetchone()
            if draft:
                structured_findings = json.loads(draft['structured_findings_json'] or '[]')
                history_sections = json.loads(draft['sections_json'] or '{}')

        if not structured_findings:
            for row in history_service.list_answers(db, history_session_id):
                structured_findings.append({
                    'question_id': row['question_key'],
                    'response': row['answer_text'] or '',
                })

        answers_map = {
            str(item.get('question_id', '')).lower(): str(item.get('response', '')).lower()
            for item in structured_findings if item.get('question_id')
        }

        wp = None
        if hist['ward_patient_id']:
            wp = db.execute('SELECT * FROM ward_patient WHERE id = ?', (hist['ward_patient_id'],)).fetchone()

        return {
            'history_session_id': history_session_id,
            'ward_patient_id': hist['ward_patient_id'],
            'patient': {
                'mrn': wp['mrn'] if wp else hist['mrn'],
                'gender': wp['gender'] if wp else None,
            },
            'intake': {
                'chief_complaint': hist['chief_complaint'],
                'complaint_entry_code': hist['complaint_code'],
            },
            'structured_findings': structured_findings,
            'history_sections': history_sections,
            'answers_map': answers_map,
            'knowledge_references': [],
            'knowledge_sources': [],
        }
