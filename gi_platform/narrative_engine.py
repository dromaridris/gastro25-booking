"""Two-stage Clinical History Narrative Generation Engine."""

from __future__ import annotations

from gi_platform.catalogue_runtime import get_question, QuestionView
from gi_platform import history_service
from gi_platform.narrative.semantic import ClinicalFact, build_semantic_document, build_multi_symptom_hpi
from gi_platform.narrative.prose import render_from_semantic_document

SECTION_LABELS = {
    'hpi': 'History of Present Illness',
    'relevant_negatives': 'Relevant Negative Findings',
    'past_medical_history': 'Past Medical History',
    'surgical_history': 'Surgical History',
    'drug_history': 'Drug History',
    'allergy_history': 'Allergy History',
    'family_history': 'Family History',
    'social_history': 'Social History',
    'physical_examination': 'Physical Examination',
    'assessment': 'Assessment / Working Diagnosis',
    'plan': 'Plan',
}

HISTORY_SECTION_KEYS = (
    'hpi', 'relevant_negatives', 'past_medical_history', 'surgical_history',
    'drug_history', 'allergy_history', 'family_history', 'social_history',
    'physical_examination',
)


def _collect_facts(db, session_id: int, *, symptom_id: int | None = None) -> list[ClinicalFact]:
    facts: list[ClinicalFact] = []
    for ans in history_service.list_answers(db, session_id, symptom_id=symptom_id):
        if symptom_id is not None and ans['symptom_id'] not in (symptom_id, None):
            continue
        if symptom_id is None and ans['symptom_id'] is not None:
            continue
        q = get_question(db, ans['question_key'])
        if not q:
            continue
        facts.append(ClinicalFact(
            code=q.code,
            prompt=q.prompt,
            value=ans['answer_text'] or '',
            answer_type=q.answer_type,
            section=q.section or 'presenting',
        ))
    return facts


def _collect_all_facts(db, session_id: int) -> tuple[list[dict], dict[int | None, list[ClinicalFact]], list[ClinicalFact]]:
    from gi_platform.symptom_service import list_session_symptoms, sync_legacy_complaint, is_shared_question

    sync_legacy_complaint(db, session_id)
    symptoms = list_session_symptoms(db, session_id)
    facts_by_symptom: dict[int | None, list[ClinicalFact]] = {}
    shared: list[ClinicalFact] = []

    for ans in history_service.list_answers(db, session_id):
        q = get_question(db, ans['question_key'])
        if not q:
            # Trained AI questions may not be in KL catalogue.
            from gi_platform.history_ai_training.service import get_trained_question
            tq = get_trained_question(db, ans['question_key'])
            if tq:
                q = QuestionView(
                    code=tq['question_id'],
                    prompt=tq['question_text'],
                    section=tq.get('category', 'presenting'),
                    answer_type=tq.get('question_type', 'text'),
                )
            else:
                continue
        fact = ClinicalFact(
            code=q.code if hasattr(q, 'code') else q['question_id'],
            prompt=q.prompt if hasattr(q, 'prompt') else q['question_text'],
            value=ans['answer_text'] or '',
            answer_type=q.answer_type if hasattr(q, 'answer_type') else q.get('question_type', 'text'),
            section=(q.section if hasattr(q, 'section') else q.get('category')) or 'presenting',
        )
        sid = ans['symptom_id'] if 'symptom_id' in ans.keys() else None
        if sid is None and is_shared_question(fact.code, section=fact.section):
            shared.append(fact)
        else:
            facts_by_symptom.setdefault(sid, []).append(fact)

    if not symptoms and not facts_by_symptom:
        sess = history_service.get_session(db, session_id)
        if sess and sess['complaint_code']:
            symptoms = [{'id': None, 'complaint_code': sess['complaint_code'], 'symptom_name': sess['chief_complaint'] or ''}]
            facts_by_symptom[None] = _collect_facts(db, session_id)

    return symptoms, facts_by_symptom, shared


def generate_history_narrative(db, session_id: int, *, chief_complaint: str) -> dict[str, str]:
    """
    Stage 1 + Stage 2 narrative generation from structured answers only.
    Deterministic. No CDS / diagnosis logic. No invented facts.
    """
    symptoms, facts_by_symptom, shared = _collect_all_facts(db, session_id)
    if len(symptoms) > 1 or (symptoms and any(s.get('id') for s in symptoms)):
        hpi = build_multi_symptom_hpi(
            symptoms=symptoms, facts_by_symptom=facts_by_symptom, shared_facts=shared,
        )
        all_facts = [f for group in facts_by_symptom.values() for f in group] + shared
        semantic = build_semantic_document(chief_complaint=chief_complaint, facts=all_facts)
        from gi_platform.narrative.prose import render_background_sections, _quality_review
        sections = {'hpi': hpi, **render_background_sections(semantic)}
        return _quality_review(sections)

    facts = _collect_facts(db, session_id)
    semantic = build_semantic_document(chief_complaint=chief_complaint, facts=facts)
    return render_from_semantic_document(semantic)


def generate_history_note(db, session_id: int, *, examination_text: str = '') -> dict[str, str]:
    """History + examination only — no assessment or plan."""
    sess = history_service.get_session(db, session_id)
    if not sess:
        return {}

    complaint = sess['chief_complaint'] or sess['complaint_code'] or 'the presenting complaint'
    sections = generate_history_narrative(db, session_id, chief_complaint=complaint)
    sections['physical_examination'] = examination_text.strip() or (
        '[Physical examination — to be completed by examining clinician]\n\n'
        'General: \nAbdomen: \nOther: '
    )
    return sections


def generate_full_note(db, session_id: int, *, examination_text: str = '',
                       assessment_text: str = '', plan_text: str = '') -> dict[str, str]:
    """
    Assemble printable note sections.
    History portions use the narrative engine; assessment/plan are optional add-ons for print.
    """
    sections = generate_history_note(db, session_id, examination_text=examination_text)
    if assessment_text:
        sections['assessment'] = assessment_text
    if plan_text:
        sections['plan'] = plan_text
    return sections


def sections_to_history_text(sections: dict[str, str], *, patient_name: str = '', mrn: str = '') -> str:
    """History sections only — suitable for ward record / HPI block."""
    header = 'CLINICAL HISTORY NOTE\n'
    if patient_name:
        header += f'Patient: {patient_name}\n'
    if mrn:
        header += f'MRN: {mrn}\n'
    header += '—' * 40 + '\n\n'
    parts = [header]
    for key in HISTORY_SECTION_KEYS:
        if sections.get(key):
            parts.append(f"{SECTION_LABELS[key]}\n{sections[key]}\n\n")
    return ''.join(parts).strip()


def sections_to_print_text(sections: dict[str, str], *, patient_name: str = '', mrn: str = '') -> str:
    header = 'CLINICAL HISTORY & EXAMINATION NOTE\n'
    if patient_name:
        header += f'Patient: {patient_name}\n'
    if mrn:
        header += f'MRN: {mrn}\n'
    header += '—' * 40 + '\n\n'
    parts = [header]
    for key in HISTORY_SECTION_KEYS + ('assessment', 'plan'):
        if sections.get(key):
            parts.append(f"{SECTION_LABELS[key]}\n{sections[key]}\n\n")
    return ''.join(parts).strip()
