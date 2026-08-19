"""Documentation context assembly — Gastro25."""

from __future__ import annotations

import json
import re
from typing import Any

from gi_platform import history_service
from gi_platform.clinical_assessment import service as assessment_service
from gi_platform.clinical_interpretation import service as interpretation_service
from gi_platform.investigation_planning import service as planning_service
from gi_platform.management_plan_ai import service as management_service
from gi_platform.management_plan_ai.constants import WORKING_DIAGNOSIS_STATUSES


def _num(val) -> float | None:
    if val is None:
        return None
    try:
        return float(re.sub(r'[^0-9.\-]', '', str(val)) or 'nan')
    except ValueError:
        return None


class DocumentationContextBuilder:
    def build(self, db, *, history_session_id: int, role: str | None) -> dict[str, Any]:
        hist = db.execute(
            'SELECT * FROM gi_history_session WHERE id = ?', (history_session_id,),
        ).fetchone()
        if not hist:
            raise ValueError(f'No history session {history_session_id}')

        assessment = assessment_service.get_final_assessment(
            db, role=role, history_session_id=history_session_id,
        )
        investigation_plan = planning_service.get_plan_view(
            db, role=role, history_session_id=history_session_id,
        )
        interpretation = interpretation_service.get_interpretation_view(
            db, role=role, history_session_id=history_session_id,
        )
        management_plan = management_service.get_plan_view(
            db, role=role, history_session_id=history_session_id,
        )

        approved_history_text = ''
        structured_findings: list[dict] = []
        draft = db.execute(
            """
            SELECT sections_json, physician_edited_text, structured_findings_json
            FROM gi_guided_history_draft d
            JOIN gi_guided_history_session s ON s.id = d.session_id
            WHERE s.history_session_id = ? AND d.status = 'approved'
            ORDER BY d.created_at DESC LIMIT 1
            """,
            (history_session_id,),
        ).fetchone()
        if draft:
            if draft['physician_edited_text']:
                approved_history_text = draft['physician_edited_text']
            elif draft['sections_json']:
                sections = json.loads(draft['sections_json'])
                approved_history_text = sections.get('hpi') or sections.get('history') or ''
            if draft['structured_findings_json']:
                structured_findings = json.loads(draft['structured_findings_json'])

        if not approved_history_text:
            narr = history_service.get_narrative(db, history_session_id)
            if narr:
                if narr['narrative_text']:
                    approved_history_text = narr['narrative_text']
                elif narr['sections_json']:
                    sections = json.loads(narr['sections_json'] or '{}')
                    approved_history_text = sections.get('hpi') or sections.get('history') or ''

        if not approved_history_text:
            answers = history_service.get_answers_map(db, history_session_id)
            if answers:
                approved_history_text = 'History answers:\n' + '\n'.join(
                    f'- {k}: {v}' for k, v in list(answers.items())[:12]
                )

        working_diagnoses = self._working_diagnoses(assessment, hist)
        lab_results = self._lab_results(db, hist['ward_patient_id'])

        sources_used = []
        if hist['chief_complaint']:
            sources_used.append('clinical_intake')
        if approved_history_text or structured_findings:
            sources_used.append('clinical_history_ai')
        if assessment.get('run'):
            sources_used.append('clinical_assessment')
        if investigation_plan.get('plan'):
            sources_used.append('investigation_planning')
        if lab_results:
            sources_used.append('investigations')
        if interpretation.get('run'):
            sources_used.append('clinical_interpretation')
        if management_plan.get('plan'):
            sources_used.append('management_plan_ai')

        return {
            'history_session_id': history_session_id,
            'ward_patient_id': hist['ward_patient_id'],
            'intake': {'chief_complaint': hist['chief_complaint']},
            'examination_text': hist['examination_text'] or '',
            'structured_findings': structured_findings,
            'approved_history_text': approved_history_text,
            'assessment': assessment,
            'working_diagnoses': working_diagnoses,
            'investigation_plan': investigation_plan,
            'interpretation': interpretation,
            'management_plan': management_plan,
            'patient_journey': {'timeline': [], 'follow_up_plans': [], 'outcomes': []},
            'laboratory_results': lab_results,
            'imaging_results': [],
            'procedures': [],
            'reports': [],
            'knowledge_references': [],
            'knowledge_sources': [],
            'source_modules_used': sources_used,
        }

    @staticmethod
    def _working_diagnoses(assessment: dict, hist) -> list[str]:
        names: list[str] = []
        for decision in assessment.get('decisions') or []:
            if decision.get('physician_status') in WORKING_DIAGNOSIS_STATUSES:
                name = decision.get('diagnosis_name')
                if name and name not in names:
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
            SELECT test_code, test_name, result_value, result_unit, reference_range
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
            out.append({
                'test_code': r['test_code'] or r['test_name'],
                'value': val if val is not None else r['result_value'],
                'unit': r['result_unit'],
                'abnormal_flag': flag,
            })
        return out
