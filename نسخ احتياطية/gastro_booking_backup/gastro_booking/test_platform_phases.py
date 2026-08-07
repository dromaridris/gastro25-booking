"""Smoke tests for platform phases 1–4."""

from __future__ import annotations

import io

from app import app


def main() -> None:
    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['role'] = 'admin'

        for path in (
            '/admin/clinical-ai',
            '/admin/branding',
            '/admin/pharma-banner',
            '/consult-requests',
            '/calendar-hub',
            '/education',
            '/archive',
        ):
            resp = client.get(path)
            assert resp.status_code == 200, f'{path}: {resp.get_data(as_text=True)[:500]}'

        status = client.get('/clinical-ai/status')
        assert status.status_code == 200
        assert status.get_json()['status'] == 'ok'

        # Branding save
        resp = client.post('/admin/branding', data={
            'site_name': 'Test GI Unit',
            'slogan': 'Test slogan',
            'dept_subtitle': 'Ward 25',
            'primary_color': '#A6192E',
            'secondary_color': '#1a1a2e',
        }, follow_redirects=True)
        assert resp.status_code == 200

        # Pharma banner
        resp = client.post('/admin/pharma-banner', data={
            'action': 'create',
            'label': 'Test',
            'message': 'Education ticker test',
            'sort_order': '0',
        }, follow_redirects=True)
        assert resp.status_code == 200

        # Consult request needs ward patient — fetch list page with new form
        resp = client.get('/consult-requests/new')
        assert resp.status_code == 200

        # Calendar hub add event
        resp = client.post('/calendar-hub/event', data={
            'title': 'Smoke test event',
            'event_date': '2026-08-01',
            'event_type': 'general',
        }, follow_redirects=True)
        assert resp.status_code == 200

        # Education
        resp = client.post('/education/new', data={
            'title': 'Journal club',
            'activity_type': 'journal_club',
            'activity_date': '2026-08-01',
            'user_id': '1',
        }, follow_redirects=True)
        assert resp.status_code == 200

        # Archive metadata-only
        resp = client.post('/archive/new', data={
            'title': 'Old export',
            'record_type': 'export',
            'source_module': 'test',
            'summary': 'Smoke test',
        }, follow_redirects=True)
        assert resp.status_code == 200

        # Clinical AI provider test (stub)
        resp = client.post('/admin/clinical-ai/test', data={'provider_key': 'stub'}, follow_redirects=True)
        assert resp.status_code == 200

        # Patient documents page — ward patient 1 may not exist; accept redirect or 200
        resp = client.get('/ward/patient/1/documents')
        assert resp.status_code in (200, 302)

        # Optional upload if patient exists
        wp = client.get('/ward/patient/1/documents')
        if wp.status_code == 200:
            pdf = io.BytesIO(b'%PDF-1.4 test')
            resp = client.post('/ward/patient/1/documents', data={
                'title': 'Smoke doc',
                'category': 'general',
                'document_file': (pdf, 'test.pdf'),
            }, content_type='multipart/form-data', follow_redirects=True)
            assert resp.status_code == 200

    print('platform_phases smoke test: OK')


if __name__ == '__main__':
    main()
