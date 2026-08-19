"""Deterministic clinical data interpretation engine."""

from __future__ import annotations

from typing import Any

from gi_platform.clinical_interpretation.constants import (
    CONFIDENCE_HIGH, CONFIDENCE_LOW, CONFIDENCE_MEDIUM,
    SOURCE_IMAGING, SOURCE_LABORATORY, SOURCE_PROCEDURE_REPORT,
)

_LAB_SIGNALS: dict[str, dict[str, Any]] = {
    'lab.hb': {
        'low': {
            'finding': 'Low haemoglobin',
            'significance': 'Anaemia may indicate blood loss or nutritional deficiency.',
            'supports': ['Upper gastrointestinal bleeding', 'Peptic ulcer bleeding'],
            'contradicts': ['Functional dyspepsia'],
            'missing': ['Repeat FBC trend', 'Iron studies'],
        },
    },
    'lab.hgb': {
        'low': {
            'finding': 'Low haemoglobin',
            'significance': 'Anaemia may indicate blood loss.',
            'supports': ['Upper gastrointestinal bleeding', 'Peptic ulcer bleeding'],
            'contradicts': [],
            'missing': ['Repeat FBC'],
        },
    },
    'lab.wbc': {
        'high': {
            'finding': 'Leucocytosis',
            'significance': 'May indicate infection or inflammation.',
            'supports': ['Peptic ulcer disease'],
            'contradicts': ['Functional dyspepsia'],
            'missing': ['CRP trend'],
        },
    },
}


class InterpretationEngine:
    def generate(self, clinical_context: dict[str, Any]) -> list[dict[str, Any]]:
        findings: list[dict[str, Any]] = []
        differential = clinical_context.get('differential_diagnoses') or []
        diagnosis_names = {d.get('diagnosis_name') for d in differential if d.get('diagnosis_name')}

        for lab in clinical_context.get('laboratory_results') or []:
            item = self._interpret_lab(lab, diagnosis_names)
            if item:
                findings.append(item)

        for imaging in clinical_context.get('imaging_results') or []:
            text = f"{imaging.get('findings_summary', '')} {imaging.get('impression', '')}".lower()
            if text.strip():
                findings.append({
                    'finding_title': f"Imaging: {imaging.get('study_name', 'study')}",
                    'source_type': SOURCE_IMAGING,
                    'source_data': imaging,
                    'explanation': text[:400],
                    'significance': 'Imaging requires clinical correlation.',
                    'differential_impact': 'Physician review required.',
                    'supporting_diagnoses': [],
                    'contradicting_diagnoses': [],
                    'missing_information': [],
                    'knowledge_references': [],
                    'confidence_indicator': CONFIDENCE_MEDIUM,
                    'version': 1,
                })

        return findings

    def _interpret_lab(self, lab: dict[str, Any], diagnosis_names: set[str]) -> dict[str, Any] | None:
        flag = lab.get('abnormal_flag')
        if flag not in ('low', 'high'):
            return None
        test_code = (lab.get('test_code') or '').lower()
        signal = _LAB_SIGNALS.get(test_code, {}).get(flag)
        if signal is None:
            signal = {
                'finding': f"Abnormal {lab.get('test_name', test_code)} ({flag})",
                'significance': f"{lab.get('test_name', 'Result')} is outside reference range.",
                'supports': [], 'contradicts': [], 'missing': ['Clinical correlation'],
            }
        supporting = [d for d in signal.get('supports', []) if d in diagnosis_names or not diagnosis_names]
        contradicting = [d for d in signal.get('contradicts', []) if d in diagnosis_names]
        value_text = str(lab.get('numeric_value') or lab.get('text_value') or '—')
        if lab.get('unit'):
            value_text += f" {lab['unit']}"
        return {
            'finding_title': signal['finding'],
            'source_type': SOURCE_LABORATORY,
            'source_data': {'result_id': lab.get('result_id'), 'test_code': test_code, 'value': value_text},
            'explanation': f"{signal['finding']} ({value_text}). {signal['significance']}",
            'significance': signal['significance'],
            'differential_impact': self._impact_text(supporting, contradicting),
            'related_diagnosis': supporting[0] if supporting else None,
            'supporting_diagnoses': supporting,
            'contradicting_diagnoses': contradicting,
            'missing_information': signal.get('missing') or [],
            'knowledge_references': [],
            'confidence_indicator': CONFIDENCE_HIGH if supporting else CONFIDENCE_MEDIUM,
            'version': 1,
        }

    @staticmethod
    def _impact_text(supporting: list[str], contradicting: list[str]) -> str:
        parts = []
        if supporting:
            parts.append(f"May increase likelihood of: {', '.join(supporting)}.")
        if contradicting:
            parts.append(f"May decrease likelihood of: {', '.join(contradicting)}.")
        return ' '.join(parts) or 'Clinical significance requires physician review.'
