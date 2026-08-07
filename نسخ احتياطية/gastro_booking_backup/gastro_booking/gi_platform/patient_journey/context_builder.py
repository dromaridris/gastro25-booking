"""Journey context — Gastro25."""

from __future__ import annotations

from gi_platform import patient_journey_service
from gi_platform.clinical_assessment import service as assessment_service
from gi_platform.clinical_interpretation import service as interpretation_service
from gi_platform.investigation_planning import service as planning_service
from gi_platform.management_plan_ai import service as management_service
from gi_platform.management_plan_ai.constants import WORKING_DIAGNOSIS_STATUSES


class JourneyContextBuilder:
    def build(self, db, *, history_session_id: int, role: str | None) -> dict:
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

        labs = patient_journey_service.labs_for_patient(db, ward_patient_id=hist['ward_patient_id'])
        laboratory_summary = [{'test_name': l['test_name'], 'value': l['result_value']} for l in labs[:10]]

        return {
            'history_session_id': history_session_id,
            'ward_patient_id': hist['ward_patient_id'],
            'intake': {'chief_complaint': hist['chief_complaint']},
            'assessment': assessment,
            'investigation_plan': investigation_plan,
            'interpretation': interpretation,
            'management_plan': management_plan,
            'laboratory_summary': laboratory_summary,
            'imaging_summary': [],
            'working_diagnoses': self._working_diagnoses(assessment, hist),
            'knowledge_references': [],
        }

    @staticmethod
    def _working_diagnoses(assessment, hist) -> list[str]:
        names: list[str] = []
        for decision in assessment.get('decisions') or []:
            if decision.get('physician_status') in WORKING_DIAGNOSIS_STATUSES:
                name = decision.get('diagnosis_name')
                if name and name not in names:
                    names.append(name)
        if not names and hist['final_diagnosis']:
            names.append(hist['final_diagnosis'])
        return names
