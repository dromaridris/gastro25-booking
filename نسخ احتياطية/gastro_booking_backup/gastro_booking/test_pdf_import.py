"""PDF/text extraction and knowledge import pipeline tests."""

import os
import sqlite3
import tempfile

from gi_platform.pdf_extract_service import extract_document_text
from gi_platform.import_service import create_job, parse_summary

# Plain text
fd, txt_path = tempfile.mkstemp(suffix='.txt')
os.close(fd)
with open(txt_path, 'w', encoding='utf-8') as fh:
    fh.write('BSG guideline excerpt: upper GI bleeding management.\nSecond paragraph.')
result = extract_document_text(txt_path)
assert result['method'] == 'txt'
assert 'upper GI bleeding' in result['text']
assert result['char_count'] > 20

# Minimal PDF (pypdf) — build inline if pypdf available
try:
    from pypdf import PdfWriter
    from pypdf.generic import NameObject, DictionaryObject, ArrayObject, NumberObject

    pdf_path = txt_path.replace('.txt', '.pdf')
    writer = PdfWriter()
    page = writer.add_blank_page(width=200, height=200)
    # pypdf blank pages have no text — method may be none unless OCR; still exercises path
    with open(pdf_path, 'wb') as pf:
        writer.write(pf)
    pdf_result = extract_document_text(pdf_path)
    assert pdf_result['method'] in ('pypdf', 'none', 'ocr')
except ImportError:
    pdf_path = None

# Import job with text file
fd2, db_path = tempfile.mkstemp(suffix='.db')
os.close(fd2)
db = sqlite3.connect(db_path)
db.row_factory = sqlite3.Row
db.executescript(
    """
    CREATE TABLE gi_import_job (
        id INTEGER PRIMARY KEY AUTOINCREMENT, job_type TEXT, filename TEXT,
        status TEXT, summary_json TEXT, error_text TEXT, created_by INT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP, finished_at TEXT
    );
    CREATE TABLE gi_knowledge_object (
        id INTEGER PRIMARY KEY AUTOINCREMENT, slug TEXT UNIQUE, title TEXT,
        object_type TEXT, status TEXT, summary TEXT, body_json TEXT,
        created_by INT, created_at TEXT, updated_at TEXT, published_at TEXT
    );
    CREATE TABLE gi_knowledge_provenance (
        id INTEGER PRIMARY KEY AUTOINCREMENT, object_id INT, source_type TEXT,
        source_filename TEXT, import_job_id INT, author TEXT, grade_level TEXT,
        notes TEXT, created_at TEXT
    );
    CREATE TABLE gi_audit_event (
        id INTEGER PRIMARY KEY AUTOINCREMENT, action TEXT, entity_type TEXT,
        entity_id INT, user_id INT, details_json TEXT, created_at TEXT
    );
    """
)
job_id, summary = create_job(
    db, job_type='knowledge_import', filename='ugib_guideline.txt',
    created_by=1, stored_path=txt_path,
)
assert summary.get('object_id')
assert summary.get('extraction_method') == 'txt'
assert summary.get('char_count', 0) > 0
obj = db.execute('SELECT body_json FROM gi_knowledge_object WHERE id = ?', (summary['object_id'],)).fetchone()
import json
body = json.loads(obj['body_json'])
assert 'imported_text' in body
assert 'upper GI bleeding' in body['imported_text']

print('PDF/OCR import tests passed')
