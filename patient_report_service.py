"""Signed, read-only patient report links.

The token contains only the procedure kind, report id and finalization
revision.  Patient data is never embedded in the token.  A token becomes
invalid automatically if the report is unlocked or finalized again.
"""

from __future__ import annotations

from itsdangerous import BadData, URLSafeSerializer


TOKEN_SALT = 'gastro25-patient-report-v1'
TOKEN_VERSION = 1
ALLOWED_REPORT_KINDS = frozenset({'ercp', 'dilatation'})


def issue_token(secret_key: str, report_kind: str, report_id: int, finalized_at: str) -> str:
    """Return a permanent signed token for one finalized report revision."""
    kind = str(report_kind or '').strip().lower()
    revision = str(finalized_at or '').strip()
    if kind not in ALLOWED_REPORT_KINDS:
        raise ValueError('Unsupported patient report kind.')
    if not isinstance(report_id, int) or report_id < 1:
        raise ValueError('Invalid patient report id.')
    if not revision:
        raise ValueError('A finalized report revision is required.')

    serializer = URLSafeSerializer(secret_key, salt=TOKEN_SALT)
    return serializer.dumps({
        'v': TOKEN_VERSION,
        'kind': kind,
        'report_id': report_id,
        'finalized_at': revision,
    })


def read_token(secret_key: str, token: str) -> dict:
    """Verify and normalize a patient-report token.

    ValueError is deliberately used for every invalid-token condition so the
    public route can return the same 404 response without leaking which part
    was wrong.
    """
    if not isinstance(token, str) or not token or len(token) > 1024:
        raise ValueError('Invalid patient report token.')

    serializer = URLSafeSerializer(secret_key, salt=TOKEN_SALT)
    try:
        payload = serializer.loads(token)
    except BadData as exc:
        raise ValueError('Invalid patient report token.') from exc

    if not isinstance(payload, dict) or payload.get('v') != TOKEN_VERSION:
        raise ValueError('Invalid patient report token.')

    kind = str(payload.get('kind') or '').strip().lower()
    report_id = payload.get('report_id')
    finalized_at = str(payload.get('finalized_at') or '').strip()
    if kind not in ALLOWED_REPORT_KINDS:
        raise ValueError('Invalid patient report token.')
    if not isinstance(report_id, int) or report_id < 1 or not finalized_at:
        raise ValueError('Invalid patient report token.')

    return {
        'kind': kind,
        'report_id': report_id,
        'finalized_at': finalized_at,
    }
