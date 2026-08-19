"""Smoke test for clinical_history_ai port."""

from __future__ import annotations

from app import app, get_db


def main() -> None:
    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['role'] = 'admin'

    with app.app_context():
        db = get_db()
        db.execute(
            "INSERT OR IGNORE INTO ward_patient (id, patient_name, mrn) VALUES (9999, 'GH Test', 'GH999')"
        )
        existing = db.execute(
            'SELECT id FROM gi_history_session WHERE ward_patient_id = 9999 ORDER BY id DESC LIMIT 1',
        ).fetchone()
        if existing:
            hist_id = existing['id']
            db.execute(
                """
                UPDATE gi_history_session SET complaint_code = ?, chief_complaint = ?
                WHERE id = ?
                """,
                ('hist.upper_gi_bleeding', 'Upper GI bleeding', hist_id),
            )
        else:
            cur = db.execute(
                """
                INSERT INTO gi_history_session (ward_patient_id, complaint_code, chief_complaint)
                VALUES (9999, 'hist.upper_gi_bleeding', 'Upper GI bleeding')
                """,
            )
            hist_id = cur.lastrowid
        db.commit()

        start = client.post(f'/clinical-history-ai/api/history/{hist_id}/start')
        assert start.status_code == 201, start.get_data(as_text=True)
        session_id = start.get_json()['session']['id']

        ans = client.post(
            f'/clinical-history-ai/api/sessions/{session_id}/answers',
            json={'answers': {'gh.q.onset': 'Days', 'gh.q.severity': 'Moderate'}},
        )
        assert ans.status_code == 200, ans.get_data(as_text=True)

        gen = client.post(f'/clinical-history-ai/api/sessions/{session_id}/generate')
        assert gen.status_code == 201, gen.get_data(as_text=True)
        draft = gen.get_json()['draft']
        assert draft['sections'].get('chief_complaint')

        approve = client.post(f'/clinical-history-ai/api/drafts/{draft["id"]}/approve')
        assert approve.status_code == 200, approve.get_data(as_text=True)

        ui = client.get('/clinical-history-ai/patient/9999')
        assert ui.status_code == 200

    print('clinical_history_ai smoke test: OK')


if __name__ == '__main__':
    main()
