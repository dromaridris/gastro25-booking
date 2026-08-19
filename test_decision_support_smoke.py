"""Smoke test for decision_support orchestrator port."""

from __future__ import annotations

from app import app


def main() -> None:
    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['role'] = 'admin'

        status = client.get('/clinical-cds/status?complaint_code=hist.upper_gi_bleed')
        assert status.status_code == 200, status.get_data(as_text=True)
        assert status.get_json()['status'] == 'ok'

        assess = client.post('/clinical-cds/assess', json={
            'complaint_code': 'hist.upper_gi_bleed',
            'answers': {'hist.ugib.melena': 'yes'},
        })
        assert assess.status_code == 200, assess.get_data(as_text=True)
        data = assess.get_json()
        assert 'differentials' in data
        assert 'investigations' in data

        advance = client.post('/clinical-cds/interview/advance', json={
            'complaint_code': 'hist.upper_gi_bleed',
            'answers': {},
        })
        assert advance.status_code == 200, advance.get_data(as_text=True)
        adv = advance.get_json()
        assert 'interview_complete' in adv

    print('decision_support smoke test: OK')


if __name__ == '__main__':
    main()
