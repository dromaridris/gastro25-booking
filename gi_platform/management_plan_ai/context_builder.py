"""Management planning context — Gastro25."""

from __future__ import annotations

import re
from typing import Any

from gi_platform.clinical_assessment import service as assessment_service
from gi_platform.clinical_interpretation import service as interpretation_service
from gi_platform.investigation_planning import service as planning_service
from gi_platform.management_plan_ai.constants import WORKING_DIAGNOSIS_STATUSES


def _num(val) -> float | None:
    if val is None:
        return None
    try:
        return float(re.sub(r'[^0-9.\-]', '', str(val)) or 'nan')
    except ValueError:
        return None


class ManagementContextBuilder:
    def build(self, db, *, history_session_id: int, role: str | None) -> dict[str, Any]:
        hist = db.execute(
            'SELECT * FROM gi_history_session WHERE id = ?', (history_session_id,),
        ).fetchone()
        if not hist:
            raise ValueError(f'No history session {history_session_id}')

        assessment = assessment_service.get_final_assessment(
            db, role=role, history_session_id=history_session_id,
        )
        plan_view = planning_service.get_plan_view(db, role=role, history_session_id=history_session_id)
        interpretation_view = interpretation_service.get_interpretation_view(
            db, role=role, history_session_id=history_session_id,
        )

        working_diagnoses = self._working_diagnoses(assessment, hist)
        lab_results = self._lab_results(db, hist['ward_patient_id'])

        return {
            'history_session_id': history_session_id,
            'ward_patient_id': hist['ward_patient_id'],
            'intake': {
                'chief_complaint': hist['chief_complaint'],
                'complaint_entry_code': hist['complaint_code'],
            },
            'differential_diagnoses': assessment.get('suggestions') or [],
            'physician_diagnosis_decisions': assessment.get('decisions') or [],
            'working_diagnoses': working_diagnoses,
            'investigation_plan': plan_view.get('plan'),
            'investigation_suggestions': plan_view.get('suggestions') or [],
            'interpretation': interpretation_view.get('run'),
            'interpretation_findings': interpretation_view.get('findings') or [],
            'differential_updates': interpretation_view.get('differential_updates') or [],
            'laboratory_results': lab_results,
            'imaging_results': [],
            'knowledge_references': [],
            'knowledge_sources': [],
        }

    @staticmethod
    def _working_diagnoses(assessment: dict[str, Any], hist) -> list[str]:
        names: list[str] = []
        for decision in assessment.get('decisions') or []:
            status = decision.get('physician_status')
            name = decision.get('diagnosis_name')
            if status in WORKING_DIAGNOSIS_STATUSES and name and name not in names:
                names.append(name)
        if not names and hist['final_diagnosis']:
            names.append(hist['final_diagnosis'])
        if not names:
            for s in assessment.get('suggestions') or []:
                name = s.get('diagnosis_name')
                if name and name not in names:
                    names.append(name)
                    break
        return names

    @staticmethod
    def _lab_results(db, ward_patient_id) -> list[dict[str, Any]]:
        if not ward_patient_id:
            return []
        rows = db.execute(
            """
            SELECT test_code, result_value, reference_range
            FROM gi_lab_result WHERE ward_patient_id = ?
            ORDER BY result_date DESC LIMIT 20
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
            if flag:
                out.append({'test_code': r['test_code'], 'abnormal_flag': flag, 'numeric_value': val})
        return out
