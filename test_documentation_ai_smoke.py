"""Smoke test for documentation_ai port."""

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
            "INSERT OR IGNORE INTO ward_patient (id, patient_name, mrn) VALUES (9994, 'DA Test', 'DA994')"
        )
        cur = db.execute(
            """
            INSERT INTO gi_history_session (ward_patient_id, complaint_code, chief_complaint)
            VALUES (9994, 'hist.upper_gi_bleeding', 'Upper GI bleeding')
            """,
        )
        hist_id = cur.lastrowid
        history_service.save_answer(db, hist_id, 'gh.q.onset', 'Days')
        history_service.save_answer(db, hist_id, 'gh.q.vomiting_blood', 'yes')
        history_service.save_narrative(
            db, hist_id, 'Patient presents with upper GI bleeding over 2 days.',
            {'hpi': 'Melena and coffee-ground vomitus for 2 days.'},
        )
        db.commit()

        assess = client.post(f'/clinical-assessment/history/{hist_id}/generate')
        assert assess.status_code == 201, assess.get_data(as_text=True)
        suggestion_id = assess.get_json()['suggestions'][0]['id']
        confirm = client.post(f'/clinical-assessment/suggestions/{suggestion_id}/confirm')
        assert confirm.status_code == 200, confirm.get_data(as_text=True)

        mgmt = client.post(f'/management-plan/history/{hist_id}/generate')
        assert mgmt.status_code == 201, mgmt.get_data(as_text=True)

        status = client.get('/documentation-ai/status')
        assert status.status_code == 200, status.get_data(as_text=True)

        templates = client.get('/documentation-ai/templates')
        assert templates.status_code == 200
        assert len(templates.get_json()['templates']) >= 1

        gen = client.post(
            f'/documentation-ai/history/{hist_id}/generate',
            json={'template_key': 'doc.admission.gi'},
        )
        assert gen.status_code == 201, gen.get_data(as_text=True)
        body = gen.get_json()
        assert body['document'], 'Expected document draft'
        assert len(body['sections']) >= 5

        doc_id = body['document']['id']
        approve = client.post(f'/documentation-ai/documents/{doc_id}/approve')
        assert approve.status_code == 200, approve.get_data(as_text=True)

        sign = client.post(f'/documentation-ai/documents/{doc_id}/sign')
        assert sign.status_code == 200, sign.get_data(as_text=True)
        assert sign.get_json()['signed_document']['template_key'] == 'doc.admission.gi'

    print('documentation_ai smoke test: OK')


if __name__ == '__main__':
    main()
