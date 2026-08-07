"""Smoke test for patient_journey AI port."""

from __future__ import annotations

from app import app, get_db
from gi_platform import history_service


def main() -> None:
    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['role'] = 'admin'

    with app.app_context():
        db = get_db()
        db.execute(
            "INSERT OR IGNORE INTO ward_patient (id, patient_name, mrn) VALUES (9993, 'PJ Test', 'PJ993')"
        )
        cur = db.execute(
            """
            INSERT INTO gi_history_session (ward_patient_id, complaint_code, chief_complaint)
            VALUES (9993, 'hist.upper_gi_bleeding', 'Upper GI bleeding')
            """,
        )
        hist_id = cur.lastrowid
        history_service.save_answer(db, hist_id, 'gh.q.onset', 'Days')
        history_service.save_answer(db, hist_id, 'gh.q.vomiting_blood', 'yes')
        db.commit()

        assess = client.post(f'/clinical-assessment/history/{hist_id}/generate')
        assert assess.status_code == 201, assess.get_data(as_text=True)
        suggestion_id = assess.get_json()['suggestions'][0]['id']
        confirm = client.post(f'/clinical-assessment/suggestions/{suggestion_id}/confirm')
        assert confirm.status_code == 200, confirm.get_data(as_text=True)

        mgmt = client.post(f'/management-plan/history/{hist_id}/generate')
        assert mgmt.status_code == 201, mgmt.get_data(as_text=True)

        status = client.get('/patient-journey-ai/status')
        assert status.status_code == 200

        view = client.get(f'/patient-journey-ai/patient/9993?history_session_id={hist_id}')
        assert view.status_code == 200
        assert view.get_json()['follow_up_suggestions']

        follow = client.post(f'/patient-journey-ai/history/{hist_id}/follow-up')
        assert follow.status_code == 201, follow.get_data(as_text=True)

        summary = client.post(f'/patient-journey-ai/history/{hist_id}/summary/generate')
        assert summary.status_code == 201, summary.get_data(as_text=True)
        draft_id = summary.get_json()['summary']['id']

        approve = client.post(f'/patient-journey-ai/summaries/{draft_id}/approve')
        assert approve.status_code == 200
        assert approve.get_json()['summary']['status'] == 'approved'

    print('patient_journey_ai smoke test: OK')


if __name__ == '__main__':
    main()
