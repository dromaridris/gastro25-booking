"""Unit Operations — SQLite service layer (rooms, scopes, consumables, waiting list)."""

from __future__ import annotations

from datetime import date, datetime, timedelta

from gi_platform.dept_ops_constants import (
    ALL_CONSUMABLE_CATEGORIES,
    ALL_PRIORITIES,
    ALL_ROOM_STATUSES,
    ALL_ROOM_TYPES,
    ALL_SCOPE_STATUSES,
    ALL_SCOPE_TYPES,
    ALL_SHIFT_TYPES,
    ANN_CATEGORIES,
    REPROCESSING_STEPS,
    ROOM_AVAILABLE,
    SCOPE_AVAILABLE,
    SCOPE_AWAITING_CLEANING,
    SCOPE_CLEANING,
    SCOPE_READY,
    STOCK_ADJUSTMENT,
    STOCK_RECEIPT,
    STOCK_USAGE,
    WL_ACTIVE,
    WL_SCHEDULED,
)


def _now() -> str:
    return datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')


def _today() -> str:
    return date.today().isoformat()


def ensure_dept_ops_seed(db) -> None:
    """Create default endoscopy rooms if none exist."""
    row = db.execute('SELECT COUNT(*) AS c FROM gi_endoscopy_room').fetchone()
    if row['c'] > 0:
        return
    defaults = [
        ('Endoscopy Room 1', 'general', 1),
        ('Endoscopy Room 2', 'general', 2),
        ('ERCP Suite', 'ercp', 3),
        ('Recovery Bay', 'recovery', 4),
    ]
    for name, rtype, order in defaults:
        db.execute(
            """
            INSERT INTO gi_endoscopy_room (name, room_type, sort_order, status)
            VALUES (?, ?, ?, ?)
            """,
            (name, rtype, order, ROOM_AVAILABLE),
        )
    db.commit()


# ── Dashboard ──────────────────────────────────────────────────────────────

def dashboard_context(db, user_id: int | None = None) -> dict:
    rooms = list_rooms(db)
    scopes = list_scopes(db)
    wl = waiting_list_summary(db)
    low = low_stock_items(db)
    cleaning = cleaning_queue(db)
    today = _today()
    appt_count = db.execute(
        """
        SELECT COUNT(*) AS c FROM appointment
        WHERE appointment_date = ?
        """,
        (today,),
    ).fetchone()['c']
    completed = db.execute(
        """
        SELECT COUNT(*) AS c FROM appointment
        WHERE appointment_date = ? AND no_show = 0
        """,
        (today,),
    ).fetchone()['c']
    occupied = sum(1 for r in rooms if r['status'] == 'occupied')
    return {
        'rooms_total': len(rooms),
        'rooms_occupied': occupied,
        'rooms_available': sum(1 for r in rooms if r['status'] == ROOM_AVAILABLE),
        'scopes_total': len(scopes),
        'scopes_available': sum(1 for s in scopes if s['status'] == SCOPE_AVAILABLE),
        'scopes_awaiting_cleaning': sum(1 for s in scopes if s['status'] == SCOPE_AWAITING_CLEANING),
        'scopes_in_procedure': sum(1 for s in scopes if s['status'] == 'in_procedure'),
        'waiting_list': wl,
        'waiting_pressure': wl['urgent_count'] + wl['delayed_count'],
        'low_stock': low,
        'cleaning_queue': cleaning,
        'today_procedure_count': appt_count,
        'today_completed_count': completed,
        'announcements': list_announcements(db, limit=8),
        'alerts': collect_alerts(db),
        'rooms': rooms,
        'calendar_today': date.today(),
    }


def collect_alerts(db) -> list[dict]:
    alerts: list[dict] = []
    for item in low_stock_items(db):
        alerts.append({
            'level': 'warning',
            'title': 'Low stock',
            'message': f"{item['name']}: {item['current_stock']} {item['unit']} (min {item['minimum_stock']})",
        })
    for entry in delay_alerts(db):
        alerts.append({
            'level': 'danger',
            'title': 'Waiting list delay',
            'message': f"{entry['patient_name']} — {entry['procedure_type']} ({entry['days_waiting']} days)",
        })
    for scope in list_scopes(db, status=SCOPE_AWAITING_CLEANING):
        alerts.append({
            'level': 'info',
            'title': 'Scope awaiting reprocessing',
            'message': scope['scope_code'],
        })
    return alerts[:20]


# ── Rooms ────────────────────────────────────────────────────────────────────

def list_rooms(db) -> list[dict]:
    rows = db.execute(
        """
        SELECT r.*, a.patient_name AS appt_patient
        FROM gi_endoscopy_room r
        LEFT JOIN appointment a ON a.id = r.current_appointment_id
        WHERE r.is_active = 1
        ORDER BY r.sort_order, r.name
        """
    ).fetchall()
    return [dict(r) for r in rows]


def get_room(db, room_id: int) -> dict | None:
    row = db.execute('SELECT * FROM gi_endoscopy_room WHERE id = ?', (room_id,)).fetchone()
    return dict(row) if row else None


def create_room(db, *, name: str, room_type: str, created_by: int | None) -> int:
    name = name.strip()
    if not name:
        raise ValueError('Room name is required.')
    if room_type not in ALL_ROOM_TYPES:
        raise ValueError('Invalid room type.')
    cur = db.execute(
        """
        INSERT INTO gi_endoscopy_room (name, room_type, status, created_by)
        VALUES (?, ?, ?, ?)
        """,
        (name, room_type, ROOM_AVAILABLE, created_by),
    )
    db.commit()
    return cur.lastrowid


def update_room_status(db, room_id: int, status: str, notes: str | None = None) -> None:
    if status not in ALL_ROOM_STATUSES:
        raise ValueError('Invalid room status.')
    db.execute(
        """
        UPDATE gi_endoscopy_room
        SET status = ?, status_notes = ?, updated_at = ?
        WHERE id = ?
        """,
        (status, notes or '', _now(), room_id),
    )
    db.commit()


# ── Scopes ───────────────────────────────────────────────────────────────────

def list_scopes(db, *, status: str | None = None) -> list[dict]:
    q = 'SELECT * FROM gi_endoscope WHERE is_active = 1'
    params: list = []
    if status:
        q += ' AND status = ?'
        params.append(status)
    q += ' ORDER BY scope_code'
    return [dict(r) for r in db.execute(q, params).fetchall()]


def get_scope(db, scope_id: int) -> dict | None:
    row = db.execute('SELECT * FROM gi_endoscope WHERE id = ?', (scope_id,)).fetchone()
    return dict(row) if row else None


def create_scope(
    db, *, scope_code: str, scope_type: str, model: str = '', serial_number: str = '',
    created_by: int | None = None,
) -> int:
    code = scope_code.strip()
    if not code:
        raise ValueError('Scope code is required.')
    if scope_type not in ALL_SCOPE_TYPES:
        raise ValueError('Invalid scope type.')
    exists = db.execute('SELECT id FROM gi_endoscope WHERE scope_code = ?', (code,)).fetchone()
    if exists:
        raise ValueError(f"Scope '{code}' already exists.")
    cur = db.execute(
        """
        INSERT INTO gi_endoscope
        (scope_code, scope_type, model, serial_number, status, created_by)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (code, scope_type, model.strip(), serial_number.strip(), SCOPE_AVAILABLE, created_by),
    )
    db.commit()
    return cur.lastrowid


def update_scope_status(db, scope_id: int, status: str, location: str | None = None) -> None:
    if status not in ALL_SCOPE_STATUSES:
        raise ValueError('Invalid scope status.')
    db.execute(
        """
        UPDATE gi_endoscope SET status = ?, location = COALESCE(?, location), updated_at = ?
        WHERE id = ?
        """,
        (status, location, _now(), scope_id),
    )
    db.commit()


# ── Reprocessing ─────────────────────────────────────────────────────────────

def cleaning_queue(db) -> list[dict]:
    rows = db.execute(
        """
        SELECT c.*, s.scope_code, s.scope_type
        FROM gi_scope_reprocessing_cycle c
        JOIN gi_endoscope s ON s.id = c.scope_id
        WHERE c.status = 'in_progress'
        ORDER BY c.started_at
        """
    ).fetchall()
    return [dict(r) for r in rows]


def start_reprocessing(db, scope_id: int, user_id: int | None) -> int:
    scope = get_scope(db, scope_id)
    if not scope:
        raise ValueError('Scope not found.')
    update_scope_status(db, scope_id, SCOPE_CLEANING)
    cur = db.execute(
        """
        INSERT INTO gi_scope_reprocessing_cycle
        (scope_id, started_at, current_step, status, started_by_id)
        VALUES (?, ?, ?, 'in_progress', ?)
        """,
        (scope_id, _now(), REPROCESSING_STEPS[0], user_id),
    )
    cycle_id = cur.lastrowid
    db.execute(
        """
        INSERT INTO gi_scope_reprocessing_step (cycle_id, step_code, completed_at, completed_by_id)
        VALUES (?, ?, ?, ?)
        """,
        (cycle_id, REPROCESSING_STEPS[0], _now(), user_id),
    )
    db.commit()
    return cycle_id


def advance_reprocessing_step(db, cycle_id: int, user_id: int | None, notes: str = '') -> None:
    cycle = db.execute(
        'SELECT * FROM gi_scope_reprocessing_cycle WHERE id = ?', (cycle_id,),
    ).fetchone()
    if not cycle or cycle['status'] != 'in_progress':
        raise ValueError('Reprocessing cycle not active.')
    current = cycle['current_step']
    try:
        idx = REPROCESSING_STEPS.index(current)
    except ValueError:
        idx = -1
    if idx >= len(REPROCESSING_STEPS) - 1:
        db.execute(
            """
            UPDATE gi_scope_reprocessing_cycle
            SET status = 'completed', completed_at = ?, current_step = ?
            WHERE id = ?
            """,
            (_now(), REPROCESSING_STEPS[-1], cycle_id),
        )
        update_scope_status(db, cycle['scope_id'], SCOPE_READY)
    else:
        nxt = REPROCESSING_STEPS[idx + 1]
        db.execute(
            """
            UPDATE gi_scope_reprocessing_cycle SET current_step = ? WHERE id = ?
            """,
            (nxt, cycle_id),
        )
        db.execute(
            """
            INSERT INTO gi_scope_reprocessing_step
            (cycle_id, step_code, completed_at, completed_by_id, notes)
            VALUES (?, ?, ?, ?, ?)
            """,
            (cycle_id, nxt, _now(), user_id, notes),
        )
        if nxt == 'ready_again':
            db.execute(
                """
                UPDATE gi_scope_reprocessing_cycle
                SET status = 'completed', completed_at = ? WHERE id = ?
                """,
                (_now(), cycle_id),
            )
            update_scope_status(db, cycle['scope_id'], SCOPE_AVAILABLE)
    db.commit()


def scope_reprocessing_history(db, scope_id: int) -> list[dict]:
    rows = db.execute(
        """
        SELECT * FROM gi_scope_reprocessing_cycle
        WHERE scope_id = ? ORDER BY started_at DESC LIMIT 20
        """,
        (scope_id,),
    ).fetchall()
    return [dict(r) for r in rows]


# ── Consumables ──────────────────────────────────────────────────────────────

def list_consumables(db) -> list[dict]:
    rows = db.execute(
        'SELECT * FROM gi_consumable_item WHERE is_archived = 0 ORDER BY name'
    ).fetchall()
    return [dict(r) for r in rows]


def low_stock_items(db) -> list[dict]:
    return [c for c in list_consumables(db) if c['current_stock'] <= c['minimum_stock']]


def create_consumable(
    db, *, name: str, category: str, current_stock: int = 0,
    minimum_stock: int = 0, unit: str = 'each', created_by: int | None = None,
) -> int:
    name = name.strip()
    if not name:
        raise ValueError('Name is required.')
    if category not in ALL_CONSUMABLE_CATEGORIES:
        raise ValueError('Invalid category.')
    if db.execute('SELECT id FROM gi_consumable_item WHERE name = ?', (name,)).fetchone():
        raise ValueError(f"Consumable '{name}' already exists.")
    cur = db.execute(
        """
        INSERT INTO gi_consumable_item
        (name, category, current_stock, minimum_stock, unit, created_by)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (name, category, current_stock, minimum_stock, unit, created_by),
    )
    db.commit()
    return cur.lastrowid


def record_stock_movement(
    db, consumable_id: int, movement_type: str, quantity: int,
    *, notes: str = '', recorded_by: int | None = None, appointment_id: int | None = None,
) -> None:
    if movement_type not in {STOCK_USAGE, STOCK_RECEIPT, STOCK_ADJUSTMENT}:
        raise ValueError('Invalid movement type.')
    if quantity <= 0:
        raise ValueError('Quantity must be positive.')
    item = db.execute('SELECT * FROM gi_consumable_item WHERE id = ?', (consumable_id,)).fetchone()
    if not item:
        raise ValueError('Consumable not found.')
    stock = item['current_stock']
    if movement_type == STOCK_USAGE:
        if stock < quantity:
            raise ValueError('Insufficient stock.')
        stock -= quantity
    elif movement_type == STOCK_RECEIPT:
        stock += quantity
    else:
        stock = quantity
    db.execute('UPDATE gi_consumable_item SET current_stock = ? WHERE id = ?', (stock, consumable_id))
    db.execute(
        """
        INSERT INTO gi_consumable_movement
        (consumable_id, movement_type, quantity, appointment_id, notes, recorded_by_id)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (consumable_id, movement_type, quantity, appointment_id, notes, recorded_by),
    )
    db.commit()


# ── Waiting list ─────────────────────────────────────────────────────────────

def list_waiting_list(db, *, status: str | None = None) -> list[dict]:
    q = 'SELECT * FROM gi_waiting_list_entry WHERE is_archived = 0'
    params: list = []
    if status:
        q += ' AND status = ?'
        params.append(status)
    q += ' ORDER BY CASE priority WHEN "emergency" THEN 0 WHEN "urgent" THEN 1 ELSE 2 END, listed_at'
    rows = db.execute(q, params).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d['days_waiting'] = _waiting_days(d.get('listed_at'))
        out.append(d)
    return out


def _waiting_days(listed_at: str | None) -> int:
    if not listed_at:
        return 0
    try:
        listed = datetime.fromisoformat(listed_at.replace('Z', '+00:00').split('.')[0])
    except ValueError:
        return 0
    return max((datetime.utcnow() - listed).days, 0)


def waiting_list_summary(db) -> dict:
    entries = list_waiting_list(db, status=WL_ACTIVE)
    delayed = delay_alerts(db)
    return {
        'active_count': len(entries),
        'urgent_count': sum(1 for e in entries if e['priority'] in ('urgent', 'emergency')),
        'delayed_count': len(delayed),
        'entries': entries[:15],
    }


def delay_alerts(db, threshold_days: int = 30) -> list[dict]:
    return [e for e in list_waiting_list(db, status=WL_ACTIVE) if e['days_waiting'] >= threshold_days]


def add_waiting_list_entry(
    db, *, patient_name: str, mrn: str, procedure_type: str, priority: str = 'routine',
    consultant_name: str = '', scheduled_date: str | None = None, created_by: int | None = None,
) -> int:
    if priority not in ALL_PRIORITIES:
        raise ValueError('Invalid priority.')
    status = WL_SCHEDULED if scheduled_date else WL_ACTIVE
    cur = db.execute(
        """
        INSERT INTO gi_waiting_list_entry
        (patient_name, mrn, procedure_type, priority, consultant_name, listed_at,
         scheduled_date, status, created_by)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            patient_name.strip(), mrn.strip(), procedure_type.strip(), priority,
            consultant_name.strip(), _now(), scheduled_date, status, created_by,
        ),
    )
    db.commit()
    return cur.lastrowid


def schedule_waiting_entry(db, entry_id: int, scheduled_date: str) -> None:
    db.execute(
        """
        UPDATE gi_waiting_list_entry
        SET scheduled_date = ?, status = ?, updated_at = ?
        WHERE id = ?
        """,
        (scheduled_date, WL_SCHEDULED, _now(), entry_id),
    )
    db.commit()


# ── Announcements & messages ─────────────────────────────────────────────────

def list_announcements(db, limit: int = 20) -> list[dict]:
    rows = db.execute(
        """
        SELECT a.*, u.username AS author_name
        FROM gi_dept_announcement a
        LEFT JOIN user u ON u.id = a.published_by_id
        WHERE a.is_archived = 0
        ORDER BY a.created_at DESC LIMIT ?
        """,
        (limit,),
    ).fetchall()
    return [dict(r) for r in rows]


def create_announcement(
    db, *, title: str, body: str, category: str = 'notice',
    priority: str = 'normal', published_by_id: int | None = None,
) -> int:
    if category not in ANN_CATEGORIES:
        raise ValueError('Invalid category.')
    cur = db.execute(
        """
        INSERT INTO gi_dept_announcement
        (title, body, category, priority, published_by_id)
        VALUES (?, ?, ?, ?, ?)
        """,
        (title.strip(), body.strip(), category, priority, published_by_id),
    )
    db.commit()
    return cur.lastrowid


def list_messages(db, user_id: int) -> list[dict]:
    rows = db.execute(
        """
        SELECT m.*, s.username AS sender_name, r.username AS recipient_name
        FROM gi_dept_message m
        LEFT JOIN user s ON s.id = m.sender_id
        LEFT JOIN user r ON r.id = m.recipient_id
        WHERE m.recipient_id = ? OR m.sender_id = ? OR m.message_scope = 'department'
        ORDER BY m.created_at DESC LIMIT 50
        """,
        (user_id, user_id),
    ).fetchall()
    return [dict(r) for r in rows]


def send_message(
    db, *, sender_id: int, subject: str, body: str,
    recipient_id: int | None = None, message_scope: str = 'direct',
) -> int:
    cur = db.execute(
        """
        INSERT INTO gi_dept_message
        (sender_id, recipient_id, message_scope, subject, body)
        VALUES (?, ?, ?, ?, ?)
        """,
        (sender_id, recipient_id, message_scope, subject.strip(), body.strip()),
    )
    db.commit()
    return cur.lastrowid


# ── Duty roster (endoscopy unit — distinct from gi_duty_roster_period) ───────

def roster_for_week(db, start_date: date | None = None) -> list[dict]:
    start = start_date or date.today()
    week_start = start - timedelta(days=start.weekday())
    week_end = week_start + timedelta(days=6)
    rows = db.execute(
        """
        SELECT r.*, u.username, u.full_name
        FROM gi_dept_ops_roster r
        JOIN user u ON u.id = r.user_id
        WHERE r.roster_date BETWEEN ? AND ?
        ORDER BY r.roster_date, u.username
        """,
        (week_start.isoformat(), week_end.isoformat()),
    ).fetchall()
    return [dict(r) for r in rows]


def set_roster_entry(
    db, *, user_id: int, roster_date: str, shift_type: str,
    is_on_call: int = 0, notes: str = '', created_by: int | None = None,
) -> None:
    if shift_type not in ALL_SHIFT_TYPES:
        raise ValueError('Invalid shift type.')
    existing = db.execute(
        """
        SELECT id FROM gi_dept_ops_roster
        WHERE user_id = ? AND roster_date = ?
        """,
        (user_id, roster_date),
    ).fetchone()
    if existing:
        db.execute(
            """
            UPDATE gi_dept_ops_roster
            SET shift_type = ?, is_on_call = ?, notes = ?
            WHERE id = ?
            """,
            (shift_type, is_on_call, notes, existing['id']),
        )
    else:
        db.execute(
            """
            INSERT INTO gi_dept_ops_roster
            (user_id, roster_date, shift_type, is_on_call, notes, created_by)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (user_id, roster_date, shift_type, is_on_call, notes, created_by),
        )
    db.commit()


def list_staff_users(db) -> list[dict]:
    rows = db.execute(
        """
        SELECT id, username, full_name, role FROM user
        WHERE is_approved = 1
        ORDER BY username
        """
    ).fetchall()
    return [dict(r) for r in rows]
