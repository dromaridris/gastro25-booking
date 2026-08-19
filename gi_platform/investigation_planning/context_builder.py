"""Investigation planning context — Gastro25."""

from __future__ import annotations

import json
from typing import Any

from gi_platform.clinical_assessment import service as assessment_service


class InvestigationContextBuilder:
    def build(self, db, *, history_session_id: int, role: str | None) -> dict[str, Any]:
        hist = db.execute(
            'SELECT * FROM gi_history_session WHERE id = ?', (history_session_id,),
        ).fetchone()
        if not hist:
            raise ValueError(f'No history session {history_session_id}')

        assessment = assessment_service.get_final_assessment(
            db, role=role, history_session_id=history_session_id,
        )
        differential = assessment.get('suggestions') or []
        physician_decisions = assessment.get('decisions') or []

        existing_codes = self._existing_investigation_codes(db, hist['ward_patient_id'])
        existing_results = self._existing_result_codes(db, hist['ward_patient_id'])

        structured_findings: list[dict] = []
        draft = db.execute(
            """
            SELECT structured_findings_json FROM gi_guided_history_draft d
            JOIN gi_guided_history_session s ON s.id = d.session_id
            WHERE s.history_session_id = ? AND d.status = 'approved'
            ORDER BY d.created_at DESC LIMIT 1
            """,
            (history_session_id,),
        ).fetchone()
        if draft and draft['structured_findings_json']:
            structured_findings = json.loads(draft['structured_findings_json'])

        wp = db.execute(
            'SELECT mrn FROM ward_patient WHERE id = ?', (hist['ward_patient_id'],),
        ).fetchone() if hist['ward_patient_id'] else None

        return {
            'history_session_id': history_session_id,
            'ward_patient_id': hist['ward_patient_id'],
            'patient': {'mrn': wp['mrn'] if wp else None},
            'intake': {
                'chief_complaint': hist['chief_complaint'],
                'complaint_entry_code': hist['complaint_code'],
            },
            'structured_findings': structured_findings,
            'differential_diagnoses': differential,
            'physician_diagnosis_decisions': physician_decisions,
            'existing_investigation_codes': sorted(existing_codes),
            'existing_result_codes': sorted(existing_results),
            'knowledge_references': [],
            'knowledge_sources': [],
        }

    @staticmethod
    def _existing_investigation_codes(db, ward_patient_id) -> set[str]:
        if not ward_patient_id:
            return set()
        codes: set[str] = set()
        rows = db.execute(
            """
            SELECT item_code FROM gi_investigation_order
            WHERE ward_patient_id = ? AND item_code IS NOT NULL
            """,
            (ward_patient_id,),
        ).fetchall()
        for r in rows:
            if r['item_code']:
                codes.add(r['item_code'])
        return codes

    @staticmethod
    def _existing_result_codes(db, ward_patient_id) -> set[str]:
        if not ward_patient_id:
            return set()
        codes: set[str] = set()
        rows = db.execute(
            """
            SELECT test_code FROM gi_lab_result
            WHERE ward_patient_id = ? AND test_code IS NOT NULL
            """,
            (ward_patient_id,),
        ).fetchall()
        for r in rows:
            if r['test_code']:
                codes.add(r['test_code'])
        return codes
