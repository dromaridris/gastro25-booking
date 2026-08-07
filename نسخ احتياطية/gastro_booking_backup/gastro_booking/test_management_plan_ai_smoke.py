"""Smoke test for management_plan_ai port."""

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
            "INSERT OR IGNORE INTO ward_patient (id, patient_name, mrn) VALUES (9995, 'MP Test', 'MP995')"
        )
        cur = db.execute(
            """
            INSERT INTO gi_history_session (ward_patient_id, complaint_code, chief_complaint)
            VALUES (9995, 'hist.upper_gi_bleeding', 'Upper GI bleeding')
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

        status = client.get('/management-plan/status')
        assert status.status_code == 200, status.get_data(as_text=True)

        gen = client.post(f'/management-plan/history/{hist_id}/generate')
        assert gen.status_code == 201, gen.get_data(as_text=True)
        body = gen.get_json()
        assert body['plan'], 'Expected management plan'
        assert body['suggestions'], 'Expected at least one management suggestion'

        mgmt_suggestion_id = body['suggestions'][0]['id']
        accept = client.post(f'/management-plan/suggestions/{mgmt_suggestion_id}/accept')
        assert accept.status_code == 200, accept.get_data(as_text=True)

        approve = client.post(f"/management-plan/plans/{body['plan']['id']}/approve")
        assert approve.status_code == 200, approve.get_data(as_text=True)
        assert approve.get_json()['plan']['status'] == 'approved'

        view = client.get(f'/management-plan/history/{hist_id}')
        assert view.status_code == 200
        assert view.get_json()['plan']['status'] == 'approved'

    print('management_plan_ai smoke test: OK')


if __name__ == '__main__':
    main()
