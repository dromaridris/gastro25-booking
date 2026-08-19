"""Smoke test: multi-symptom history + AI training + professional narrative."""

from __future__ import annotations

from app import app, get_db
from gi_platform import history_service, symptom_service
from gi_platform.complaints_extra_seed import seed_extra_complaints_if_missing, seed_symptom_training_questions
from gi_platform.narrative_engine import generate_history_note


def main() -> None:
    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['role'] = 'admin'

        with app.app_context():
            db = get_db()
            seed_extra_complaints_if_missing(db)
            seed_symptom_training_questions(db)
            db.execute(
                "INSERT OR IGNORE INTO ward_patient (id, patient_name, mrn) VALUES (9990, 'MS Test', 'MS990')"
            )
            sid = history_service.create_session(db, ward_patient_id=9990, created_by=1)

            symptom_service.set_session_symptoms(db, sid, symptoms=[
                {'complaint_code': 'hist.abdominal_distension', 'onset_text': 'Days', 'is_primary': True},
                {'complaint_code': 'hist.loose_stools', 'onset_text': 'Weeks', 'is_primary': False},
            ])
            symptoms = symptom_service.list_session_symptoms(db, sid)
            assert len(symptoms) == 2
            assert symptoms[0]['duration_category'] == 'acute'
            assert symptoms[1]['duration_category'] == 'subacute'

            history_service.save_answer(db, sid, 'gh.dist.onset', 'Days', symptom_id=symptoms[0]['id'])
            history_service.save_answer(db, sid, 'gh.dist.pain', 'yes', symptom_id=symptoms[0]['id'])
            history_service.save_answer(db, sid, 'gh.loose.onset', 'Weeks', symptom_id=symptoms[1]['id'])
            history_service.save_answer(db, sid, 'gh.loose.frequency', '4-6', symptom_id=symptoms[1]['id'])

            diff = symptom_service.compute_combined_differential(db, sid)
            assert 'diagnoses' in diff

            sections = generate_history_note(db, sid)
            assert sections.get('hpi'), 'Expected HPI text'
            assert 'distension' in sections['hpi'].lower() or 'Abdominal' in sections['hpi']

            status = client.get('/admin/history-ai-training')
            assert status.status_code == 200, status.get_data(as_text=True)
            assert b'History AI Training' in status.data

            gen = client.post(f'/clinical-history/session/{sid}/generate-note', follow_redirects=False)
            assert gen.status_code in (302, 200), gen.get_data(as_text=True)

    print('multi_symptom_history smoke test: OK')


if __name__ == '__main__':
    main()
