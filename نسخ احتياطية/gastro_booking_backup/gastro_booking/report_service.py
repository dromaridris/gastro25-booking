"""
Gastro25 Core Services — Report Lifecycle Service
--------------------------------------------------
This is step 1 of the Gastro25 Core Services refactoring.

Generic report-lifecycle helpers shared by all procedure-report modules
(ERCP today; Dilatation / PEG / APC / EUS in the future).

This service manages ONLY the generic lifecycle common to every kind of
procedure report:
    - Draft creation
    - Save (updated_at bookkeeping)
    - Finalize (status, finalized_by, finalized_at)
    - Unlock (status, unlocked_by, unlocked_at)
    - Status
    - Report number generation

It intentionally knows NOTHING about any specific procedure's clinical
fields (papilla, cannulation, cholangiogram, stents, procedure-note
generation, research variables, endoscopist selection, etc.). Those stay
inside their own procedure module (today: the ERCP Reporting Module in
app.py). Any clinical validation rules (e.g. "an endoscopist must be
selected before finalizing an ERCP report") also stay in the procedure
module — this service has no opinion on them.

Every table used with this service is expected to already provide the
standard columns the existing `ercp_report` table has:
    status, created_by, created_at, updated_at,
    finalized_by, finalized_at, unlocked_by, unlocked_at

Design note: `table` / `fk_column` arguments are internal, hardcoded
constants controlled entirely by this codebase (never raw user input), so
interpolating them into the SQL strings below is safe — every actual
*value* is still passed through parameterized placeholders, exactly as
elsewhere in this app.
"""

from datetime import datetime

STATUS_DRAFT = 'draft'
STATUS_FINALIZED = 'finalized'


def _now():
    return datetime.utcnow().isoformat()


def is_finalized(report_row):
    """True if the given report row (any table using this service) is
    currently finalized/read-only."""
    return report_row['status'] == STATUS_FINALIZED


def get_or_create_report(dbconn, table, fk_column, fk_value, username):
    """
    One report per fk_value, created lazily on first access.

    Returns the existing row if one already exists for fk_value; otherwise
    inserts a fresh draft row (status/created_by/created_at/updated_at only
    — no procedure-specific columns) and returns it.

    Does NOT commit — callers that need to also seed procedure-specific
    companion rows (e.g. ERCP's `ercp_research` row) in the same
    create-on-first-open transaction should commit once, after this call,
    the same way the existing code already does.
    """
    row = dbconn.execute(
        f'SELECT * FROM {table} WHERE {fk_column} = ?', (fk_value,)
    ).fetchone()
    if row:
        return row, False

    now = _now()
    dbconn.execute(
        f'INSERT INTO {table} ({fk_column}, status, created_by, created_at, updated_at) '
        f'VALUES (?, ?, ?, ?, ?)',
        (fk_value, STATUS_DRAFT, username, now, now)
    )
    row = dbconn.execute(
        f'SELECT * FROM {table} WHERE {fk_column} = ?', (fk_value,)
    ).fetchone()
    return row, True


def save_fields(dbconn, table, report_id, fields):
    """
    Update `fields` (dict of column: value) on the given report row, plus
    the generic updated_at timestamp. Does not commit.

    Caller is responsible for confirming the report isn't finalized first
    (whether a finalized report is fully locked or allows some edits is a
    per-module policy decision, not a generic lifecycle rule).
    """
    now = _now()
    if fields:
        set_clause = ', '.join(f'{k}=?' for k in fields) + ', updated_at=?'
        values = list(fields.values()) + [now, report_id]
    else:
        set_clause = 'updated_at=?'
        values = [now, report_id]
    dbconn.execute(f'UPDATE {table} SET {set_clause} WHERE id=?', values)
    return now


def finalize_report(dbconn, table, report_id, username):
    """Mark a report finalized. Does not commit. Returns the finalized_at
    timestamp used."""
    now = _now()
    dbconn.execute(
        f"UPDATE {table} SET status=?, finalized_by=?, finalized_at=?, updated_at=? WHERE id=?",
        (STATUS_FINALIZED, username, now, now, report_id)
    )
    return now


def unlock_report(dbconn, table, report_id, username):
    """Return a finalized report to draft status for editing. Does not
    commit. Returns the unlocked_at timestamp used."""
    now = _now()
    dbconn.execute(
        f"UPDATE {table} SET status=?, unlocked_by=?, unlocked_at=?, updated_at=? WHERE id=?",
        (STATUS_DRAFT, username, now, now, report_id)
    )
    return now


def generate_report_number(prefix, report_id):
    """Human-facing report number, e.g. 'ERCP-42'. Always derived fresh
    from the row id — nothing stored, so there's no separate counter that
    could ever drift out of sync."""
    return f'{prefix}-{report_id}'
