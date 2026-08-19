"""Smoke tests for unified ward clinical encounter (decision-based history)."""

from __future__ import annotations

from app import app, get_db
from gi_platform import history_service, symptom_service, unified_encounter as ue
from gi_platform.complaints_extra_seed import seed_extra_complaints_if_missing, seed_symptom_training_questions
from gi_platform.narrative_engine import generate_history_note
from gi_platform.unified_encounter.characterization import (
    STRUCTURED_TYPES,
    assert_no_free_text_batch,
    build_characterization_queue,
    odpara_questions,
)
from gi_platform.unified_encounter.differential import build_enriched_differential
from gi_platform.unified_encounter.discrimination import plan_discriminating_questions
from gi_platform.unified_encounter.service import _extract_structured_answer


class _Form(dict):
    def getlist(self, key):
        v = self.get(key)
        if v is None:
            return []
        if isinstance(v, list):
            return v
        return [v]


def _setup_patient(db, pid: int = 9911, name: str = 'UE Smoke', mrn: str = 'UE9911') -> int:
    db.execute(
        "INSERT OR IGNORE INTO ward_patient (id, patient_name, mrn) VALUES (?, ?, ?)",
        (pid, name, mrn),
    )
    db.commit()
    return pid


def _answer_required_odpara(db, sid: int, sym: dict) -> None:
    for q in odpara_questions(
        sym['complaint_code'],
        symptom_name=sym.get('symptom_name') or '',
        symptom_id=sym.get('id'),
    ):
        if q.get('optional'):
            continue
        at = q['answer_type']
        if at == 'multi_choice':
            val = '; '.join((q.get('choices') or ['None'])[:2])
        elif at in ('numeric', 'date'):
            continue
        else:
            val = (q.get('choices') or ['Yes'])[0]
        history_service.save_answer(db, sid, q['code'], val, symptom_id=sym.get('id'))


def test_no_freetext_in_characterization_batch() -> None:
    with app.app_context():
        db = get_db()
        seed_extra_complaints_if_missing(db)
        pid = _setup_patient(db, 9921, 'UE FT', 'UE9921')
        sid = history_service.create_session(db, ward_patient_id=pid, created_by=1)
        symptom_service.set_session_symptoms(db, sid, symptoms=[
            {'complaint_code': 'hist.abdominal_pain', 'onset_text': 'Days', 'is_primary': True},
            {'complaint_code': 'hist.vomiting', 'onset_text': 'Days', 'is_primary': False},
        ])
        symptoms = symptom_service.list_session_symptoms(db, sid)
        queue = build_characterization_queue(db, symptoms, answered_codes=set(), current_index=0)
        assert queue.get('questions'), 'Expected characterization questions'
        for q in queue['questions']:
            at = (q.get('answer_type') or '').lower()
            assert at != 'text' or q.get('is_comment') or q.get('allow_other'), q
            assert at in STRUCTURED_TYPES or q.get('is_comment'), q
            if at in ('choice', 'multi_choice', 'boolean'):
                assert q.get('choices'), f'Missing choices: {q["code"]}'
        # Full ODPARA bank for pain must be structured
        odpara = odpara_questions('hist.abdominal_pain', symptom_name='Abdominal pain')
        clean = assert_no_free_text_batch(odpara)
        assert all(
            (q.get('answer_type') or '') != 'text' or q.get('is_comment')
            for q in clean
        )
        assert any(q.get('answer_type') == 'multi_choice' for q in odpara), 'Expected multi-select associated/aggravating'
        assert any(q.get('answer_type') == 'numeric' for q in odpara), 'Expected numeric severity/weight'
        assert any(q.get('answer_type') == 'date' for q in odpara), 'Expected optional onset date'
        assert any(q.get('allow_other') for q in odpara), 'Expected Other-specify path'
    print('characterization: no free-text batch OK')


def test_multi_complaint_sequential() -> None:
    with app.app_context():
        db = get_db()
        seed_extra_complaints_if_missing(db)
        pid = _setup_patient(db, 9922, 'UE Multi', 'UE9922')
        sid = history_service.create_session(db, ward_patient_id=pid, created_by=1)
        ue.ensure_schema(db)
        state, _ = ue.handle_action(db, sid, 'set_mode', _Form(encounter_mode='diagnostic'))
        state, msg = ue.handle_action(db, sid, 'set_complaints', _Form({
            'complaint_codes': ['hist.abdominal_pain', 'hist.vomiting'],
            'primary_complaint': 'hist.abdominal_pain',
            'onset_hist.abdominal_pain': 'Days',
            'onset_hist.vomiting': 'Days',
        }))
        assert state['stage'] == 'characterization', msg
        symptoms = symptom_service.list_session_symptoms(db, sid)
        assert len(symptoms) == 2

        # Fully characterize complaint 0
        _answer_required_odpara(db, sid, symptoms[0])
        answered = set(history_service.get_answers_map(db, sid).keys())
        queue = build_characterization_queue(
            db, symptoms, answered_codes=answered, current_index=0,
        )
        # May still have complaint-specific; finish those if present
        guard = 0
        while queue.get('questions') and guard < 40:
            for q in list(queue['questions']):
                if q.get('optional'):
                    continue
                val = (q.get('choices') or ['Yes'])[0]
                if q.get('answer_type') == 'multi_choice':
                    val = '; '.join((q.get('choices') or ['None'])[:1])
                history_service.save_answer(db, sid, q['code'], val, symptom_id=q.get('symptom_id'))
            answered = set(history_service.get_answers_map(db, sid).keys())
            queue = build_characterization_queue(
                db, symptoms, answered_codes=answered, current_index=0,
            )
            guard += 1
            if queue.get('advance'):
                break

        assert queue.get('advance') or queue.get('subphase') == 'done' or not queue.get('questions')
        # Advance to second complaint
        idx = 1 if queue.get('advance') else 0
        if queue.get('advance'):
            queue2 = build_characterization_queue(
                db, symptoms, answered_codes=answered, current_index=1,
            )
            assert queue2.get('current_symptom')
            assert queue2['current_symptom']['complaint_code'] == symptoms[1]['complaint_code']
            assert queue2.get('questions'), 'Second complaint must get its own ODPARA batch'
            for q in queue2['questions']:
                assert (q.get('answer_type') or '') != 'text' or q.get('is_comment')
    print('multi-complaint sequential: OK')


def test_disc_why_line_rule_in_out() -> None:
    from gi_platform.unified_encounter.discrimination import build_why_line, annotate_questions_with_why

    diff = [
        {'name': 'Colorectal cancer', 'confidence': 'high'},
        {'name': 'Inflammatory bowel disease', 'confidence': 'moderate'},
        {'name': 'Haemorrhoids', 'confidence': 'moderate'},
        {'name': 'Anal fissure', 'confidence': 'moderate'},
        {'name': 'Diverticular bleed', 'confidence': 'moderate'},
    ]
    fever = build_why_line({'prompt': 'Fever?', 'code': 'q.fever', 'is_exclusion': True}, diff)
    assert fever['why_line'], fever
    assert any('ibd' in n.lower() or 'inflammatory' in n.lower() for n in fever['rule_in']), fever
    assert any('haemorrhoid' in n.lower() or 'fissure' in n.lower() for n in fever['rule_out']), fever

    ibd_fh = build_why_line({'prompt': 'Family history of IBD?', 'code': 'q.fh_ibd'}, diff)
    assert any('inflammatory' in n.lower() or 'ibd' in n.lower() for n in ibd_fh['rule_in']), ibd_fh

    wt = build_why_line({'prompt': 'Weight loss?', 'code': 'q.wt', 'is_exclusion': True}, diff)
    assert any('cancer' in n.lower() for n in wt['rule_in']), wt

    qs = annotate_questions_with_why([
        {'prompt': 'Nocturnal diarrhea?', 'code': 'q.noct', 'is_exclusion': True},
    ], diff)
    assert qs[0].get('why_line')
    assert 'Rule in' in qs[0]['why_line'] or qs[0].get('rule_in')
    print('disc why-line rule-in/out: OK')


def test_other_specify_path() -> None:
    form = _Form({
        'answer_type': 'choice',
        'answer_text': 'Other',
        'other_specify': 'Left lower quadrant radiating to thigh',
    })
    answer, meta = _extract_structured_answer(form)
    assert answer.startswith('Other:'), answer
    assert 'thigh' in answer
    assert meta.get('other_specify')

    form2 = _Form({
        'answer_type': 'multi_choice',
        'answer_text': ['Food', 'Other'],
        'other_specify': 'spicy meals',
    })
    answer2, meta2 = _extract_structured_answer(form2)
    assert 'Food' in answer2
    assert 'Other: spicy meals' in answer2
    assert meta2.get('selections')
    print('other-specify path: OK')


def test_section_batch_save() -> None:
    """One Save persists an entire characterization / discriminating section."""
    from gi_platform.unified_encounter.service import _batch_question_codes, _extract_answer_for_code

    with app.app_context():
        db = get_db()
        seed_extra_complaints_if_missing(db)
        pid = _setup_patient(db, 9933, 'UE Section', 'UE9933')
        sid = history_service.create_session(db, ward_patient_id=pid, created_by=1)
        ue.ensure_schema(db)
        state, _ = ue.handle_action(db, sid, 'set_mode', _Form(encounter_mode='diagnostic'))
        state, msg = ue.handle_action(db, sid, 'set_complaints', _Form({
            'complaint_codes': ['hist.vomiting'],
            'primary_complaint': 'hist.vomiting',
            'onset_hist.vomiting': 'Days',
        }))
        assert state['stage'] == 'characterization', msg
        symptoms = symptom_service.list_session_symptoms(db, sid)
        queue = build_characterization_queue(
            db, symptoms, answered_codes=set(), current_index=0,
        )
        qs = queue.get('questions') or []
        assert len(qs) >= 2, 'Section should expose multiple ODPARA questions at once'

        payload: dict = {}
        for q in qs:
            code = q['code']
            payload[f'atype__{code}'] = q.get('answer_type') or 'choice'
            if q.get('optional'):
                payload[f'optional__{code}'] = '1'
            if q.get('symptom_id'):
                payload[f'sid__{code}'] = str(q['symptom_id'])
            if q.get('optional') and q.get('answer_type') in ('numeric', 'date'):
                continue  # leave blank → Not recorded
            choices = q.get('choices') or ['Yes']
            if q.get('answer_type') == 'multi_choice':
                payload[f'ans__{code}'] = [choices[0]]
            else:
                payload[f'ans__{code}'] = choices[0]

        assert len(_batch_question_codes(_Form(payload))) >= 2
        state, msg = ue.handle_action(db, sid, 'save_char_section', _Form(payload))
        assert 'section saved' in msg.lower() or 'saved' in msg.lower(), msg
        answered = set(history_service.get_answers_map(db, sid).keys())
        for q in qs:
            if q.get('optional') and q.get('answer_type') in ('numeric', 'date'):
                assert q['code'] in answered  # Not recorded
            elif not q.get('optional'):
                assert q['code'] in answered, q['code']

        # Batch field extraction with Other
        batch = _Form({
            'atype__q.demo': 'choice',
            'ans__q.demo': 'Other',
            'other__q.demo': 'epigastric band-like',
        })
        ans, meta, opt = _extract_answer_for_code(batch, 'q.demo')
        assert ans.startswith('Other:'), ans
        assert meta.get('other_specify')
        assert not opt
    print('section batch save: OK')


def test_diagnostic_mode() -> None:
    with app.app_context():
        db = get_db()
        seed_extra_complaints_if_missing(db)
        seed_symptom_training_questions(db)
        pid = _setup_patient(db, 9911)
        sid = history_service.create_session(db, ward_patient_id=pid, created_by=1)
        ue.ensure_schema(db)

        state, msg = ue.handle_action(db, sid, 'set_mode', _Form(encounter_mode='diagnostic'))
        assert state['mode'] == 'diagnostic', msg
        assert state['stage'] == 'complaints'

        state, msg = ue.handle_action(db, sid, 'set_complaints', _Form({
            'complaint_codes': ['hist.abdominal_pain', 'hist.vomiting'],
            'primary_complaint': 'hist.abdominal_pain',
            'onset_hist.abdominal_pain': 'Days',
            'onset_hist.vomiting': 'Days',
        }))
        assert state['stage'] == 'characterization', msg
        symptoms = symptom_service.list_session_symptoms(db, sid)
        assert len(symptoms) == 2

        odpara = odpara_questions('hist.abdominal_pain', symptom_name='Abdominal pain', symptom_id=symptoms[0]['id'])
        assert odpara and all(
            q.get('choices') or q.get('answer_type') in ('numeric', 'date', 'text')
            for q in odpara
        )
        for q in odpara:
            if q.get('optional'):
                continue
            if q['answer_type'] == 'multi_choice':
                history_service.save_answer(
                    db, sid, q['code'], '; '.join(q['choices'][:1]),
                    symptom_id=symptoms[0]['id'],
                )
            else:
                history_service.save_answer(
                    db, sid, q['code'], (q.get('choices') or ['Yes'])[0],
                    symptom_id=symptoms[0]['id'],
                )

        answered = set(history_service.get_answers_map(db, sid).keys())
        queue = build_characterization_queue(
            db, symptoms, answered_codes=answered, current_index=0,
        )
        assert queue is not None

        state, msg = ue.handle_action(db, sid, 'finish_characterization', _Form())
        assert state['stage'] == 'initial_reasoning', msg

        diff = build_enriched_differential(db, sid, ckp_session_id=state.get('ckp_session_id'))
        assert diff.get('diagnoses'), 'Differential must populate after Stage 3'
        assert any(d.get('name') for d in diff['diagnoses'])

        state, msg = ue.handle_action(db, sid, 'confirm_initial_reasoning', _Form())
        assert state['stage'] == 'discriminating', msg

        disc = plan_discriminating_questions(
            db, session_id=sid, symptoms=symptoms,
            answered_codes=set(history_service.get_answers_map(db, sid).keys()),
            ckp_session_id=state.get('ckp_session_id'),
            differential=diff['diagnoses'],
            limit=4,
        )
        for q in disc:
            assert (q.get('answer_type') or '') != 'text', q
            assert q.get('answer_type') in (
                'boolean', 'choice', 'multi_choice', 'numeric', 'date', 'scale', 'duration',
            )
            if q['answer_type'] in ('boolean', 'choice', 'multi_choice'):
                assert q.get('choices'), q

        # Save one discriminating answer via structured handler
        if disc:
            q0 = disc[0]
            state, msg = ue.handle_action(db, sid, 'save_disc_answer', _Form({
                'question_key': q0['code'],
                'answer_type': q0['answer_type'],
                'answer_text': (q0.get('choices') or ['Yes'])[0],
                'symptom_id': str(q0.get('symptom_id') or ''),
            }))
            assert 'differential' in msg.lower() or 'saved' in msg.lower(), msg

        state, msg = ue.handle_action(db, sid, 'finish_discriminating', _Form())
        assert state['stage'] == 'history_summary', msg

        sections = generate_history_note(db, sid)
        assert sections.get('hpi') is not None

        state, msg = ue.handle_action(db, sid, 'save_exam_checklist', _Form({
            'exam__general__Fever / hypothermia': 'present',
            'exam__abdomen__Tenderness — localized': 'present',
            'exam_other': 'Soft elsewhere',
            'exam_normal': ['cardiorespiratory', 'neuro'],
        }))
        sess = history_service.get_session(db, sid)
        exam = (sess['examination_text'] if 'examination_text' in sess.keys() else '') or ''
        assert 'Heart sounds were normal' in exam, exam
        assert 'alert and oriented' in exam, exam
        assert 'Present:' not in exam and 'Absent:' not in exam, exam
        assert 'An abnormal temperature was documented' in exam, exam
        assert 'Localized abdominal tenderness was present' in exam, exam
        # Unticked abdomen items must not appear
        assert 'Guarding' not in exam, exam
        assert 'Organomegaly' not in exam, exam
        # Blocks are separated and bodies indented for readability
        assert '\n\n' in exam, exam
        assert any(line.startswith('  ') for line in exam.splitlines()), exam

        # No sign is offered twice across systems
        from gi_platform.unified_encounter.exam_ix import build_exam_checklist, _concept_key
        groups = build_exam_checklist(symptom_service.list_session_symptoms(db, sid))
        concepts = [_concept_key(i) for g in groups for i in g['items']]
        assert len(concepts) == len(set(concepts)), 'Duplicate exam concepts across systems'

        state, msg = ue.handle_action(db, sid, 'generate_exam_note', _Form({
            'exam__abdomen__Soft, non-tender': 'present',
            'exam_normal': ['neuro'],
        }))
        assert 'generated' in msg.lower(), msg
        sess = history_service.get_session(db, sid)
        exam2 = (sess['examination_text'] if 'examination_text' in sess.keys() else '') or ''
        assert 'The abdomen was soft and non-tender' in exam2, exam2
        assert 'alert and oriented' in exam2, exam2

        edited = 'General examination: The patient was comfortable and haemodynamically stable.'
        state, msg = ue.handle_action(db, sid, 'save_exam_note', _Form({
            'examination_note': edited,
        }))
        assert 'saved' in msg.lower(), msg
        sess = history_service.get_session(db, sid)
        assert sess['examination_text'] == edited

        view = ue.build_workflow_view(db, sid)
        assert view['ue_mode'] == 'diagnostic'
        assert view['ue_differential']['diagnoses']

    print('unified_encounter diagnostic mode: OK')


def test_known_disease_mode() -> None:
    with app.app_context():
        db = get_db()
        seed_extra_complaints_if_missing(db)
        pid = _setup_patient(db, 9912, 'UE Known', 'UE9912')
        sid = history_service.create_session(db, ward_patient_id=pid, created_by=1)
        ue.ensure_schema(db)

        state, msg = ue.handle_action(db, sid, 'set_mode', _Form(encounter_mode='known_disease'))
        assert state['mode'] == 'known_disease'
        assert state['stage'] == 'known_diseases'

        state, msg = ue.handle_action(db, sid, 'set_known_diseases', _Form({
            'known_disease_codes': ['dx.cirrhosis', 'dx.pud'],
        }))
        assert state['stage'] == 'current_problem', msg

        state, msg = ue.handle_action(db, sid, 'set_current_problems', _Form({
            'current_problem_codes': ['cp.hematemesis', 'cp.ascites'],
        }))
        assert state['stage'] == 'characterization', msg
        symptoms = symptom_service.list_session_symptoms(db, sid)
        assert len(symptoms) >= 1

        sym = symptoms[0]
        _answer_required_odpara(db, sid, sym)

        state, msg = ue.handle_action(db, sid, 'finish_characterization', _Form())
        assert state['stage'] == 'initial_reasoning'
        diff = build_enriched_differential(db, sid)
        assert diff.get('diagnoses'), 'Known-disease mode must also populate differential'

        view = ue.build_workflow_view(db, sid)
        assert view['ue_mode'] == 'known_disease'
        assert 'dx.cirrhosis' in (view['ue_state'].get('known_disease_codes') or [])

    print('unified_encounter known-disease mode: OK')


def test_http_workflow_page() -> None:
    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['role'] = 'admin'
        with app.app_context():
            db = get_db()
            pid = _setup_patient(db, 9915, 'UE HTTP Fresh', 'UE9915')
            sid = history_service.create_session(db, ward_patient_id=pid, created_by=1)
            ue.ensure_schema(db)
            ue.save_state(db, sid, ue.get_state(db, sid))
        r = client.get(f'/ward/patient/{pid}/clinical')
        assert r.status_code == 200, r.status_code
        body = r.get_data(as_text=True)
        assert 'New Diagnostic Encounter' in body
        assert 'Known Disease Follow-up' in body
        assert 'Structured interview (Clinical Intelligence)' not in body

        import re
        m = re.search(r'name="csrf-token" content="([^"]+)"', body)
        assert m, 'csrf token missing from page'
        token = m.group(1)

        r2 = client.post(
            f'/ward/patient/{pid}/clinical',
            data={
                'action': 'ue_set_mode',
                'encounter_mode': 'diagnostic',
                'csrf_token': token,
            },
            follow_redirects=True,
        )
        assert r2.status_code == 200
        body2 = r2.get_data(as_text=True)
        assert 'Security check failed' not in body2
        assert (
            'Start characterization' in body2
            or 'ue_set_complaints' in body2
            or 'Select one or more chief complaints' in body2
            or 'Stage 1' in body2
        ), body2[:500]
        # Catalogue dropdown must stay visible, plus exam note button
        assert 'Order from full catalogue' in body2
        assert 'ix-item-code' in body2
        assert 'Upper GI endoscopy (EGD)' in body2
        assert 'ue_generate_exam_note' in body2

    print('unified_encounter HTTP page: OK')


def main() -> None:
    test_no_freetext_in_characterization_batch()
    test_other_specify_path()
    test_disc_why_line_rule_in_out()
    test_section_batch_save()
    test_multi_complaint_sequential()
    test_diagnostic_mode()
    test_known_disease_mode()
    test_http_workflow_page()
    print('unified_encounter smoke tests: ALL OK')


if __name__ == '__main__':
    main()
