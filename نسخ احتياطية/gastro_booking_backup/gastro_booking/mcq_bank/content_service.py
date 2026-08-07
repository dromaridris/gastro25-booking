import json


def save_extracted_items(db, book_id, chapter_id, content_type, extracted_items):
    saved_ids = []
    for item in extracted_items:
        cur = db.execute(
            """INSERT INTO mcqbank_content_item
               (book_id, chapter_id, content_type, item_number, payload_json,
                status, confidence_flag, review_flags_json, review_evidence_json,
                source_location_json, raw_extracted_text)
               VALUES (?, ?, ?, ?, ?, 'pending_review', ?, ?, ?, ?, ?)""",
            (
                book_id, chapter_id, content_type, item.item_number,
                json.dumps(item.payload, ensure_ascii=False),
                item.confidence_flag,
                json.dumps(item.review_flags, ensure_ascii=False),
                json.dumps(item.review_evidence, ensure_ascii=False) if item.review_evidence else None,
                json.dumps(item.source_location, ensure_ascii=False),
                item.raw_extracted_text,
            ),
        )
        saved_ids.append(cur.lastrowid)
    db.commit()
    return saved_ids


def _row_to_dict(row):
    d = dict(row)
    d["payload"] = json.loads(d.pop("payload_json"))
    d["review_flags"] = json.loads(d.pop("review_flags_json") or "[]")
    d["review_evidence"] = json.loads(d.pop("review_evidence_json")) if d.get("review_evidence_json") else None
    d["source_location"] = json.loads(d.pop("source_location_json") or "{}")
    return d


# ---------- Manager-facing (admin/hod/specialist/registrar - full detail) ----------

def admin_list_items(db, book_id=None, chapter_id=None, content_type=None,
                      status=None, confidence_flag=None, search=None, limit=100, offset=0):
    clauses, params = [], []
    if book_id:
        clauses.append("book_id = ?"); params.append(book_id)
    if chapter_id:
        clauses.append("chapter_id = ?"); params.append(chapter_id)
    if content_type:
        clauses.append("content_type = ?"); params.append(content_type)
    if status:
        clauses.append("status = ?"); params.append(status)
    if confidence_flag:
        clauses.append("confidence_flag = ?"); params.append(confidence_flag)
    if search:
        clauses.append("payload_json LIKE ?"); params.append(f"%{search}%")
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    rows = db.execute(
        f"SELECT * FROM mcqbank_content_item {where} ORDER BY chapter_id, item_number LIMIT ? OFFSET ?",
        (*params, limit, offset),
    ).fetchall()
    return [_row_to_dict(r) for r in rows]


def admin_count_items(db, book_id=None, chapter_id=None, status=None):
    clauses, params = [], []
    if book_id:
        clauses.append("book_id = ?"); params.append(book_id)
    if chapter_id:
        clauses.append("chapter_id = ?"); params.append(chapter_id)
    if status:
        clauses.append("status = ?"); params.append(status)
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    row = db.execute(f"SELECT COUNT(*) c FROM mcqbank_content_item {where}", params).fetchone()
    return row["c"]


def admin_get_item(db, item_id):
    row = db.execute("SELECT * FROM mcqbank_content_item WHERE id = ?", (item_id,)).fetchone()
    return _row_to_dict(row) if row else None


def admin_update_payload(db, item_id, payload: dict):
    db.execute(
        "UPDATE mcqbank_content_item SET payload_json = ?, updated_at = datetime('now') WHERE id = ?",
        (json.dumps(payload, ensure_ascii=False), item_id),
    )
    db.commit()


def admin_set_status(db, item_id, status):
    assert status in ("pending_review", "approved", "rejected")
    db.execute(
        "UPDATE mcqbank_content_item SET status = ?, updated_at = datetime('now') WHERE id = ?",
        (status, item_id),
    )
    db.commit()


def admin_bulk_approve_high_confidence(db, book_id, chapter_id=None):
    clauses = ["book_id = ?", "confidence_flag = 'high'", "status = 'pending_review'"]
    params = [book_id]
    if chapter_id:
        clauses.append("chapter_id = ?")
        params.append(chapter_id)
    db.execute(
        f"UPDATE mcqbank_content_item SET status='approved', updated_at=datetime('now') WHERE {' AND '.join(clauses)}",
        params,
    )
    db.commit()


# ---------- Student-facing (approved only, safe fields only) ----------

def student_list_approved_ids(db, scope_clauses, scope_params, content_type="mcq"):
    where = " AND ".join(["content_type = ?", "status = 'approved'"] + scope_clauses)
    rows = db.execute(
        f"SELECT id FROM mcqbank_content_item WHERE {where} ORDER BY chapter_id, item_number",
        (content_type, *scope_params),
    ).fetchall()
    return [r["id"] for r in rows]


def student_get_item_payload(db, item_id):
    row = db.execute(
        "SELECT payload_json FROM mcqbank_content_item WHERE id = ? AND status = 'approved'", (item_id,)
    ).fetchone()
    return json.loads(row["payload_json"]) if row else None


def random_approved_item_ids(db, count, book_id=None, chapter_id=None):
    clauses, params = ["content_type = 'mcq'", "status = 'approved'"], []
    if book_id:
        clauses.append("book_id = ?"); params.append(book_id)
    if chapter_id:
        clauses.append("chapter_id = ?"); params.append(chapter_id)
    where = " AND ".join(clauses)
    rows = db.execute(
        f"SELECT id FROM mcqbank_content_item WHERE {where} ORDER BY RANDOM() LIMIT ?",
        (*params, count),
    ).fetchall()
    return [r["id"] for r in rows]
