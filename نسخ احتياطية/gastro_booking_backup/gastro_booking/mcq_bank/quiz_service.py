"""
'Generate Quiz' feature: a manager (admin/hod/specialist/registrar) picks N
random approved questions and assigns the quiz to specific users. Assignment
delivery deliberately reuses the EXISTING gi_training_assignment table and
notification_service.notify_user() - the same mechanism governance/roster
already use to push things into a user's "My Tasks" - instead of building a
parallel task system. See notification_service.py's _MY_TASKS_FILTER for the
one-line addition that makes quiz links count as a My Task.
"""
from mcq_bank import content_service
from gi_platform import notification_service


def generate_quiz(db, title, question_count, created_by_id, book_id=None, chapter_id=None):
    item_ids = content_service.random_approved_item_ids(
        db, question_count, book_id=book_id, chapter_id=chapter_id
    )
    if not item_ids:
        return None

    cur = db.execute(
        """INSERT INTO mcqbank_quiz (title, book_id, chapter_id, question_count, created_by_id)
           VALUES (?, ?, ?, ?, ?)""",
        (title, book_id, chapter_id, len(item_ids), created_by_id),
    )
    quiz_id = cur.lastrowid
    for position, item_id in enumerate(item_ids, start=1):
        db.execute(
            "INSERT INTO mcqbank_quiz_item (quiz_id, content_item_id, position) VALUES (?, ?, ?)",
            (quiz_id, item_id, position),
        )
    db.commit()
    return db.execute("SELECT * FROM mcqbank_quiz WHERE id = ?", (quiz_id,)).fetchone()


def assign_quiz_to_users(db, quiz_id, user_ids, assigned_by_id):
    quiz = db.execute("SELECT * FROM mcqbank_quiz WHERE id = ?", (quiz_id,)).fetchone()
    if not quiz:
        return 0

    assigned = 0
    for user_id in user_ids:
        existing = db.execute(
            "SELECT 1 FROM mcqbank_quiz_assignment WHERE quiz_id = ? AND user_id = ?",
            (quiz_id, user_id),
        ).fetchone()
        if existing:
            continue

        ta_cur = db.execute(
            """INSERT INTO gi_training_assignment
               (user_id, assignment_type, source_module, source_id, title, details, assigned_by_id)
               VALUES (?, 'mcq_quiz', 'mcq_bank', ?, ?, ?, ?)""",
            (
                user_id, quiz_id, f"Quiz: {quiz['title']}",
                f"{quiz['question_count']} questions", assigned_by_id,
            ),
        )
        training_assignment_id = ta_cur.lastrowid

        db.execute(
            """INSERT INTO mcqbank_quiz_assignment
               (quiz_id, user_id, training_assignment_id, score_total)
               VALUES (?, ?, ?, ?)""",
            (quiz_id, user_id, training_assignment_id, quiz["question_count"]),
        )

        notification_service.notify_user(
            db, user_id=user_id,
            title=f"New quiz assigned: {quiz['title']}",
            body=f"{quiz['question_count']} questions - tap to start.",
            link_url=f"/mcq-bank/quiz/{quiz_id}/take",
        )
        assigned += 1

    db.commit()
    return assigned


def list_my_assigned_quizzes(db, user_id, status=None):
    clauses, params = ["qa.user_id = ?"], [user_id]
    if status:
        clauses.append("qa.status = ?")
        params.append(status)
    where = " AND ".join(clauses)
    return db.execute(
        f"""SELECT qa.*, q.title, q.question_count
            FROM mcqbank_quiz_assignment qa
            JOIN mcqbank_quiz q ON q.id = qa.quiz_id
            WHERE {where} ORDER BY qa.created_at DESC""",
        params,
    ).fetchall()


def get_quiz_items(db, quiz_id):
    return db.execute(
        """SELECT qi.position, ci.id AS content_item_id, ci.payload_json
           FROM mcqbank_quiz_item qi
           JOIN mcqbank_content_item ci ON ci.id = qi.content_item_id
           WHERE qi.quiz_id = ? ORDER BY qi.position""",
        (quiz_id,),
    ).fetchall()


def record_quiz_result(db, quiz_id, user_id, correct_count, total_count):
    db.execute(
        """UPDATE mcqbank_quiz_assignment
           SET status = 'done', score_correct = ?, score_total = ?, completed_at = datetime('now')
           WHERE quiz_id = ? AND user_id = ?""",
        (correct_count, total_count, quiz_id, user_id),
    )
    row = db.execute(
        "SELECT training_assignment_id FROM mcqbank_quiz_assignment WHERE quiz_id = ? AND user_id = ?",
        (quiz_id, user_id),
    ).fetchone()
    if row and row["training_assignment_id"]:
        db.execute(
            "UPDATE gi_training_assignment SET status = 'done', completed_at = datetime('now') WHERE id = ?",
            (row["training_assignment_id"],),
        )
    db.commit()
