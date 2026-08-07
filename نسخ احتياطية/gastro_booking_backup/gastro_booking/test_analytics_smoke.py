"""Smoke test for analytics port."""

from __future__ import annotations

from app import app, get_db


def main() -> None:
    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['role'] = 'admin'

    status = client.get('/analytics/status')
    assert status.status_code == 200, status.get_data(as_text=True)

    metrics = client.get('/analytics/metrics')
    assert metrics.status_code == 200
    body = metrics.get_json()
    assert len(body['metrics']) >= 5

    run = client.get('/analytics/run/g25.clinical.assessment_runs')
    assert run.status_code == 200, run.get_data(as_text=True)
    assert 'value' in run.get_json()

    research = client.get('/analytics/run/g25.research.enrollments')
    assert research.status_code == 200, research.get_data(as_text=True)
    assert 'value' in research.get_json()

    bad = client.get('/analytics/run/unknown.metric')
    assert bad.status_code == 400

    print('analytics smoke test: OK')


if __name__ == '__main__':
    main()
