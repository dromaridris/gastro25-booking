from mcq_bank import content_service


def resolve_scope(db, book_id=None, chapter_id=None, topic=None):
    if chapter_id:
        scope_key = f"chapter:{chapter_id}"
        clauses, params = ["chapter_id = ?"], [chapter_id]
    elif topic:
        scope_key = f"topic:{topic}"
        clauses, params = ["chapter_id IN (SELECT id FROM mcqbank_chapter WHERE topic = ?)"], [topic]
    elif book_id:
        scope_key = f"book:{book_id}"
        clauses, params = ["book_id = ?"], [book_id]
    else:
        scope_key = "all"
        clauses, params = [], []

    item_ids = content_service.student_list_approved_ids(db, clauses, params)
    return scope_key, item_ids


def get_wrong_only_items(db, user_id, base_scope_key):
    rows = db.execute(
        """SELECT DISTINCT content_item_id FROM mcqbank_user_progress
           WHERE user_id = ? AND scope_key = ? AND status = 'answered_wrong'""",
        (user_id, base_scope_key),
    ).fetchall()
    return [r["content_item_id"] for r in rows]


def get_or_create_current_cycle(db, user_id, scope_key):
    row = db.execute(
        """SELECT * FROM mcqbank_user_cycle WHERE user_id = ? AND scope_key = ?
           AND completed_at IS NULL ORDER BY cycle_number DESC LIMIT 1""",
        (user_id, scope_key),
    ).fetchone()
    if row:
        return row["cycle_number"]
    last = db.execute(
        "SELECT MAX(cycle_number) m FROM mcqbank_user_cycle WHERE user_id = ? AND scope_key = ?",
        (user_id, scope_key),
    ).fetchone()
    next_cycle = (last["m"] or 0) + 1
    db.execute(
        "INSERT INTO mcqbank_user_cycle (user_id, scope_key, cycle_number) VALUES (?, ?, ?)",
        (user_id, scope_key, next_cycle),
    )
    db.commit()
    return next_cycle


def ensure_cycle_progress_rows(db, user_id, scope_key, cycle_number, item_ids):
    for item_id in item_ids:
        db.execute(
            """INSERT OR IGNORE INTO mcqbank_user_progress
               (user_id, content_item_id, scope_key, cycle_number, status)
               VALUES (?, ?, ?, ?, 'unseen')""",
            (user_id, item_id, scope_key, cycle_number),
        )
    db.commit()


def get_next_question(db, user_id, scope_key, cycle_number, item_ids, random_order=False):
    if not item_ids:
        return None
    placeholders = ",".join("?" * len(item_ids))
    order_by = "RANDOM()" if random_order else "ci.chapter_id, ci.item_number"
    row = db.execute(
        f"""SELECT up.content_item_id FROM mcqbank_user_progress up
            JOIN mcqbank_content_item ci ON ci.id = up.content_item_id
            WHERE up.user_id = ? AND up.scope_key = ? AND up.cycle_number = ?
              AND up.status = 'unseen' AND up.content_item_id IN ({placeholders})
            ORDER BY {order_by} LIMIT 1""",
        (user_id, scope_key, cycle_number, *item_ids),
    ).fetchone()
    return row["content_item_id"] if row else None


def submit_answer(db, user_id, content_item_id, scope_key, cycle_number, selected_option):
    payload = content_service.student_get_item_payload(db, content_item_id)
    if payload is None:
        return None
    prev = db.execute(
        """SELECT status FROM mcqbank_user_progress
           WHERE user_id = ? AND content_item_id = ? AND scope_key = ? AND cycle_number = ?""",
        (user_id, content_item_id, scope_key, cycle_number),
    ).fetchone()
    first_answer = not prev or prev["status"] == "unseen"

    is_correct = selected_option == payload["correct_answer"]
    status = "answered_correct" if is_correct else "answered_wrong"
    db.execute(
        """UPDATE mcqbank_user_progress SET status = ?, selected_option = ?, is_correct = ?,
           answered_at = datetime('now')
           WHERE user_id = ? AND content_item_id = ? AND scope_key = ? AND cycle_number = ?""",
        (status, selected_option, 1 if is_correct else 0, user_id, content_item_id, scope_key, cycle_number),
    )
    db.commit()

    daily_target = None
    if first_answer:
        from mcq_bank import daily_target_service
        daily_target = daily_target_service.record_solves(db, user_id, 1)

    from mcq_bank.extractors.mcq.schema import student_view
    result = {
        "is_correct": is_correct,
        **student_view(payload, reveal_answer=True),
    }
    if daily_target is not None:
        result["daily_target"] = daily_target
    return result


def get_stats(db, user_id, scope_key, cycle_number):
    row = db.execute(
        """SELECT
             COUNT(*) AS total,
             SUM(CASE WHEN status != 'unseen' THEN 1 ELSE 0 END) AS solved,
             SUM(CASE WHEN status = 'unseen' THEN 1 ELSE 0 END) AS remaining,
             SUM(CASE WHEN status = 'answered_correct' THEN 1 ELSE 0 END) AS correct
           FROM mcqbank_user_progress WHERE user_id = ? AND scope_key = ? AND cycle_number = ?""",
        (user_id, scope_key, cycle_number),
    ).fetchone()
    total = row["total"] or 0
    solved = row["solved"] or 0
    correct = row["correct"] or 0
    accuracy = round((correct / solved) * 100, 1) if solved else 0.0
    return {
        "total": total, "solved": solved, "remaining": row["remaining"] or 0,
        "correct": correct, "accuracy_pct": accuracy, "cycle_number": cycle_number,
    }


def maybe_complete_cycle(db, user_id, scope_key, cycle_number):
    stats = get_stats(db, user_id, scope_key, cycle_number)
    if stats["remaining"] == 0 and stats["total"] > 0:
        db.execute(
            """UPDATE mcqbank_user_cycle SET completed_at = datetime('now')
               WHERE user_id = ? AND scope_key = ? AND cycle_number = ? AND completed_at IS NULL""",
            (user_id, scope_key, cycle_number),
        )
        db.commit()
        return True
    return False
