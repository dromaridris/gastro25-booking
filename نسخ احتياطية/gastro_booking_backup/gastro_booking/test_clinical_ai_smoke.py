"""Smoke test for Clinical AI core port."""

from __future__ import annotations

import json

from app import app


def main() -> None:
    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['role'] = 'admin'

        status = client.get('/clinical-ai/status')
        assert status.status_code == 200, status.get_data(as_text=True)
        data = status.get_json()
        assert data['status'] == 'ok'
        assert 'supported_prompt_types' in data
        assert 'guideline_lookup' in data['supported_prompt_types']

        run = client.post(
            '/clinical-ai/sessions/run',
            json={
                'prompt_type': 'guideline_lookup',
                'user_question': 'Summarise upper GI bleed guidelines.',
                'provider_key': 'stub',
            },
        )
        assert run.status_code == 200, run.get_data(as_text=True)
        result = run.get_json()
        assert result['session']['status'] == 'completed'
        assert result['parsed_response']['narrative']

        config = client.get('/clinical-ai/config')
        assert config.status_code == 200

    print('clinical_ai smoke test: OK')


if __name__ == '__main__':
    main()
