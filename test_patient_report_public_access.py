"""Regression tests for signed, read-only patient report links."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

import app as gastro
import patient_report_service


def _insert_appointment(db, procedure_type):
    now = datetime.utcnow().isoformat()
    cur = db.execute(
        'INSERT INTO appointment '
        '(patient_name, gender, age, phone, mrn, procedure_type, appointment_date, '
        'booked_by_username, booked_by_role, created_at) '
        'VALUES (?,?,?,?,?,?,?,?,?,?)',
        (
            'Patient QR Test', 'Other', 40, '', 'QR-TEST-001', procedure_type,
            '2026-08-21', 'tester', 'admin', now,
        ),
    )
    return cur.lastrowid


def _insert_report(db, kind, status='finalized'):
    appointment_id = _insert_appointment(db, kind)
    now = datetime.utcnow().isoformat()
    table = 'ercp_report' if kind == 'ercp' else 'dilatation_report'
    cur = db.execute(
        f'INSERT INTO {table} '
        '(appointment_id, status, finalized_by, finalized_at, created_by, created_at, updated_at) '
        'VALUES (?,?,?,?,?,?,?)',
        (appointment_id, status, 'tester', now, 'tester', now, now),
    )
    db.commit()
    return cur.lastrowid, appointment_id, now


def _token(kind, report_id, finalized_at):
    return patient_report_service.issue_token(
        gastro.app.config['SECRET_KEY'],
        kind,
        report_id,
        finalized_at,
    )


def test_patient_report_token_rejects_tampering():
    token = _token('ercp', 123, '2026-08-21T10:00:00')
    assert patient_report_service.read_token(
        gastro.app.config['SECRET_KEY'], token
    )['report_id'] == 123

    replacement = 'A' if token[-1] != 'A' else 'B'
    with pytest.raises(ValueError):
        patient_report_service.read_token(
            gastro.app.config['SECRET_KEY'], token[:-1] + replacement
        )


@pytest.mark.parametrize('kind', ['ercp', 'dilatation'])
def test_finalized_report_has_public_read_only_view(kind):
    with gastro.app.app_context():
        report_id, _, finalized_at = _insert_report(gastro.get_db(), kind)
    token = _token(kind, report_id, finalized_at)

    response = gastro.app.test_client().get(f'/patient-report/{token}')
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert 'Patient QR Test' in body
    assert 'Print / Save as PDF' in body
    assert 'Staff Login' in body
    assert 'Register here' not in body
    assert response.headers['Cache-Control'] == 'private, no-store, max-age=0'
    assert response.headers['X-Robots-Tag'] == 'noindex, nofollow, noarchive'


def test_public_link_is_revoked_when_report_is_unlocked():
    with gastro.app.app_context():
        db = gastro.get_db()
        report_id, _, finalized_at = _insert_report(db, 'ercp')
        token = _token('ercp', report_id, finalized_at)
        db.execute("UPDATE ercp_report SET status='draft' WHERE id=?", (report_id,))
        db.commit()

    response = gastro.app.test_client().get(f'/patient-report/{token}')
    assert response.status_code == 404


def test_public_link_is_revoked_after_new_finalization_revision():
    with gastro.app.app_context():
        db = gastro.get_db()
        report_id, _, finalized_at = _insert_report(db, 'dilatation')
        token = _token('dilatation', report_id, finalized_at)
        db.execute(
            'UPDATE dilatation_report SET finalized_at=? WHERE id=?',
            ('2026-08-21T11:00:00', report_id),
        )
        db.commit()

    response = gastro.app.test_client().get(f'/patient-report/{token}')
    assert response.status_code == 404


def test_print_qr_targets_patient_view_only_after_finalization(monkeypatch):
    monkeypatch.setattr(gastro.qr_service, 'generate_data_uri', lambda url: url)
    with gastro.app.app_context():
        db = gastro.get_db()
        finalized_id, _, _ = _insert_report(db, 'ercp')
        draft_id, _, _ = _insert_report(db, 'ercp', status='draft')

    with gastro.app.test_request_context(base_url='https://gastro.example/'):
        finalized_context = gastro._build_ercp_print_context(finalized_id)
        draft_context = gastro._build_ercp_print_context(draft_id)

    assert '/patient-report/' in finalized_context['qr_data_uri']
    assert '/login?' in draft_context['qr_data_uri']
    assert 'qr=1' in draft_context['qr_data_uri']


def test_public_image_requires_the_matching_finalized_report_token():
    with gastro.app.app_context():
        db = gastro.get_db()
        report_id, _, finalized_at = _insert_report(db, 'ercp')
        image_name = f'patient_qr_test_{report_id}.jpg'
        image_path = Path(gastro.ERCP_IMAGES_DIR) / image_name
        image_path.write_bytes(b'not-a-real-jpeg-but-safe-for-route-test')
        db.execute(
            'INSERT INTO ercp_report_image '
            '(report_id, slot, filename, caption, uploaded_by, uploaded_at) '
            'VALUES (?,?,?,?,?,?)',
            (report_id, 1, image_name, 'QR image', 'tester', finalized_at),
        )
        db.commit()

    token = _token('ercp', report_id, finalized_at)
    client = gastro.app.test_client()
    page = client.get(f'/patient-report/{token}')
    image = client.get(f'/patient-report/{token}/image/1')

    assert page.status_code == 200
    assert f'/patient-report/{token}/image/1' in page.get_data(as_text=True)
    assert image.status_code == 200
    assert image.headers['Cache-Control'] == 'private, no-store, max-age=0'
    assert client.get(f'/patient-report/{token}/image/2').status_code == 404
