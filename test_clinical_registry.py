import os

from app import app

with app.test_client() as c:
    with c.session_transaction() as s:
        s['user_id'] = 1
        s['role'] = 'admin'
    r = c.get('/gi-registry')
    t = r.get_data(as_text=True)
    assert r.status_code == 200, r.status_code
    assert 'GI Clinical Registry' in t
    assert 'branch map' not in t.lower()
    assert 'Developer module map' not in t
    assert 'Upper GI Endoscopy' in t
    assert 'IBD' in t
    assert 'gi-registry-card' in t
    print('clinical registry ok')

    r = c.get('/gi-registry/procedure/ercp')
    assert r.status_code == 200
    assert 'ERCP' in r.get_data(as_text=True)
    print('procedure hub ok')

    r = c.get('/gi-registry/diagnosis/ibd')
    assert r.status_code == 200
    print('diagnosis hub ok')

    r = c.get('/gi-registry/dev-map')
    assert r.status_code == 404, 'dev map must be hidden without GASTRO25_DEV_MAP'
    print('dev map hidden ok')

    os.environ['GASTRO25_DEV_MAP'] = '1'
    try:
        r = c.get('/gi-registry/dev-map')
        assert r.status_code == 200
        assert 'Developer module map' in r.get_data(as_text=True)
        print('dev map enabled ok')
    finally:
        os.environ.pop('GASTRO25_DEV_MAP', None)
