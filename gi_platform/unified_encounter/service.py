"""Unified encounter state machine + workflow view for ward clinical workflow."""

from __future__ import annotations

import json
from typing import Any

from gi_platform.unified_encounter.seeds import CURRENT_PROBLEMS, KNOWN_DISEASES

STAGE_LABELS = {
    'mode_select': 'Encounter type',
    'complaints': 'Chief complaints',
    'known_diseases': 'Known disease(s)',
    'current_problem': 'Current clinical problem',
    'characterization': 'Complaint characterization',
    'initial_reasoning': 'Initial differential',
    'discriminating': 'Discriminating questions',
    'history_summary': 'History summary',
    'examination': 'Examination',
    'investigations': 'Investigations',
    'plan': 'Plan',
}

DIAGNOSTIC_FLOW = [
    'mode_select', 'complaints', 'characterization', 'initial_reasoning',
    'discriminating', 'history_summary', 'examination', 'investigations', 'plan',
]
KNOWN_FLOW = [
    'mode_select', 'known_diseases', 'current_problem', 'characterization',
    'initial_reasoning', 'discriminating', 'history_summary', 'examination',
    'investigations', 'plan',
]


def ensure_schema(db) -> None:
    cols = {r[1] for r in db.execute('PRAGMA table_info(gi_history_session)').fetchall()}
    if 'encounter_state_json' not in cols:
        db.execute(
            "ALTER TABLE gi_history_session ADD COLUMN encounter_state_json TEXT DEFAULT '{}'"
        )
        db.commit()


def _default_state() -> dict:
    return {
        'mode': None,
        'stage': 'mode_select',
        'characterization_index': 0,
        'known_disease_codes': [],
        'current_problem_codes': [],
        'ckp_session_id': None,
        'exam_findings': {},
        'exam_normal': [],
        'exam_other': '',
        'exam_other': '',
        'ix_checked': [],
        'differential_snapshot': [],
        'started': False,
    }


def get_state(db, session_id: int) -> dict:
    ensure_schema(db)
    row = db.execute(
        'SELECT encounter_state_json FROM gi_history_session WHERE id = ?',
        (session_id,),
    ).fetchone()
    raw = ''
    if row:
        try:
            raw = row['encounter_state_json'] or ''
        except Exception:
            raw = ''
    state = _default_state()
    if raw:
        try:
            loaded = json.loads(raw)
            if isinstance(loaded, dict):
                state.update(loaded)
        except Exception:
            pass
    return state


def save_state(db, session_id: int, state: dict) -> None:
    ensure_schema(db)
    db.execute(
        """
        UPDATE gi_history_session
        SET encounter_state_json = ?, updated_at = datetime('now')
        WHERE id = ?
        """,
        (json.dumps(state), session_id),
    )
    db.commit()


def _flow_for(mode: str | None) -> list[str]:
    if mode == 'known_disease':
        return KNOWN_FLOW
    if mode == 'diagnostic':
        return DIAGNOSTIC_FLOW
    return ['mode_select']


def advance_stage(state: dict, *, to: str | None = None) -> dict:
    flow = _flow_for(state.get('mode'))
    if to:
        if to in flow:
            state['stage'] = to
        return state
    cur = state.get('stage') or 'mode_select'
    try:
        i = flow.index(cur)
    except ValueError:
        state['stage'] = flow[0]
        return state
    if i + 1 < len(flow):
        state['stage'] = flow[i + 1]
    return state


def _answered_codes(db, session_id: int) -> set[str]:
    from gi_platform import history_service
    return set(history_service.get_answers_map(db, session_id).keys())


def _extract_structured_answer(
    form,
    *,
    field_name: str = 'answer_text',
    answer_type: str | None = None,
    other_key: str = 'other_specify',
    unit_key: str = 'unit',
    comment_key: str = 'physician_comment',
) -> tuple[str, dict]:
    """
    Prefer structured widgets: multi-select checkboxes, single choice, numeric, date.
    Free text only via Other (specify) / physician comment fields.
    """
    meta: dict[str, Any] = {}
    atype = (answer_type if answer_type is not None else (form.get('answer_type') or '')).strip().lower()

    multi: list[str] = []
    if hasattr(form, 'getlist'):
        multi = [str(v).strip() for v in form.getlist(field_name) if str(v).strip()]
    if multi and atype in ('multi_choice', 'multiple_choice', 'multiselect'):
        other = (form.get(other_key) or '').strip()
        if other and any(v.lower().startswith('other') for v in multi):
            multi = [v if not v.lower().startswith('other') else f'Other: {other}' for v in multi]
            meta['other_specify'] = other
        meta['selections'] = multi
        return '; '.join(multi), meta

    answer = (form.get(field_name) or '').strip()
    if not answer and multi:
        answer = '; '.join(multi)

    other = (form.get(other_key) or '').strip()
    if other:
        meta['other_specify'] = other
        if answer.lower() in ('other', 'yes — other', 'yes - other') or answer.lower().startswith('other'):
            answer = f'Other: {other}'
        elif 'Other' in answer and ':' not in answer:
            answer = f'{answer}: {other}'
        elif not answer:
            answer = other

    comment = (form.get(comment_key) or '').strip()
    if comment:
        meta['physician_comment'] = comment
        if not answer or answer == '__comment__':
            answer = comment

    if atype in ('numeric', 'number', 'scale') and answer:
        unit = (form.get(unit_key) or '').strip()
        meta['numeric'] = answer
        if unit:
            meta['unit'] = unit
    if atype == 'date' and answer:
        meta['date'] = answer

    return answer, meta


def _batch_question_codes(form) -> list[str]:
    """Unique question codes from ans__/atype__ fields in a section form."""
    codes: list[str] = []
    seen: set[str] = set()
    keys = list(form.keys()) if hasattr(form, 'keys') else []
    for key in keys:
        k = str(key)
        code = None
        if k.startswith('ans__'):
            code = k[5:]
        elif k.startswith('atype__'):
            code = k[7:]
        if code and code not in seen:
            seen.add(code)
            codes.append(code)
    return codes


def _extract_answer_for_code(form, code: str) -> tuple[str, dict, bool]:
    """Return (answer, meta, optional) for one question in a batch section form."""
    atype = (form.get(f'atype__{code}') or '').strip().lower()
    optional = (form.get(f'optional__{code}') or '').strip() in ('1', 'true', 'yes')
    answer, meta = _extract_structured_answer(
        form,
        field_name=f'ans__{code}',
        answer_type=atype,
        other_key=f'other__{code}',
        unit_key=f'unit__{code}',
        comment_key=f'comment__{code}',
    )
    return answer, meta, optional


def _save_batch_answers(db, session_id: int, state: dict, form) -> tuple[int, str | None]:
    """
    Persist all ans__* fields from a section form.
    Returns (saved_count, error_message).
    """
    from gi_platform import history_service

    codes = _batch_question_codes(form)
    if not codes:
        return 0, 'No answers in this section.'
    saved = 0
    for code in codes:
        answer, meta, optional = _extract_answer_for_code(form, code)
        if not answer and optional:
            answer = 'Not recorded'
        if not answer:
            return saved, f'Answer required for: {code}'
        try:
            symptom_id = int(form.get(f'sid__{code}') or 0) or None
        except Exception:
            symptom_id = None
        history_service.save_answer(
            db, session_id, code, answer,
            answer_json=meta or None,
            symptom_id=symptom_id,
        )
        _sync_ckp_answer(db, state, code, answer)
        saved += 1
    return saved, None


def _try_start_ckp(db, session_id: int, state: dict, complaints: list[str]) -> None:
    if state.get('ckp_session_id'):
        return
    try:
        from clinical_knowledge_platform.seed_demo import seed_demo_gastroenterology
        from clinical_knowledge_platform.workflow.controller import EncounterController
        seed_demo_gastroenterology(db)
        ctrl = EncounterController.start(db, patient_label=f'ward_session_{session_id}')
        if complaints:
            ctrl.intake(complaints)
        state['ckp_session_id'] = ctrl.session_id
    except Exception:
        state['ckp_session_id'] = None


def _sync_ckp_answer(db, state: dict, question_code: str, answer_text: str) -> None:
    ckp_id = state.get('ckp_session_id')
    if not ckp_id:
        return
    ans = (answer_text or '').strip().lower()
    if ans in ('yes', 'y', 'present', 'true'):
        polarity = 'present'
    elif ans in ('no', 'n', 'absent', 'false', 'none'):
        polarity = 'absent'
    else:
        polarity = 'unknown'
    try:
        from clinical_knowledge_platform.workflow.controller import EncounterController
        ctrl = EncounterController(db, int(ckp_id))
        ctrl.answer_question(question_code, polarity, value=answer_text)
    except Exception:
        pass


def _map_current_problems_to_symptoms(problem_codes: list[str]) -> list[dict]:
    by_code = {p['code']: p for p in CURRENT_PROBLEMS}
    items = []
    for i, code in enumerate(problem_codes):
        p = by_code.get(code)
        if not p:
            continue
        mapped = (p.get('maps_complaint') or '').strip()
        if not mapped:
            continue
        items.append({
            'complaint_code': mapped,
            'onset_text': '',
            'is_primary': i == 0,
            'symptom_name': p['label'],
        })
    return items


def handle_action(db, session_id: int, action: str, form) -> tuple[dict, str]:
    """
    Process a POST action. Returns (state, flash_message).
    form: request.form-like mapping with getlist support.
    """
    from gi_platform import history_service, symptom_service
    from gi_platform.unified_encounter.characterization import build_characterization_queue
    from gi_platform.unified_encounter.differential import build_enriched_differential
    from gi_platform.unified_encounter.exam_ix import build_exam_checklist, format_exam_text

    state = get_state(db, session_id)
    msg = ''

    if action == 'set_mode':
        mode = (form.get('encounter_mode') or '').strip()
        if mode not in ('diagnostic', 'known_disease'):
            return state, 'Choose an encounter type.'
        state = _default_state()
        state['mode'] = mode
        state['started'] = True
        state['stage'] = 'complaints' if mode == 'diagnostic' else 'known_diseases'
        save_state(db, session_id, state)
        return state, (
            'New Diagnostic Encounter started.'
            if mode == 'diagnostic'
            else 'Known Disease Follow-up / New Problem started.'
        )

    if action == 'reset_encounter':
        state = _default_state()
        save_state(db, session_id, state)
        return state, 'Encounter reset — choose a mode to begin.'

    if action == 'set_complaints':
        codes = form.getlist('complaint_codes') if hasattr(form, 'getlist') else form.get('complaint_codes') or []
        if isinstance(codes, str):
            codes = [codes]
        primary = (form.get('primary_complaint') or '').strip()
        items = []
        for idx, code in enumerate(codes):
            code = (code or '').strip()
            if not code:
                continue
            onset = (form.get(f'onset_{code}') or '').strip()
            items.append({
                'complaint_code': code,
                'onset_text': onset,
                'is_primary': code == primary or (not primary and idx == 0),
            })
        if not items:
            return state, 'Select at least one chief complaint.'
        symptom_service.set_session_symptoms(db, session_id, symptoms=items)
        labels = [s.get('symptom_name') or s['complaint_code'] for s in symptom_service.list_session_symptoms(db, session_id)]
        _try_start_ckp(db, session_id, state, labels)
        state['characterization_index'] = 0
        state['stage'] = 'characterization'
        save_state(db, session_id, state)
        return state, f'Started characterization for {len(items)} complaint(s).'

    if action == 'set_known_diseases':
        codes = form.getlist('known_disease_codes') if hasattr(form, 'getlist') else []
        if not codes:
            return state, 'Select at least one known disease.'
        state['known_disease_codes'] = [c for c in codes if c]
        state['stage'] = 'current_problem'
        save_state(db, session_id, state)
        return state, 'Known disease(s) recorded.'

    if action == 'set_current_problems':
        codes = form.getlist('current_problem_codes') if hasattr(form, 'getlist') else []
        if not codes:
            return state, 'Select at least one current clinical problem.'
        state['current_problem_codes'] = [c for c in codes if c]
        items = _map_current_problems_to_symptoms(state['current_problem_codes'])
        if items:
            symptom_service.set_session_symptoms(db, session_id, symptoms=items)
        labels = [s.get('symptom_name') or s['complaint_code'] for s in symptom_service.list_session_symptoms(db, session_id)]
        disease_labels = [
            d['label'] for d in KNOWN_DISEASES if d['code'] in state.get('known_disease_codes', [])
        ]
        _try_start_ckp(db, session_id, state, labels + disease_labels)
        state['characterization_index'] = 0
        state['stage'] = 'characterization'
        save_state(db, session_id, state)
        return state, 'Current problem set — characterize next.'

    if action in ('save_char_section', 'save_char_answer'):
        # Section save (preferred): all ans__* in one POST.
        # Legacy save_char_answer: single question_key + answer_text.
        if action == 'save_char_section' or _batch_question_codes(form):
            n, err = _save_batch_answers(db, session_id, state, form)
            if err:
                return state, err
        else:
            qkey = (form.get('question_key') or '').strip()
            answer, meta = _extract_structured_answer(form)
            try:
                symptom_id = int(form.get('symptom_id') or 0) or None
            except Exception:
                symptom_id = None
            optional = (form.get('optional') or '').strip() in ('1', 'true', 'yes')
            if not qkey:
                return state, 'Question key required.'
            if not answer and not optional:
                return state, 'Answer required.'
            if not answer and optional:
                answer = 'Not recorded'
            history_service.save_answer(
                db, session_id, qkey, answer,
                answer_json=meta or None,
                symptom_id=symptom_id,
            )
            _sync_ckp_answer(db, state, qkey, answer)
            n = 1

        # Advance characterization index when current complaint done
        symptoms = symptom_service.list_session_symptoms(db, session_id)
        answered = _answered_codes(db, session_id)
        queue = build_characterization_queue(
            db, symptoms,
            answered_codes=answered,
            current_index=int(state.get('characterization_index') or 0),
            disease_codes=state.get('known_disease_codes') or [],
        )
        if queue.get('advance') and not queue.get('complete'):
            state['characterization_index'] = int(state.get('characterization_index') or 0) + 1
            save_state(db, session_id, state)
            return state, f'Section saved ({n}) — next complaint.'
        if queue.get('complete') and not queue.get('questions'):
            state['stage'] = 'initial_reasoning'
            diff = build_enriched_differential(db, session_id, ckp_session_id=state.get('ckp_session_id'))
            state['differential_snapshot'] = diff.get('diagnoses') or []
            save_state(db, session_id, state)
            return state, f'Characterization complete ({n} saved) — initial differential ready.'
        save_state(db, session_id, state)
        return state, f'Section saved ({n}).'

    if action == 'finish_characterization':
        state['stage'] = 'initial_reasoning'
        diff = build_enriched_differential(db, session_id, ckp_session_id=state.get('ckp_session_id'))
        state['differential_snapshot'] = diff.get('diagnoses') or []
        save_state(db, session_id, state)
        return state, 'Moved to initial reasoning.'

    if action == 'confirm_initial_reasoning':
        state['stage'] = 'discriminating'
        save_state(db, session_id, state)
        return state, 'Continue with discriminating questions.'

    if action in ('save_disc_section', 'save_disc_answer'):
        # One section save → one differential refresh (affects site decisions once).
        if action == 'save_disc_section' or _batch_question_codes(form):
            n, err = _save_batch_answers(db, session_id, state, form)
            if err:
                return state, err
        else:
            qkey = (form.get('question_key') or '').strip()
            answer, meta = _extract_structured_answer(form)
            try:
                symptom_id = int(form.get('symptom_id') or 0) or None
            except Exception:
                symptom_id = None
            if not qkey or not answer:
                return state, 'Answer required.'
            history_service.save_answer(
                db, session_id, qkey, answer,
                answer_json=meta or None,
                symptom_id=symptom_id,
            )
            _sync_ckp_answer(db, state, qkey, answer)
            n = 1
        diff = build_enriched_differential(db, session_id, ckp_session_id=state.get('ckp_session_id'))
        state['differential_snapshot'] = diff.get('diagnoses') or []
        save_state(db, session_id, state)
        return state, f'Section saved ({n}) — differential updated.'

    if action == 'finish_discriminating':
        state['stage'] = 'history_summary'
        save_state(db, session_id, state)
        return state, 'Ready for history summary.'

    if action == 'goto_stage':
        to = (form.get('stage') or '').strip()
        advance_stage(state, to=to)
        save_state(db, session_id, state)
        return state, f'Moved to {STAGE_LABELS.get(to, to)}.'

    if action == 'save_exam_note':
        note = (form.get('examination_note') or '').strip()
        if not note:
            return state, 'Examination note cannot be empty.'
        history_service.save_examination(db, session_id, note)
        return state, 'Examination note saved.'

    if action in ('save_exam_checklist', 'generate_exam_note'):
        findings: dict[str, dict] = {}
        normal_systems: list[str] = []
        if hasattr(form, 'getlist'):
            normal_systems = [
                str(v).strip() for v in form.getlist('exam_normal') if str(v).strip()
            ]
        else:
            raw = form.get('exam_normal')
            if isinstance(raw, list):
                normal_systems = [str(v).strip() for v in raw if str(v).strip()]
            elif raw:
                normal_systems = [str(raw).strip()]

        # form keys: exam__{system}__{item} = present|absent
        for key in form.keys() if hasattr(form, 'keys') else []:
            if not str(key).startswith('exam__'):
                continue
            parts = str(key).split('__', 2)
            if len(parts) != 3:
                continue
            _, system, item = parts
            if system in normal_systems:
                # Normal system: ignore individual ticks — one clean line only
                continue
            val = (form.get(key) or '').strip()
            if val not in ('present', 'absent'):
                continue
            findings.setdefault(system, {})[item] = val

        other = (form.get('exam_other') or '').strip()
        # Do not treat a previous serialized exam note as free-text "other"
        if other.lower().startswith(('general:', 'abdomen:', 'general —', 'abdomen —')) and \
                ('normal examination' in other.lower() or 'present:' in other.lower() or 'absent:' in other.lower()):
            other = ''

        state['exam_findings'] = findings
        state['exam_normal'] = normal_systems
        state['exam_other'] = other
        titles = {
            s['key']: s['title']
            for s in build_exam_checklist(symptom_service.list_session_symptoms(db, session_id))
        }
        text = format_exam_text(
            findings, other,
            normal_systems=normal_systems,
            system_titles=titles,
        )
        history_service.save_examination(db, session_id, text)
        # Feed CKP signs when possible
        ckp_id = state.get('ckp_session_id')
        if ckp_id:
            try:
                from clinical_knowledge_platform.workflow.controller import EncounterController
                ctrl = EncounterController(db, int(ckp_id))
                for system in normal_systems:
                    ctrl.record_exam(f'exam.{system}.normal', 'present')
                for system, items in findings.items():
                    for item, pol in items.items():
                        code = f"exam.{system}.{item}".replace(' ', '_').lower()[:80]
                        ctrl.record_exam(code, 'present' if pol == 'present' else 'absent')
            except Exception:
                pass
        diff = build_enriched_differential(db, session_id, ckp_session_id=state.get('ckp_session_id'))
        state['differential_snapshot'] = diff.get('diagnoses') or []
        save_state(db, session_id, state)
        if action == 'generate_exam_note':
            n_sys = len(normal_systems) + len(findings)
            if not n_sys:
                return state, 'Nothing ticked yet — mark findings or Normal examination first.'
            return state, f'Examination note generated from {n_sys} system(s).'
        return state, 'Examination checklist saved — differential updated.'

    if action == 'save_ix_checklist':
        checked = form.getlist('ix_checked') if hasattr(form, 'getlist') else []
        state['ix_checked'] = list(checked)
        # Create orders for newly checked suggested items
        from gi_platform import order_service
        sess = history_service.get_session(db, session_id)
        existing = {
            (r['item_name'] or '').lower()
            for r in db.execute(
                'SELECT item_name FROM gi_investigation_order WHERE session_id = ?',
                (session_id,),
            ).fetchall()
        }
        created = 0
        for name in checked:
            name = (name or '').strip()
            if not name or name.lower() in existing:
                continue
            approval = order_service.initial_approval_status('lab')
            db.execute(
                """
                INSERT INTO gi_investigation_order
                (session_id, ward_patient_id, order_type, item_code, item_name, custom_note,
                 created_by, approval_status)
                VALUES (?, ?, 'lab', 'checklist', ?, NULL, ?, ?)
                """,
                (session_id, sess['ward_patient_id'] if sess else None, name,
                 None, approval),
            )
            created += 1
            existing.add(name.lower())
        db.commit()
        save_state(db, session_id, state)
        return state, f'Investigation checklist saved ({created} new order(s)).'

    if action == 'advance':
        advance_stage(state)
        save_state(db, session_id, state)
        return state, f'Advanced to {STAGE_LABELS.get(state["stage"], state["stage"])}.'

    return state, ''


def build_workflow_view(db, session_id: int) -> dict[str, Any]:
    """Assemble template context for the staged clinical workflow."""
    from gi_platform import history_service, symptom_service
    from gi_platform.catalogue_runtime import list_complaints
    from gi_platform.unified_encounter.characterization import build_characterization_queue
    from gi_platform.unified_encounter.differential import build_enriched_differential
    from gi_platform.unified_encounter.discrimination import plan_discriminating_questions
    from gi_platform.unified_encounter.exam_ix import build_exam_checklist, build_investigation_checklist

    ensure_schema(db)
    state = get_state(db, session_id)
    symptoms = symptom_service.list_session_symptoms(db, session_id)
    answered = _answered_codes(db, session_id)
    stage = state.get('stage') or 'mode_select'
    mode = state.get('mode')

    # If legacy session already has symptoms but no mode, treat as diagnostic mid-flow
    if not mode and symptoms:
        state['mode'] = 'diagnostic'
        state['started'] = True
        if stage == 'mode_select':
            state['stage'] = 'characterization'
            stage = 'characterization'
        save_state(db, session_id, state)
        mode = 'diagnostic'

    char_queue = None
    disc_questions = []
    differential = {'diagnoses': [], 'red_flags': [], 'investigations': []}

    if stage in (
        'characterization', 'initial_reasoning', 'discriminating',
        'history_summary', 'examination', 'investigations', 'plan',
    ) or symptoms:
        differential = build_enriched_differential(
            db, session_id, ckp_session_id=state.get('ckp_session_id'),
        )
        if differential.get('diagnoses'):
            state['differential_snapshot'] = differential['diagnoses']

    if stage == 'characterization':
        char_queue = build_characterization_queue(
            db, symptoms,
            answered_codes=answered,
            current_index=int(state.get('characterization_index') or 0),
            disease_codes=state.get('known_disease_codes') or [],
        )
        # Auto-advance if empty questions mid-queue
        guard = 0
        while char_queue and char_queue.get('advance') and not char_queue.get('complete') and guard < 10:
            state['characterization_index'] = int(state.get('characterization_index') or 0) + 1
            char_queue = build_characterization_queue(
                db, symptoms,
                answered_codes=answered,
                current_index=int(state['characterization_index']),
                disease_codes=state.get('known_disease_codes') or [],
            )
            guard += 1
        if char_queue and char_queue.get('complete') and not char_queue.get('questions'):
            state['stage'] = 'initial_reasoning'
            stage = 'initial_reasoning'
            save_state(db, session_id, state)

    if stage == 'discriminating':
        disc_questions = plan_discriminating_questions(
            db,
            session_id=session_id,
            symptoms=symptoms,
            answered_codes=answered,
            ckp_session_id=state.get('ckp_session_id'),
            differential=differential.get('diagnoses') or [],
            limit=8,
        )

    exam_systems = build_exam_checklist(symptoms) if stage in ('examination', 'investigations', 'plan', 'history_summary') or True else []
    ix_pack = build_investigation_checklist(db, session_id, differential=differential)

    flow = _flow_for(mode)
    stage_index = flow.index(stage) if stage in flow else 0

    return {
        'ue_state': state,
        'ue_mode': mode,
        'ue_stage': stage,
        'ue_stage_label': STAGE_LABELS.get(stage, stage),
        'ue_flow': flow,
        'ue_stage_labels': STAGE_LABELS,
        'ue_stage_index': stage_index,
        'ue_complaints': list_complaints(db),
        'ue_known_diseases': KNOWN_DISEASES,
        'ue_current_problems': CURRENT_PROBLEMS,
        'ue_char_queue': char_queue,
        'ue_disc_questions': disc_questions,
        'ue_differential': differential,
        'ue_exam_systems': exam_systems,
        'ue_ix': ix_pack,
        'ue_answers': history_service.list_answers(db, session_id),
        'CURRENT_PROBLEMS': CURRENT_PROBLEMS,
        'KNOWN_DISEASES': KNOWN_DISEASES,
        'STAGE_LABELS': STAGE_LABELS,
    }
