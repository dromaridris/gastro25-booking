#!/usr/bin/env python3
"""Extract Bates OCR PDF and import into Knowledge Library (gi_knowledge_object).

Preserves page order and stores every non-empty line. Creates:
  - 1 published parent guideline (supersedes truncated id 977 when present)
  - page-batch reference objects (fine-grained / reviewable chunks)
  - gi_knowledge_link parent → batches
  - import job + provenance rows (same path as Import Manager)

Re-run:
  python scripts/import_bates_ocr.py
  python scripts/import_bates_ocr.py --pdf "D:\\gastro materials\\BATES OCR.pdf"
  python scripts/import_bates_ocr.py --extract-only
  python scripts/import_bates_ocr.py --import-only
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PDF = Path(r"D:\gastro materials\BATES OCR.pdf")
EXTRACT_DIR = ROOT / "scripts" / "tmp_bates_ocr"
PAGES_JSONL = EXTRACT_DIR / "pages.jsonl"
FULL_TXT = EXTRACT_DIR / "full_text.txt"
MANIFEST = EXTRACT_DIR / "manifest.json"
DB_PATH = ROOT / "gastro_booking.db"

SOURCE_LABEL = "Bates OCR"
WORK_TITLE = "Bates' Guide to Physical Examination and History Taking"
PARENT_SLUG = "bates-ocr-guide-physical-examination-history-taking"
OLD_OBJECT_ID = 977
PAGES_PER_BATCH = 10


def _connect() -> sqlite3.Connection:
    db = sqlite3.connect(str(DB_PATH))
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    return db


def extract_pdf(pdf_path: Path) -> dict:
    try:
        import fitz  # pymupdf
    except ImportError as exc:
        raise SystemExit("pymupdf (fitz) is required for Bates OCR extraction") from exc

    if not pdf_path.is_file():
        raise SystemExit(f"PDF not found: {pdf_path}")

    EXTRACT_DIR.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(str(pdf_path))
    page_count = doc.page_count
    total_lines = 0
    total_chars = 0
    empty_pages = 0

    with PAGES_JSONL.open("w", encoding="utf-8") as jl, FULL_TXT.open(
        "w", encoding="utf-8"
    ) as txt:
        for i in range(page_count):
            raw = doc[i].get_text("text") or ""
            # Keep every line (including blanks) for faithful page order; mark blank.
            all_lines = raw.splitlines()
            lines = []
            for n, line in enumerate(all_lines, start=1):
                lines.append({"n": n, "t": line, "blank": not bool(line.strip())})
            nonempty = [ln for ln in lines if not ln["blank"]]
            if not nonempty and not raw.strip():
                empty_pages += 1
            total_lines += len(nonempty)
            total_chars += len(raw)

            page_rec = {
                "page": i + 1,
                "char_count": len(raw),
                "line_count": len(nonempty),
                "line_count_all": len(lines),
                "text": raw,
                "lines": lines,
            }
            jl.write(json.dumps(page_rec, ensure_ascii=False) + "\n")
            txt.write(f"\n\n===== PAGE {i + 1} / {page_count} =====\n")
            txt.write(raw if raw.endswith("\n") or not raw else raw + "\n")

            if (i + 1) % 100 == 0 or i == 0:
                print(f"  extracted page {i + 1}/{page_count}", flush=True)

    doc.close()
    manifest = {
        "source_label": SOURCE_LABEL,
        "work": WORK_TITLE,
        "pdf_path": str(pdf_path),
        "pdf_size_bytes": pdf_path.stat().st_size,
        "page_count": page_count,
        "empty_pages": empty_pages,
        "nonempty_pages": page_count - empty_pages,
        "line_count_nonempty": total_lines,
        "char_count": total_chars,
        "extraction_method": "pymupdf",
        "extracted_at": datetime.now(timezone.utc).isoformat(),
        "pages_jsonl": str(PAGES_JSONL),
        "full_text": str(FULL_TXT),
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(
        f"Extracted {page_count} pages, {total_lines} nonempty lines, "
        f"{total_chars} chars → {EXTRACT_DIR}"
    )
    return manifest


def _load_pages() -> tuple[dict, list[dict]]:
    if not MANIFEST.is_file() or not PAGES_JSONL.is_file():
        raise SystemExit("Run extraction first (missing scripts/tmp_bates_ocr/manifest.json)")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    pages = []
    with PAGES_JSONL.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                pages.append(json.loads(line))
    return manifest, pages


def _upsert_parent(db: sqlite3.Connection, manifest: dict, pages: list[dict]) -> int:
    """Create or replace parent guideline; return object id.

    Parent holds full searchable text. Every line (incl. blanks) lives in linked
    page-batch ``reference`` objects so the Knowledge Library stays usable.
    """
    line_count = sum(
        1 for p in pages for ln in p["lines"] if not ln.get("blank")
    )
    line_count_all = sum(len(p["lines"]) for p in pages)
    # Compact page index (offsets into full text) for navigation — not a second line dump.
    page_index = [
        {
            "page": p["page"],
            "char_count": p["char_count"],
            "line_count": p["line_count"],
            "line_count_all": p["line_count_all"],
        }
        for p in pages
    ]

    full_text = FULL_TXT.read_text(encoding="utf-8") if FULL_TXT.is_file() else ""
    tags = [
        SOURCE_LABEL,
        "Bates",
        WORK_TITLE,
        "physical examination",
        "history taking",
        "ocr",
    ]
    body = {
        "imported_text": full_text,
        "extraction_method": manifest.get("extraction_method", "pymupdf"),
        "page_count": manifest["page_count"],
        "empty_pages": manifest.get("empty_pages", 0),
        "line_count": line_count,
        "line_count_all": line_count_all,
        "char_count": manifest.get("char_count", len(full_text)),
        "source_label": SOURCE_LABEL,
        "work": WORK_TITLE,
        "page_index": page_index,
        "lines_location": "Linked reference objects (slug bates-ocr-pages-*); body.lines on each batch.",
        "pages_per_batch": PAGES_PER_BATCH,
        "supersedes_object_id": OLD_OBJECT_ID,
        "import_kind": "bates_ocr_full",
    }
    summary = (
        f"{SOURCE_LABEL}: full extract of {WORK_TITLE}. "
        f"{manifest['page_count']} pages, {line_count} nonempty lines "
        f"({line_count_all} incl. blanks), "
        f"{manifest.get('char_count', 0)} characters via pymupdf. "
        f"Supersedes truncated Knowledge Library object #{OLD_OBJECT_ID}."
    )
    title = f"{SOURCE_LABEL} — {WORK_TITLE}"

    existing = db.execute(
        "SELECT id FROM gi_knowledge_object WHERE slug = ?", (PARENT_SLUG,)
    ).fetchone()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    if existing:
        oid = existing["id"]
        db.execute(
            """
            UPDATE gi_knowledge_object
            SET title = ?, object_type = 'guideline', status = 'published',
                summary = ?, body_json = ?, tags_json = ?,
                stable_id = ?, version_no = COALESCE(version_no, 1) + 1,
                supersedes_id = ?, published_at = COALESCE(published_at, ?),
                updated_at = ?,
                provenance_json = ?
            WHERE id = ?
            """,
            (
                title,
                summary,
                json.dumps(body, ensure_ascii=False),
                json.dumps(tags, ensure_ascii=False),
                PARENT_SLUG,
                OLD_OBJECT_ID,
                now,
                now,
                json.dumps(
                    {
                        "source": SOURCE_LABEL,
                        "work": WORK_TITLE,
                        "method": "pymupdf",
                        "pdf": manifest.get("pdf_path"),
                    },
                    ensure_ascii=False,
                ),
                oid,
            ),
        )
        print(f"Updated parent guideline id={oid} slug={PARENT_SLUG}")
    else:
        cur = db.execute(
            """
            INSERT INTO gi_knowledge_object
            (slug, title, object_type, status, specialty, summary, body_json, tags_json,
             stable_id, version_no, supersedes_id, published_at, updated_at, provenance_json)
            VALUES (?, ?, 'guideline', 'published', 'gastroenterology', ?, ?, ?,
                    ?, 2, ?, ?, ?, ?)
            """,
            (
                PARENT_SLUG,
                title,
                summary,
                json.dumps(body, ensure_ascii=False),
                json.dumps(tags, ensure_ascii=False),
                PARENT_SLUG,
                OLD_OBJECT_ID,
                now,
                now,
                json.dumps(
                    {
                        "source": SOURCE_LABEL,
                        "work": WORK_TITLE,
                        "method": "pymupdf",
                        "pdf": manifest.get("pdf_path"),
                    },
                    ensure_ascii=False,
                ),
            ),
        )
        oid = cur.lastrowid
        print(f"Created parent guideline id={oid} slug={PARENT_SLUG}")
    db.commit()
    return oid


def _clear_prior_batches(db: sqlite3.Connection, parent_id: int) -> int:
    """Remove previous Bates OCR page-batch objects linked to parent (re-import safe)."""
    rows = db.execute(
        """
        SELECT o.id FROM gi_knowledge_object o
        WHERE o.slug LIKE 'bates-ocr-pages-%'
           OR (
             o.object_type = 'reference'
             AND o.id IN (
               SELECT target_id FROM gi_knowledge_link
               WHERE source_id = ? AND link_type = 'contains_chunk'
             )
           )
        """,
        (parent_id,),
    ).fetchall()
    ids = [r["id"] for r in rows]
    if not ids:
        return 0
    for oid in ids:
        db.execute("DELETE FROM gi_knowledge_link WHERE source_id = ? OR target_id = ?", (oid, oid))
        db.execute("DELETE FROM gi_knowledge_activation WHERE object_id = ?", (oid,))
        db.execute("DELETE FROM gi_knowledge_provenance WHERE object_id = ?", (oid,))
        db.execute("DELETE FROM gi_knowledge_object WHERE id = ?", (oid,))
    db.commit()
    print(f"Removed {len(ids)} prior Bates OCR batch object(s)")
    return len(ids)


def _create_batches(db: sqlite3.Connection, parent_id: int, pages: list[dict], manifest: dict) -> list[int]:
    batch_ids: list[int] = []
    tags = [SOURCE_LABEL, "Bates", "ocr-page-batch", WORK_TITLE]
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    n_pages = len(pages)
    for start in range(0, n_pages, PAGES_PER_BATCH):
        chunk = pages[start : start + PAGES_PER_BATCH]
        p_from = chunk[0]["page"]
        p_to = chunk[-1]["page"]
        slug = f"bates-ocr-pages-{p_from:04d}-{p_to:04d}"
        lines = []
        texts = []
        for p in chunk:
            texts.append(f"===== PAGE {p['page']} =====\n{p['text']}")
            for ln in p["lines"]:
                # Upload every line including blanks (preserve layout); flag blanks.
                lines.append(
                    {
                        "p": p["page"],
                        "n": ln["n"],
                        "t": ln["t"],
                        "blank": bool(ln.get("blank")),
                    }
                )
        imported = "\n\n".join(texts)
        nonempty = sum(1 for ln in lines if not ln["blank"])
        body = {
            "imported_text": imported,
            "extraction_method": "pymupdf",
            "page_from": p_from,
            "page_to": p_to,
            "page_count": len(chunk),
            "line_count": nonempty,
            "line_count_all": len(lines),
            "source_label": SOURCE_LABEL,
            "work": WORK_TITLE,
            "parent_slug": PARENT_SLUG,
            "lines": lines,
            "import_kind": "bates_ocr_page_batch",
        }
        title = f"{SOURCE_LABEL} pages {p_from}–{p_to}"
        summary = (
            f"{SOURCE_LABEL} line-level chunk for {WORK_TITLE}, "
            f"pages {p_from}–{p_to}: {nonempty} nonempty / {len(lines)} total lines."
        )
        cur = db.execute(
            """
            INSERT INTO gi_knowledge_object
            (slug, title, object_type, status, specialty, summary, body_json, tags_json,
             stable_id, version_no, published_at, updated_at, provenance_json)
            VALUES (?, ?, 'reference', 'published', 'gastroenterology', ?, ?, ?,
                    ?, 1, ?, ?, ?)
            """,
            (
                slug,
                title,
                summary,
                json.dumps(body, ensure_ascii=False),
                json.dumps(tags, ensure_ascii=False),
                slug,
                now,
                now,
                json.dumps(
                    {"source": SOURCE_LABEL, "parent_slug": PARENT_SLUG, "pages": [p_from, p_to]},
                    ensure_ascii=False,
                ),
            ),
        )
        bid = cur.lastrowid
        batch_ids.append(bid)
        db.execute(
            """
            INSERT INTO gi_knowledge_link (source_id, target_id, link_type, metadata_json)
            VALUES (?, ?, 'contains_chunk', ?)
            """,
            (
                parent_id,
                bid,
                json.dumps({"page_from": p_from, "page_to": p_to}, ensure_ascii=False),
            ),
        )
        if len(batch_ids) % 20 == 0:
            db.commit()
            print(f"  batches created: {len(batch_ids)}", flush=True)
    db.commit()
    print(f"Created {len(batch_ids)} page-batch reference objects")
    return batch_ids


def _supersede_old(db: sqlite3.Connection, new_id: int) -> None:
    old = db.execute(
        "SELECT id, status, summary FROM gi_knowledge_object WHERE id = ?",
        (OLD_OBJECT_ID,),
    ).fetchone()
    if not old:
        print(f"No prior object #{OLD_OBJECT_ID} to supersede")
        return
    note = (
        f" [SUPERSEDED by Knowledge object #{new_id} ({PARENT_SLUG}) — "
        f"full Bates OCR import with line-level chunks. Truncated 120k-char dump retained for audit.]"
    )
    summary = (old["summary"] or "") + note
    db.execute(
        """
        UPDATE gi_knowledge_object
        SET status = 'archived',
            summary = ?,
            updated_at = datetime('now')
        WHERE id = ?
        """,
        (summary, OLD_OBJECT_ID),
    )
    db.commit()
    print(f"Archived old Bates dump id={OLD_OBJECT_ID} (status=archived); superseded by {new_id}")


def _add_provenance_and_job(
    db: sqlite3.Connection, parent_id: int, batch_ids: list[int], manifest: dict
) -> int:
    pdf_name = Path(manifest.get("pdf_path") or "BATES OCR.pdf").name
    summary = {
        "object_id": parent_id,
        "slug": PARENT_SLUG,
        "title": f"{SOURCE_LABEL} — {WORK_TITLE}",
        "object_type": "guideline",
        "status": "published",
        "filename": pdf_name,
        "extraction_method": "pymupdf",
        "char_count": manifest.get("char_count", 0),
        "page_count": manifest.get("page_count", 0),
        "line_count": manifest.get("line_count_nonempty", 0),
        "batch_count": len(batch_ids),
        "batch_ids_sample": batch_ids[:5],
        "message": (
            f"Bates OCR imported: parent #{parent_id}, {len(batch_ids)} page batches, "
            f"{manifest.get('line_count_nonempty', 0)} nonempty lines."
        ),
        "source_file_deleted": False,
        "import_script": "scripts/import_bates_ocr.py",
    }
    cur = db.execute(
        """
        INSERT INTO gi_import_job (job_type, filename, created_by, status, summary_json, finished_at)
        VALUES ('knowledge_import', ?, NULL, 'done', ?, datetime('now'))
        """,
        (pdf_name, json.dumps(summary, ensure_ascii=False)),
    )
    job_id = cur.lastrowid
    notes = (
        f"{SOURCE_LABEL} full import via scripts/import_bates_ocr.py. "
        f"pymupdf extract: {manifest.get('page_count')} pages, "
        f"{manifest.get('line_count_nonempty')} nonempty lines, "
        f"{manifest.get('char_count')} chars. "
        f"{len(batch_ids)} reference batches linked. Supersedes #{OLD_OBJECT_ID}."
    )
    db.execute(
        """
        INSERT INTO gi_knowledge_provenance
        (object_id, source_type, source_filename, import_job_id, author, grade_level, notes)
        VALUES (?, 'pdf_import', ?, ?, 'Bates OCR import script', '', ?)
        """,
        (parent_id, pdf_name, job_id, notes),
    )
    for bid in batch_ids:
        db.execute(
            """
            INSERT INTO gi_knowledge_provenance
            (object_id, source_type, source_filename, import_job_id, author, grade_level, notes)
            VALUES (?, 'pdf_import', ?, ?, 'Bates OCR import script', '', ?)
            """,
            (
                bid,
                pdf_name,
                job_id,
                f"Page-batch chunk of {SOURCE_LABEL}; parent object #{parent_id}.",
            ),
        )
    db.commit()
    print(f"Import job id={job_id}; provenance attached to parent + batches")
    return job_id


def import_into_db(manifest: dict | None = None) -> dict:
    if manifest is None:
        manifest, pages = _load_pages()
    else:
        _, pages = _load_pages()

    if not DB_PATH.is_file():
        raise SystemExit(f"Database not found: {DB_PATH}")

    db = _connect()
    try:
        parent_id = _upsert_parent(db, manifest, pages)
        _clear_prior_batches(db, parent_id)
        batch_ids = _create_batches(db, parent_id, pages, manifest)
        _supersede_old(db, parent_id)
        job_id = _add_provenance_and_job(db, parent_id, batch_ids, manifest)

        # Smoke counts
        parent = db.execute(
            "SELECT id, slug, status, length(body_json) AS blen FROM gi_knowledge_object WHERE id = ?",
            (parent_id,),
        ).fetchone()
        body = json.loads(
            db.execute(
                "SELECT body_json FROM gi_knowledge_object WHERE id = ?", (parent_id,)
            ).fetchone()["body_json"]
        )
        batch_count = db.execute(
            "SELECT COUNT(*) AS c FROM gi_knowledge_object WHERE slug LIKE 'bates-ocr-pages-%'"
        ).fetchone()["c"]
        old = db.execute(
            "SELECT id, status FROM gi_knowledge_object WHERE id = ?", (OLD_OBJECT_ID,)
        ).fetchone()

        result = {
            "parent_id": parent_id,
            "parent_slug": PARENT_SLUG,
            "parent_body_bytes": parent["blen"],
            "parent_line_count": body.get("line_count"),
            "parent_line_count_all": body.get("line_count_all"),
            "parent_text_chars": len(body.get("imported_text") or ""),
            "batch_count": batch_count,
            "batch_ids": batch_ids,
            "page_count": manifest["page_count"],
            "line_count_nonempty": manifest.get("line_count_nonempty"),
            "job_id": job_id,
            "old_977_status": dict(old) if old else None,
            "ui": {
                "library": "/knowledge-library",
                "parent": f"/knowledge-library/{parent_id}",
                "guidelines": "/knowledge-library/guidelines",
                "search": "/knowledge-library?q=Bates+OCR",
                "filter_batches": "/knowledge-library?q=bates-ocr-pages&object_type=reference",
            },
        }
        (EXTRACT_DIR / "import_result.json").write_text(
            json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        print(json.dumps({k: v for k, v in result.items() if k != "batch_ids"}, indent=2))
        return result
    finally:
        db.close()


def main(argv: list[str] | None = None) -> int:
    global PAGES_PER_BATCH

    parser = argparse.ArgumentParser(description="Import Bates OCR into Knowledge Library")
    parser.add_argument("--pdf", type=Path, default=DEFAULT_PDF, help="Path to BATES OCR.pdf")
    parser.add_argument("--extract-only", action="store_true")
    parser.add_argument("--import-only", action="store_true")
    parser.add_argument("--pages-per-batch", type=int, default=PAGES_PER_BATCH)
    args = parser.parse_args(argv)

    PAGES_PER_BATCH = max(1, args.pages_per_batch)

    if not args.import_only:
        print(f"Extracting: {args.pdf}")
        extract_pdf(args.pdf)
    if not args.extract_only:
        print(f"Importing into {DB_PATH}")
        import_into_db()
    return 0


if __name__ == "__main__":
    sys.exit(main())
