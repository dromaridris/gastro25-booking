import threading
import time
import sqlite3
import os

from mcq_bank.extractors.text_utils import preprocess_book_text
from mcq_bank.extractors.mcq.chapter_splitter import detect_chapters, get_chapter_text
from mcq_bank.extractors.registry import get_extractor
from mcq_bank import book_service, content_service, pdf_ingest


def create_job(db, book_id, content_type):
    cur = db.execute(
        "INSERT INTO mcqbank_extraction_job (book_id, content_type, status) VALUES (?, ?, 'queued')",
        (book_id, content_type),
    )
    db.commit()
    return cur.lastrowid


def get_job(db, job_id):
    row = db.execute("SELECT * FROM mcqbank_extraction_job WHERE id = ?", (job_id,)).fetchone()
    return dict(row) if row else None


def _update_job(conn, job_id, **fields):
    sets = ", ".join(f"{k} = ?" for k in fields)
    conn.execute(f"UPDATE mcqbank_extraction_job SET {sets} WHERE id = ?", (*fields.values(), job_id))
    conn.commit()


def start_extraction_job_async(db_path, job_id, book_id, file_path, content_type="mcq"):
    thread = threading.Thread(
        target=_run_extraction_job,
        args=(db_path, job_id, book_id, file_path, content_type),
        daemon=True,
    )
    thread.start()


def _run_extraction_job(db_path, job_id, book_id, file_path, content_type):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")

    try:
        _update_job(conn, job_id, status="running",
                    current_step="Extracting text from PDF (this can take a while for large files)",
                    started_at=time.strftime("%Y-%m-%d %H:%M:%S"))

        raw_text = pdf_ingest.extract_text_from_file(file_path)

        _update_job(conn, job_id, current_step="Preprocessing text")
        clean_text = preprocess_book_text(raw_text)
        chapters, strategy = detect_chapters(clean_text)

        _update_job(conn, job_id, current_step=f"Detected {len(chapters)} chapter(s)",
                    total_units=len(chapters))

        extractor = get_extractor(content_type)
        processed = 0

        for chapter in chapters:
            chapter_row = book_service.create_chapter(conn, book_id, chapter["number"], chapter["title"])
            ch_text = get_chapter_text(clean_text, chapter)
            items = extractor.extract(ch_text)
            content_service.save_extracted_items(conn, book_id, chapter_row["id"], content_type, items)
            processed += 1
            _update_job(
                conn, job_id, processed_units=processed,
                current_step=f"Extracted chapter {chapter['number']}: {chapter['title'][:50]} ({len(items)} items)",
            )

        _update_job(conn, job_id, status="completed", current_step="Done",
                    finished_at=time.strftime("%Y-%m-%d %H:%M:%S"))
    except Exception as e:
        _update_job(conn, job_id, status="failed", error_message=str(e),
                    finished_at=time.strftime("%Y-%m-%d %H:%M:%S"))
    finally:
        # Always drop the source book PDF — extracted text/items stay in DB.
        try:
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
        except OSError:
            pass
        conn.close()
