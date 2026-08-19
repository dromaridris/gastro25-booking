"""Smoke test for clinical_interpretation port."""

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
            "INSERT OR IGNORE INTO ward_patient (id, patient_name, mrn) VALUES (9997, 'CI Test', 'CI997')"
        )
        cur = db.execute(
            """
            INSERT INTO gi_history_session (ward_patient_id, complaint_code, chief_complaint)
            VALUES (9997, 'hist.upper_gi_bleeding', 'Upper GI bleeding')
            """,
        )
        hist_id = cur.lastrowid
        history_service.save_answer(db, hist_id, 'gh.q.onset', 'Days')
        history_service.save_answer(db, hist_id, 'gh.q.vomiting_blood', 'yes')
        db.execute(
            """
            INSERT INTO gi_lab_result (
                ward_patient_id, test_code, test_name, result_value, result_unit,
                reference_range, status
            ) VALUES (9997, 'lab.hb', 'Haemoglobin', '8.5', 'g/dL', '12.0-16.0', 'completed')
            """,
        )
        db.commit()

        assess = client.post(f'/clinical-assessment/history/{hist_id}/generate')
        assert assess.status_code == 201, assess.get_data(as_text=True)

        status = client.get('/clinical-interpretation/status')
        assert status.status_code == 200, status.get_data(as_text=True)

        gen = client.post(f'/clinical-interpretation/history/{hist_id}/generate')
        assert gen.status_code == 201, gen.get_data(as_text=True)
        body = gen.get_json()
        assert body['run'], 'Expected interpretation run'
        assert body['findings'], 'Expected at least one lab finding'

        finding_id = body['findings'][0]['id']
        accept = client.post(f'/clinical-interpretation/findings/{finding_id}/accept')
        assert accept.status_code == 200, accept.get_data(as_text=True)

        view = client.get(f'/clinical-interpretation/history/{hist_id}')
        assert view.status_code == 200
        assert len(view.get_json()['decisions']) >= 1

    print('clinical_interpretation smoke test: OK')


if __name__ == '__main__':
    main()
