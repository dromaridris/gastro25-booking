"""Smoke test for Unit Operations module."""
from app import app, get_db


def main():
    with app.test_client() as c:
        with c.session_transaction() as sess:
            sess['user_id'] = 1
            sess['role'] = 'admin'

        endpoints = [
            '/dept-ops/',
            '/dept-ops/rooms',
            '/dept-ops/scopes',
            '/dept-ops/reprocessing',
            '/dept-ops/consumables',
            '/dept-ops/waiting-list',
            '/dept-ops/roster',
            '/dept-ops/announcements',
            '/dept-ops/messages',
        ]
        for ep in endpoints:
            r = c.get(ep)
            assert r.status_code == 200, f'{ep} returned {r.status_code}'

        r = c.post('/dept-ops/scopes', data={
            'action': 'create', 'scope_code': 'GS-TEST-01', 'scope_type': 'gastroscope',
            'model': 'Test', 'serial_number': 'SN1',
        }, follow_redirects=True)
        assert r.status_code == 200 and 'GS-TEST-01' in r.get_data(as_text=True)

        r = c.post('/dept-ops/waiting-list', data={
            'action': 'add', 'patient_name': 'Test Patient', 'mrn': 'MRN99',
            'procedure_type': 'Colonoscopy', 'priority': 'urgent',
        }, follow_redirects=True)
        assert 'Test Patient' in r.get_data(as_text=True)

        r = c.post('/dept-ops/consumables', data={
            'action': 'create', 'name': 'Test Snare', 'category': 'snare',
            'current_stock': '10', 'minimum_stock': '5',
        }, follow_redirects=True)
        assert 'Test Snare' in r.get_data(as_text=True)

        r = c.get('/dept-ops/rooms')
        assert 'Endoscopy Room 1' in r.get_data(as_text=True)

        r = c.post('/dept-ops/announcements', data={
            'title': 'Unit test', 'body': 'Announcement body', 'category': 'notice',
        }, follow_redirects=True)
        assert 'Unit test' in r.get_data(as_text=True)

        with app.app_context():
            row = get_db().execute(
                "SELECT id FROM gi_endoscope WHERE scope_code='GS-TEST-01'"
            ).fetchone()
            scope_id = row['id'] if row else None

        if scope_id:
            c.post('/dept-ops/scopes', data={
                'action': 'status', 'scope_id': scope_id,
                'status': 'awaiting_cleaning', 'location': 'Room 1',
            }, follow_redirects=True)
            r = c.post('/dept-ops/reprocessing', data={
                'action': 'start', 'scope_id': scope_id,
            }, follow_redirects=True)
            assert r.status_code == 200

        print('All dept_ops smoke tests passed.')


if __name__ == '__main__':
    main()
