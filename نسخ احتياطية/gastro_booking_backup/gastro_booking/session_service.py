"""
Gastro25 Core Services — Session Service
--------------------------------------------
Generic helpers for a procedure's session numbering: "Session 1",
"Session 2", ... across all of a patient's visits for a given procedure,
plus support for the "repeat this session" linkage.

Used today by the ERCP module's Patient Overview page and Repeat ERCP
workflow. Any future procedure module (Dilatation, PEG, APC, EUS, ...)
can reuse this exactly by supplying its own procedure_type — e.g.:

    ERCP Session 1, ERCP Session 2, ...
    Dilatation Session 1, ...
    PEG Session 1, ...

— all computed the same way, with no per-procedure duplication of the
numbering/repeat-linkage logic.

This service knows nothing about clinical content. It only orders and
numbers rows from the shared `appointment` table for one patient + one
procedure_type; all clinical/report data still lives in that procedure's
own report table (e.g. ercp_report), untouched by this module.
"""


def list_sessions(dbconn, procedure_type, mrn, fallback_row=None):
    """All of one patient's appointments for a given procedure, oldest
    first — the canonical session order.

    A blank/missing MRN falls back to a single-row list containing
    `fallback_row` — this mirrors the existing behaviour: an appointment
    with no MRN on file can't be reliably cross-linked to other visits,
    so only that single visit is treated as "session 1"."""
    mrn = (mrn or '').strip()
    if not mrn:
        return [fallback_row] if fallback_row is not None else []
    return dbconn.execute(
        'SELECT * FROM appointment WHERE procedure_type = ? AND mrn = ? '
        'ORDER BY appointment_date, id',
        (procedure_type, mrn)
    ).fetchall()


def list_sessions_for_types(dbconn, procedure_types, mrn, fallback_row=None):
    """Sessions across multiple related procedure_type values (e.g. upper_gi + peg_tube)."""
    types = [t for t in procedure_types if t]
    if not types:
        return list_sessions(dbconn, '', mrn, fallback_row=fallback_row)
    mrn = (mrn or '').strip()
    if not mrn:
        return [fallback_row] if fallback_row is not None else []
    placeholders = ','.join('?' * len(types))
    return dbconn.execute(
        f'SELECT * FROM appointment WHERE procedure_type IN ({placeholders}) AND mrn = ? '
        'ORDER BY appointment_date, id',
        (*types, mrn),
    ).fetchall()


def number_sessions(session_rows):
    """[row, row, ...] (already in session order) ->
    {appointment_id: session_number}, 1-indexed."""
    return {row['id']: idx for idx, row in enumerate(session_rows, start=1)}


def repeat_of_session_number(session_number_map, repeat_of_appointment_id):
    """Given the {appointment_id: session_number} map and a row's
    repeat_of_appointment_id, return which session number it's a repeat
    of (or None if it isn't a repeat / the source session isn't in this
    list)."""
    return session_number_map.get(repeat_of_appointment_id)


def next_session_number(session_rows):
    """The session number a brand-new repeat visit for this patient +
    procedure would receive next. Available for any future UI that wants
    to show "This will be Session N" before the repeat is booked — not
    currently wired into any page, so it introduces no visible change."""
    return len(session_rows) + 1
