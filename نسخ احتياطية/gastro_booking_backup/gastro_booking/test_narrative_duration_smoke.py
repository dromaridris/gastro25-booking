"""Smoke: ward Generate History duration/onset prose (no DB required)."""

from __future__ import annotations

from gi_platform.narrative.semantic import ClinicalFact, build_multi_symptom_hpi, build_semantic_document
from gi_platform.narrative.prose import render_hpi_paragraph
from gi_platform.narrative.terminology import duration_as_timeline_phrase, phrase_from_fact


def _assert_no_robotic(text: str) -> None:
    bad = (
        'Symptoms had been Months',
        'Symptoms had been Years',
        'Symptoms had been Days',
        'Symptoms had been Weeks',
        'Symptoms started with',
        'Regarding the ',
    )
    for frag in bad:
        assert frag not in text, f'Robotic fragment still present: {frag!r} in {text!r}'
    assert 'had been present for' in text.lower() or "duration" in text.lower(), text


def test_phrase_from_bare_units() -> None:
    expected = {
        'Months': 'present for months',
        'Years': 'present for years',
        'Days': 'present for days',
        'Weeks': 'present for weeks',
        'Hours': 'present for a few hours',  # CHOICE_LABELS maps hours → a few hours
    }
    for raw, want in expected.items():
        phrase = phrase_from_fact('Symptom onset', raw, 'text', code='sym.onset')
        assert phrase == want, (raw, phrase, want)
        assert duration_as_timeline_phrase(raw) == want


def test_single_symptom_opening() -> None:
    doc = build_semantic_document(
        chief_complaint='dysphagia',
        facts=[
            ClinicalFact(
                code='sym.duration', prompt='Symptom duration', value='Months',
                answer_type='text', section='presenting',
            ),
        ],
    )
    hpi = render_hpi_paragraph(doc)
    print('SINGLE:', hpi)
    assert 'presented with dysphagia' in hpi.lower()
    assert 'months' in hpi.lower()
    assert 'Symptoms had been Months' not in hpi
    _assert_no_robotic(hpi)


def test_multi_symptom_user_case() -> None:
    """Reproduces the angry-user screenshot case."""
    symptoms = [
        {'id': 1, 'symptom_name': 'dysphagia', 'onset_text': 'Months', 'complaint_code': 'hist.dysphagia'},
        {'id': 2, 'symptom_name': 'weight loss', 'onset_text': 'Years', 'complaint_code': 'hist.weight_loss'},
        {'id': 3, 'symptom_name': 'chronic liver disease', 'onset_text': 'Years', 'complaint_code': 'hist.cld'},
    ]
    facts_by_symptom = {1: [], 2: [], 3: []}
    hpi = build_multi_symptom_hpi(
        symptoms=symptoms, facts_by_symptom=facts_by_symptom, shared_facts=[],
    )
    print('MULTI:', hpi)
    assert 'presented with dysphagia' in hpi.lower()
    assert 'months' in hpi.lower()
    assert 'regarding' in hpi.lower()
    assert 'weight loss' in hpi.lower() or 'unintentional weight loss' in hpi.lower()
    assert 'years' in hpi.lower()
    assert 'Symptoms had been Months' not in hpi
    assert 'Symptoms had been Years' not in hpi
    assert 'Symptoms started with' not in hpi
    _assert_no_robotic(hpi)


def main() -> None:
    test_phrase_from_bare_units()
    test_single_symptom_opening()
    test_multi_symptom_user_case()
    print('narrative_duration smoke: OK')


if __name__ == '__main__':
    main()
