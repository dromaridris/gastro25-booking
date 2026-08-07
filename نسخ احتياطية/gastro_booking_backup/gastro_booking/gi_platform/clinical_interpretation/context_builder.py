"""Interpretation context builder — Gastro25."""

from __future__ import annotations

import re
from typing import Any

from gi_platform.clinical_assessment import service as assessment_service


def _num(val) -> float | None:
    if val is None:
        return None
    try:
        return float(re.sub(r'[^0-9.\-]', '', str(val)) or 'nan')
    except ValueError:
        return None


class InterpretationContextBuilder:
    def build(self, db, *, history_session_id: int, role: str | None) -> dict[str, Any]:
        assessment = assessment_service.get_final_assessment(
            db, role=role, history_session_id=history_session_id,
        )
        hist = db.execute(
            'SELECT * FROM gi_history_session WHERE id = ?', (history_session_id,),
        ).fetchone()
        if not hist:
            raise ValueError(f'No history session {history_session_id}')

        lab_results = self._lab_results(db, hist['ward_patient_id'])
        return {
            'history_session_id': history_session_id,
            'ward_patient_id': hist['ward_patient_id'],
            'intake': {'complaint_entry_code': hist['complaint_code'], 'chief_complaint': hist['chief_complaint']},
            'differential_diagnoses': assessment.get('suggestions') or [],
            'physician_diagnosis_decisions': assessment.get('decisions') or [],
            'previous_differential_snapshot': assessment.get('suggestions') or [],
            'laboratory_results': lab_results,
            'imaging_results': [],
            'procedure_reports': [],
            'clinical_data_sources': [{'type': 'laboratory', 'id': l.get('result_id')} for l in lab_results],
            'knowledge_references': [],
            'knowledge_sources': [],
        }

    @staticmethod
    def _lab_results(db, ward_patient_id) -> list[dict[str, Any]]:
        if not ward_patient_id:
            return []
        rows = db.execute(
            """
            SELECT id, test_code, test_name, result_value, result_unit, reference_range, status
            FROM gi_lab_result WHERE ward_patient_id = ?
            ORDER BY result_date DESC, recorded_at DESC LIMIT 40
            """,
            (ward_patient_id,),
        ).fetchall()
        out = []
        for r in rows:
            val = _num(r['result_value'])
            flag = None
            ref = r['reference_range'] or ''
            if val is not None and '-' in ref:
                parts = ref.replace(' ', '').split('-', 1)
                try:
                    lo, hi = float(parts[0]), float(parts[1])
                    if val < lo:
                        flag = 'low'
                    elif val > hi:
                        flag = 'high'
                except ValueError:
                    pass
            code = r['test_code'] or f"lab.{re.sub(r'[^a-z0-9]', '_', (r['test_name'] or '').lower())}"
            if not code.startswith('lab.'):
                code = f'lab.{code}'
            out.append({
                'result_id': r['id'],
                'test_code': code,
                'test_name': r['test_name'],
                'numeric_value': val,
                'text_value': r['result_value'],
                'unit': r['result_unit'],
                'reference_text': ref,
                'abnormal_flag': flag,
                'status': r['status'] or 'completed',
            })
        return out
