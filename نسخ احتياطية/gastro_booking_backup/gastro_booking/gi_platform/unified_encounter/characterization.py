"""ODPARA / SOCRATES-style characterization — structured inputs from seeds/KB only."""

from __future__ import annotations

from typing import Any

from gi_platform.unified_encounter.seeds import (
    BLEED_TOKENS,
    CHARACTERIZATION_BANKS,
    PAIN_LIKE_TOKENS,
)

# Types allowed in characterization / discriminating batches (no bare free-text).
STRUCTURED_TYPES = frozenset({
    'boolean', 'choice', 'select', 'multiple_choice', 'multi_choice',
    'numeric', 'number', 'date', 'scale', 'duration',
})


def _family_for_complaint(complaint_code: str, symptom_name: str = '') -> str:
    blob = f'{complaint_code or ""} {symptom_name or ""}'.lower()
    if any(t in blob for t in BLEED_TOKENS):
        return 'bleed'
    if any(t in blob for t in PAIN_LIKE_TOKENS):
        return 'pain'
    return 'general'


def _normalize_atype(atype: str, choices: list | None, *, allow_text_comment: bool = False) -> str | None:
    at = (atype or 'text').lower().strip()
    if at in ('select', 'single_choice'):
        at = 'choice'
    if at in ('multiple_choice', 'multiselect', 'multi-select'):
        at = 'multi_choice'
    if at in ('number',):
        at = 'numeric'
    if at == 'scale':
        at = 'numeric'
    if at == 'duration':
        at = 'choice' if choices else 'numeric'
    if at == 'text':
        if allow_text_comment:
            return 'text'
        if choices:
            return 'multi_choice' if len(choices) > 6 else 'choice'
        return None
    if at in STRUCTURED_TYPES or at == 'text':
        return at
    if choices:
        return 'choice'
    return None


def _materialize(
    template: dict,
    *,
    prefix: str,
    symptom_name: str,
    symptom_id: int | None,
    complaint_code: str,
) -> dict | None:
    choices = list(template.get('choices') or [])
    allow_comment = bool(template.get('is_comment'))
    atype = _normalize_atype(
        template.get('answer_type') or 'choice',
        choices,
        allow_text_comment=allow_comment,
    )
    if not atype:
        return None
    # Never emit bare free-text in characterization unless explicitly a physician comment.
    if atype == 'text' and not allow_comment:
        return None
    prompt_tpl = template.get('prompt') or template.get('suffix') or ''
    prompt = prompt_tpl.replace('{symptom}', symptom_name or 'this symptom')
    out = {
        'code': f'{prefix}.{template["suffix"]}',
        'prompt': prompt,
        'answer_type': atype,
        'choices': choices,
        'help_text': template.get('help_text') or '',
        'symptom_id': symptom_id,
        'symptom_name': symptom_name,
        'complaint_code': complaint_code,
        'phase': 'characterization',
        'allow_other': bool(template.get('allow_other')) or ('Other' in choices),
        'optional': bool(template.get('optional')),
        'is_comment': allow_comment,
    }
    for key in ('min', 'max', 'step', 'unit'):
        if key in template:
            out[key] = template[key]
    return out


def odpara_questions(complaint_code: str, *, symptom_name: str = '', symptom_id: int | None = None) -> list[dict]:
    """Return structured characterization questions for one complaint (from seeds)."""
    family = _family_for_complaint(complaint_code, symptom_name)
    prefix = f'ue.char.{(complaint_code or "sx").replace(".", "_")}'
    banks = CHARACTERIZATION_BANKS
    templates: list[dict] = []
    templates.extend(banks.get('common') or [])
    templates.extend(banks.get(family) or [])
    templates.extend(banks.get('shared_tail') or [])

    out: list[dict] = []
    for tmpl in templates:
        q = _materialize(
            tmpl,
            prefix=prefix,
            symptom_name=symptom_name,
            symptom_id=symptom_id,
            complaint_code=complaint_code,
        )
        if q:
            out.append(q)
    return out


def complaint_specific_mcqs(
    db,
    complaint_code: str,
    *,
    symptom_id: int | None = None,
    symptom_name: str = '',
    answered: set[str] | None = None,
    limit: int = 12,
) -> list[dict]:
    """Pull complaint-linked trained / catalogue questions that are already structured."""
    answered = answered or set()
    out: list[dict] = []
    try:
        from gi_platform.clinical_history_ai.question_engine import HistoryQuestionEngine
        engine = HistoryQuestionEngine()
        trained = engine.load_questions_for_complaint(db, complaint_code)
        for tq in trained:
            atype_raw = (tq.get('question_type') or 'text').lower()
            choices = list(tq.get('answer_options') or [])
            atype = _normalize_atype(atype_raw, choices)
            if not atype or atype == 'text':
                continue
            code = tq['question_id']
            if code in answered:
                continue
            if atype == 'boolean' and not choices:
                choices = ['Yes', 'No', 'Unknown']
            if atype in ('choice', 'multi_choice') and not choices:
                continue
            out.append({
                'code': code,
                'prompt': tq['question_text'],
                'answer_type': atype,
                'choices': choices,
                'help_text': tq.get('clinical_purpose') or 'Complaint-specific discriminating detail.',
                'symptom_id': symptom_id,
                'symptom_name': symptom_name,
                'complaint_code': complaint_code,
                'phase': 'characterization',
                'allow_other': 'Other' in choices,
            })
            if len(out) >= limit:
                return out
    except Exception:
        pass
    return out


def assert_no_free_text_batch(questions: list[dict]) -> list[dict]:
    """Filter/guard: characterization batch must not contain bare free-text."""
    clean: list[dict] = []
    for q in questions:
        at = (q.get('answer_type') or '').lower()
        if at == 'text' and not q.get('is_comment') and not q.get('allow_other'):
            continue
        if at == 'text' and q.get('is_comment'):
            clean.append(q)
            continue
        if at not in STRUCTURED_TYPES and at != 'text':
            if q.get('choices'):
                q = dict(q)
                q['answer_type'] = 'choice'
                clean.append(q)
            continue
        clean.append(q)
    return clean


def build_characterization_queue(
    db,
    symptoms: list[dict],
    *,
    answered_codes: set[str] | None = None,
    current_index: int = 0,
    disease_codes: list[str] | None = None,
) -> dict[str, Any]:
    """
    One complaint at a time: ODPARA (+ SOCRATES if pain) first, then complaint-specific MCQs.
    For known-disease mode, append disease-context questions after ODPARA of current problem.
    """
    from gi_platform.unified_encounter.seeds import DISEASE_CONTEXT_QUESTIONS

    answered_codes = answered_codes or set()
    if not symptoms:
        return {
            'current_symptom': None,
            'index': 0,
            'total': 0,
            'questions': [],
            'complete': True,
        }

    idx = max(0, min(current_index, len(symptoms) - 1))
    sym = symptoms[idx]
    code = sym['complaint_code']
    name = sym.get('symptom_name') or code
    sid = sym.get('id')

    odpara = odpara_questions(code, symptom_name=name, symptom_id=sid)
    # Optional numeric/date/comment never block advancement.
    pending_required = [
        q for q in odpara
        if q['code'] not in answered_codes and not q.get('optional')
    ]
    pending_optional = [
        q for q in odpara
        if q['code'] not in answered_codes and q.get('optional') and not q.get('is_comment')
    ]
    if pending_required:
        # Full ODPARA/SOCRATES section in one form (one Save).
        # Optionals ride along; unanswered optionals never block advancement.
        batch = list(pending_required) + list(pending_optional)
        return {
            'current_symptom': sym,
            'index': idx,
            'total': len(symptoms),
            'questions': assert_no_free_text_batch(batch),
            'complete': False,
            'subphase': 'odpara' if _family_for_complaint(code, name) != 'pain' else 'odpara_socrates',
        }

    specific = complaint_specific_mcqs(
        db, code, symptom_id=sid, symptom_name=name,
        answered=answered_codes, limit=12,
    )
    pending_specific = [q for q in specific if q['code'] not in answered_codes]

    # Disease context once, after first complaint's ODPARA (known-disease mode).
    if disease_codes and idx == 0 and not pending_specific:
        for dcode in disease_codes:
            for dq in DISEASE_CONTEXT_QUESTIONS.get(dcode, []):
                if dq['code'] in answered_codes:
                    continue
                atype = _normalize_atype(dq.get('answer_type') or 'choice', dq.get('choices'))
                if not atype or atype == 'text':
                    continue
                pending_specific.append({
                    **dq,
                    'answer_type': atype,
                    'symptom_id': sid,
                    'symptom_name': name,
                    'complaint_code': code,
                    'phase': 'characterization',
                    'allow_other': 'Other' in (dq.get('choices') or []),
                })

    if pending_specific:
        return {
            'current_symptom': sym,
            'index': idx,
            'total': len(symptoms),
            'questions': assert_no_free_text_batch(pending_specific),
            'complete': False,
            'subphase': 'complaint_specific',
        }

    # This complaint done — caller should advance index.
    return {
        'current_symptom': sym,
        'index': idx,
        'total': len(symptoms),
        'questions': [],
        'complete': idx >= len(symptoms) - 1,
        'advance': True,
        'subphase': 'done',
    }
