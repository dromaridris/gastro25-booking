"""Runtime catalogue index + adaptive history engine (ported from GI clinical_history)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from gi_platform.cds_service import AssessmentResult
from gi_platform import history_service

# Semantic families — asked once per session across all symptoms.
_FAMILY_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ('alcohol', re.compile(r'\balcohol\b', re.I)),
    ('smoking', re.compile(r'\bsmok', re.I)),
    ('allergy', re.compile(r'\ballerg', re.I)),
    ('medications', re.compile(r'\b(medication|medicines?|drugs?\b|current regular)', re.I)),
)


@dataclass
class QuestionView:
    code: str
    prompt: str
    section: str
    answer_type: str
    choices: list | None = None
    is_exclusion: bool = False
    help_text: str | None = None
    symptom_id: int | None = None
    symptom_name: str | None = None
    complaint_code: str | None = None


# Structured options for common free-text social / context questions.
_STRUCTURED_OVERRIDES: dict[str, tuple[str, list[str], str]] = {
    'q.common.alcohol_social': (
        'choice',
        ['None', 'Occasional', 'Regular', 'Heavy'],
        'Alcohol use affects bleeding risk, liver disease, pancreatitis, and malignancy work-up.',
    ),
    'q.common.smoking': (
        'choice',
        ['never', 'former', 'current'],
        'Smoking is a risk factor for peptic ulcer, malignancy, and CVD comorbidity.',
    ),
    'q.common.allergy': (
        'choice',
        ['None known', 'Yes — drug allergy', 'Yes — other', 'Unknown'],
        'Drug allergies change safe prescribing before endoscopy or antibiotics.',
    ),
    'q.common.surgical': (
        'choice',
        ['No prior surgery', 'Prior abdominal/GI surgery', 'Other surgery', 'Unknown'],
        'Prior abdominal surgery changes obstruction and adhesion risk.',
    ),
}


def question_family(code: str, prompt: str = '') -> str | None:
    blob = f'{code or ""} {prompt or ""}'
    for name, pat in _FAMILY_PATTERNS:
        if pat.search(blob):
            return name
    return None


_DURATION_CHOICES = ['Hours', 'Days', 'Weeks', 'Months', 'Years']
_YES_NO_UNKNOWN = ['Yes', 'No', 'Unknown']


def normalize_question_view(q: QuestionView) -> QuestionView:
    """Ensure analyzable questions use structured widgets when metadata allows.
    Never leave free-text when choices or a structured type exists.
    """
    override = _STRUCTURED_OVERRIDES.get(q.code)
    if override:
        atype, choices, help_default = override
        q.answer_type = atype
        q.choices = choices
        if not q.help_text:
            q.help_text = help_default

    # Apply unified-encounter / KB patches by question id (Q000xxx).
    try:
        from gi_platform.unified_encounter.seeds import KB_STRUCTURED_PATCHES
        patch = KB_STRUCTURED_PATCHES.get(q.code)
        if patch:
            q.answer_type = patch.get('answer_type') or q.answer_type
            if patch.get('choices') is not None:
                q.choices = list(patch['choices'])
    except Exception:
        pass

    atype = (q.answer_type or 'text').lower()
    if atype == 'duration':
        q.answer_type = 'choice'
        q.choices = q.choices or list(_DURATION_CHOICES)
        atype = 'choice'
    if atype == 'scale':
        q.answer_type = 'numeric'
        atype = 'numeric'
    if atype in ('multiple_choice', 'multiselect', 'multi-select'):
        q.answer_type = 'multi_choice'
        atype = 'multi_choice'
    if q.choices and atype == 'text':
        q.answer_type = 'choice'
        atype = 'choice'
    if atype == 'boolean' and not q.choices:
        q.choices = list(_YES_NO_UNKNOWN)
    return q


def list_complaints(db) -> list[dict]:
    rows = db.execute(
        """
        SELECT slug, title, body_json FROM gi_knowledge_object
        WHERE object_type = 'complaint' AND status = 'published'
        ORDER BY json_extract(body_json, '$.sort_order'), title
        """
    ).fetchall()
    out = []
    for r in rows:
        body = json.loads(r['body_json'] or '{}')
        out.append({
            'code': body.get('complaint_code', r['slug']),
            'name': r['title'],
            'category': body.get('category', 'gi'),
        })
    return out


def get_question(db, question_code: str) -> QuestionView | None:
    slug = f"kl.question.{question_code.replace('.', '_')}"
    row = db.execute(
        "SELECT title, body_json FROM gi_knowledge_object WHERE slug = ? OR body_json LIKE ?",
        (slug, f'%"question_code": "{question_code}"%'),
    ).fetchone()
    if not row:
        return None
    body = json.loads(row['body_json'] or '{}')
    return normalize_question_view(QuestionView(
        code=body.get('question_code', question_code),
        prompt=body.get('prompt') or row['title'],
        section=body.get('section', 'presenting'),
        answer_type=body.get('answer_type', 'text'),
        choices=body.get('choices'),
        is_exclusion=bool(body.get('is_exclusion_question')),
        help_text=body.get('help_text') or body.get('clinical_purpose'),
    ))


def _session_answered_codes(db, session_id: int) -> set[str]:
    """All question codes answered anywhere in the session (any symptom)."""
    return set(history_service.get_answers_map(db, session_id).keys())


def _session_answered_families(db, session_id: int) -> set[str]:
    answered = set()
    for key, val in history_service.get_answers_map(db, session_id).items():
        if not (val or '').strip():
            continue
        fam = question_family(key)
        if fam:
            answered.add(fam)
    return answered


def _rules_for_complaint(db, complaint_code: str, rule_kind: str) -> list[dict]:
    rows = db.execute(
        """
        SELECT body_json FROM gi_knowledge_object
        WHERE object_type = 'cds_rule' AND status = 'published'
          AND json_extract(body_json, '$.complaint_code') = ?
          AND json_extract(body_json, '$.rule_kind') = ?
        """,
        (complaint_code, rule_kind),
    ).fetchall()
    return [json.loads(r['body_json'] or '{}') for r in rows]


def _priors(db, complaint_code: str) -> dict[str, float]:
    scores: dict[str, float] = {}
    for body in _rules_for_complaint(db, complaint_code, 'prior'):
        dx = body.get('diagnosis_code')
        if dx:
            scores[dx] = scores.get(dx, 0.0) + float(body.get('prior_weight', 1.0))
    return scores


def compute_differential_for_session(db, complaint_code: str, session_id: int) -> AssessmentResult:
    from gi_platform.decision_support.adapters import build_context_from_session, to_legacy_result
    from gi_platform.decision_support.service import get_decision_support_service

    ctx = build_context_from_session(
        db, session_id=session_id, complaint_code=complaint_code, teaching_mode=False,
    )
    if not ctx.complaint_code:
        return AssessmentResult()
    result = get_decision_support_service(db).assess(ctx)
    return to_legacy_result(result)


def get_next_questions(
    db, complaint_code: str, session_id: int, batch_size: int = 3,
    symptom_id: int | None = None,
    *,
    skip_families: set[str] | None = None,
    skip_codes: set[str] | None = None,
) -> list[QuestionView]:
    from gi_platform.decision_support.adapters import build_context_from_session, question_rec_to_view
    from gi_platform.decision_support.engines.adaptive_history_engine import recommend_next_questions
    from gi_platform.decision_support.knowledge_accessor import CdsKnowledgeAccessor
    from gi_platform.clinical_history_ai.question_engine import HistoryQuestionEngine
    from gi_platform.symptom_service import is_shared_question

    # Symptom-scoped answers for branching; session-wide for shared/dedupe.
    answers = history_service.get_answers_map(db, session_id, symptom_id=symptom_id)
    session_answered = _session_answered_codes(db, session_id)
    answered_families = _session_answered_families(db, session_id) | (skip_families or set())
    blocked_codes = set(skip_codes or set()) | session_answered

    def _already_covered(code: str, prompt: str = '', section: str = '') -> bool:
        if code in blocked_codes or code in answers:
            return True
        if is_shared_question(code, section=section) and code in session_answered:
            return True
        fam = question_family(code, prompt)
        if fam and fam in answered_families:
            return True
        return False

    def _accept(q: QuestionView) -> QuestionView | None:
        q = normalize_question_view(q)
        if _already_covered(q.code, q.prompt or '', q.section or ''):
            return None
        fam = question_family(q.code, q.prompt or '')
        if fam:
            answered_families.add(fam)
        blocked_codes.add(q.code)
        return q

    ctx = build_context_from_session(db, session_id=session_id, complaint_code=complaint_code)
    # Session-wide answered codes so adaptive engine skips shared items already done.
    ctx.answered_question_codes = set(ctx.answered_question_codes or set()) | session_answered
    accessor = CdsKnowledgeAccessor(db)
    recs = recommend_next_questions(ctx, accessor, batch_size=batch_size * 3)

    visible: list[QuestionView] = []
    for rec in recs:
        if _already_covered(rec.question_code, rec.prompt or ''):
            continue
        q = _accept(question_rec_to_view(rec, db=db))
        if q:
            if not q.help_text and rec.rationale:
                q.help_text = rec.rationale
            visible.append(q)
        if len(visible) >= batch_size:
            return visible

    # AI-trained questions (admin-configured branching).
    engine = HistoryQuestionEngine()
    trained = engine.load_questions_for_complaint(db, complaint_code)
    # Branching uses full session answers, with symptom-scoped values taking precedence.
    trained_answers = {**history_service.get_answers_map(db, session_id), **answers}
    for tq in trained:
        qid = tq['question_id']
        if _already_covered(qid, tq.get('question_text') or '', tq.get('category') or ''):
            continue
        if not engine._should_show(db, tq, trained_answers, {'complaint_code': complaint_code}):
            continue
        q = _accept(QuestionView(
            code=qid,
            prompt=tq['question_text'],
            section=tq.get('category', 'presenting'),
            answer_type=tq.get('question_type', 'text'),
            choices=tq.get('answer_options') or None,
            is_exclusion=bool(tq.get('is_required')),
            help_text=tq.get('clinical_purpose'),
        ))
        if q:
            visible.append(q)
        if len(visible) >= batch_size:
            return visible

    rules = _rules_for_complaint(db, complaint_code, 'question')
    rules.sort(key=lambda b: int(b.get('sort_order', 9999)))

    # Merge configurable History Designer questions (Settings → History Templates).
    from gi_platform import history_template_service
    for tq in history_template_service.template_questions_for_complaint(db, complaint_code):
        if not _already_covered(tq['code'], tq.get('prompt') or '', tq.get('section') or ''):
            rules.append({
                'question_code': tq['code'],
                'sort_order': 50,
                '_template': tq,
                'clinical_rationale': tq.get('help_text'),
            })

    for body in rules:
        qcode = body.get('question_code')
        if not qcode or _already_covered(qcode, body.get('prompt') or ''):
            continue
        parent = body.get('parent_question_code')
        required = body.get('parent_answer_required')
        if parent:
            parent_ans = str(answers.get(parent) or history_service.get_answers_map(db, session_id).get(parent, '')).lower()
            if required and str(required).lower() not in parent_ans and parent_ans not in ('yes', 'true', '1'):
                continue
        q = get_question(db, qcode)
        if not q and body.get('_template'):
            tq = body['_template']
            q = QuestionView(
                code=tq['code'],
                prompt=tq['prompt'],
                section=tq.get('section', 'presenting'),
                answer_type=tq.get('answer_type', 'text'),
                choices=tq.get('choices'),
                is_exclusion=bool(tq.get('is_exclusion')),
                help_text=tq.get('help_text'),
            )
        if q:
            rationale = body.get('clinical_rationale')
            if rationale and not q.help_text:
                q.help_text = rationale
            q = _accept(q)
            if q:
                visible.append(q)
        if len(visible) >= batch_size:
            break

    if not visible:
        for row in db.execute(
            """
            SELECT body_json, title FROM gi_knowledge_object
            WHERE object_type = 'history_question' AND status = 'published'
            AND (body_json LIKE ? OR body_json LIKE '%"complaint_code": null%')
            ORDER BY title LIMIT 20
            """,
            (f'%"complaint_code": "{complaint_code}"%',),
        ).fetchall():
            body = json.loads(row['body_json'] or '{}')
            code = body.get('question_code')
            if not code or _already_covered(code, body.get('prompt') or '', body.get('section') or ''):
                continue
            q = _accept(QuestionView(
                code=code,
                prompt=body.get('prompt', row['title']),
                section=body.get('section', ''),
                answer_type=body.get('answer_type', 'text'),
                choices=body.get('choices'),
                is_exclusion=bool(body.get('is_exclusion_question')),
                help_text=body.get('help_text'),
            ))
            if q:
                visible.append(q)
            if len(visible) >= batch_size:
                break
    return visible


def get_next_questions_for_session(
    db, session_id: int, *, batch_size: int = 3,
) -> tuple[list[QuestionView], bool]:
    """Return pending questions across all session symptoms + shared session questions."""
    from gi_platform.symptom_service import list_session_symptoms, sync_legacy_complaint

    sync_legacy_complaint(db, session_id)
    ensure_structured_common_questions(db)
    symptoms = list_session_symptoms(db, session_id)
    if not symptoms:
        sess = history_service.get_session(db, session_id)
        if sess and sess['complaint_code']:
            symptoms = [{'id': None, 'complaint_code': sess['complaint_code'], 'symptom_name': sess['chief_complaint'] or ''}]
        else:
            return [], False

    pending: list[QuestionView] = []
    all_complete = True
    skip_families = _session_answered_families(db, session_id)
    skip_codes: set[str] = set()
    for sym in symptoms:
        sid = sym.get('id')
        code = sym['complaint_code']
        need = max(1, batch_size - len(pending))
        qs = get_next_questions(
            db, code, session_id, batch_size=need, symptom_id=sid,
            skip_families=skip_families, skip_codes=skip_codes,
        )
        if qs:
            all_complete = False
        for q in qs:
            q.symptom_id = sid
            q.symptom_name = sym.get('symptom_name')
            q.complaint_code = code
            pending.append(q)
            skip_codes.add(q.code)
            fam = question_family(q.code, q.prompt or '')
            if fam:
                skip_families.add(fam)
        if len(pending) >= batch_size:
            return pending[:batch_size], False

    shared = _shared_session_questions(
        db, session_id, batch_size=max(1, batch_size - len(pending)),
        skip_families=skip_families, skip_codes=skip_codes,
    )
    if shared:
        all_complete = False
        pending.extend(shared)
    return pending[:batch_size], all_complete and not shared


def ensure_structured_common_questions(db) -> int:
    """Patch published common questions so alcohol/allergy/etc. are choice, not free text."""
    updated = 0
    for code, (atype, choices, help_text) in _STRUCTURED_OVERRIDES.items():
        slug = f"kl.question.{code.replace('.', '_')}"
        row = db.execute(
            "SELECT id, body_json FROM gi_knowledge_object WHERE slug = ?", (slug,),
        ).fetchone()
        if not row:
            continue
        body = json.loads(row['body_json'] or '{}')
        if body.get('answer_type') == atype and body.get('choices') == choices:
            continue
        body['answer_type'] = atype
        body['choices'] = choices
        if not body.get('help_text'):
            body['help_text'] = help_text
        # Prefer the structured prompt wording for alcohol.
        if code == 'q.common.alcohol_social':
            body['prompt'] = 'Alcohol use?'
        db.execute(
            "UPDATE gi_knowledge_object SET body_json = ?, title = COALESCE(?, title) WHERE id = ?",
            (json.dumps(body), body.get('prompt'), row['id']),
        )
        updated += 1
    if updated:
        db.commit()
    return updated


def _shared_session_questions(
    db, session_id: int, *, batch_size: int = 3,
    skip_families: set[str] | None = None,
    skip_codes: set[str] | None = None,
) -> list[QuestionView]:
    """Session-level questions (medications, PMH, etc.) asked once."""
    from gi_platform.clinical_history_ai.question_engine import HistoryQuestionEngine
    from gi_platform.symptom_service import is_shared_question

    answers = history_service.get_answers_map(db, session_id, symptom_id=None)
    answered_families = _session_answered_families(db, session_id) | (skip_families or set())
    blocked = set(skip_codes or set())
    engine = HistoryQuestionEngine()
    questions = engine.load_questions_for_complaint(db, '__default__')
    out: list[QuestionView] = []
    for q in questions:
        qid = q['question_id']
        prompt = q.get('question_text') or ''
        section = q.get('category', '')
        if not is_shared_question(qid, section=section):
            continue
        if qid in answers or qid in blocked:
            continue
        fam = question_family(qid, prompt)
        if fam and fam in answered_families:
            continue
        view = normalize_question_view(QuestionView(
            code=qid,
            prompt=prompt,
            section=section or 'pmh',
            answer_type=q.get('question_type', 'text'),
            choices=q.get('answer_options') or None,
            help_text=q.get('clinical_purpose'),
        ))
        out.append(view)
        blocked.add(qid)
        if fam:
            answered_families.add(fam)
        if len(out) >= batch_size:
            break
    return out


def session_interview_complete(db, session_id: int) -> bool:
    _, complete = get_next_questions_for_session(db, session_id, batch_size=1)
    return complete


def interview_complete(
    db, complaint_code: str, session_id: int, *, symptom_id: int | None = None,
) -> bool:
    if not complaint_code:
        return False
    return len(get_next_questions(db, complaint_code, session_id, batch_size=1, symptom_id=symptom_id)) == 0


def build_narrative(db, session_id: int) -> str:
    from gi_platform.narrative_engine import generate_history_note, sections_to_history_text

    sess = history_service.get_session(db, session_id)
    if not sess:
        return ''

    exam = sess['examination_text'] if 'examination_text' in sess.keys() else ''
    sections = generate_history_note(db, session_id, examination_text=exam or '')
    patient_name, mrn = '', sess['mrn'] or ''
    if sess['ward_patient_id']:
        wp = db.execute(
            'SELECT patient_name, mrn FROM ward_patient WHERE id = ?', (sess['ward_patient_id'],)
        ).fetchone()
        if wp:
            patient_name, mrn = wp['patient_name'], mrn or wp['mrn'] or ''
    return sections_to_history_text(sections, patient_name=patient_name, mrn=mrn)
