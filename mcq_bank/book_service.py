import re


def slugify(name):
    s = re.sub(r"[^a-zA-Z0-9]+", "-", name.strip().lower()).strip("-")
    return s or "book"


def create_book(db, name, source_filename=None):
    slug = slugify(name)
    base_slug, i = slug, 2
    while db.execute("SELECT 1 FROM mcqbank_book WHERE slug = ?", (slug,)).fetchone():
        slug = f"{base_slug}-{i}"
        i += 1
    cur = db.execute(
        "INSERT INTO mcqbank_book (name, slug, source_filename) VALUES (?, ?, ?)",
        (name, slug, source_filename),
    )
    db.commit()
    return db.execute("SELECT * FROM mcqbank_book WHERE id = ?", (cur.lastrowid,)).fetchone()


def create_chapter(db, book_id, number, title, topic=None):
    db.execute(
        """INSERT INTO mcqbank_chapter (book_id, number, title, topic) VALUES (?, ?, ?, ?)
           ON CONFLICT(book_id, number) DO UPDATE SET title=excluded.title, topic=excluded.topic""",
        (book_id, number, title, topic),
    )
    db.commit()
    return db.execute(
        "SELECT * FROM mcqbank_chapter WHERE book_id = ? AND number = ?", (book_id, number)
    ).fetchone()


def list_books(db):
    return db.execute("SELECT * FROM mcqbank_book ORDER BY name").fetchall()


def get_book(db, book_id):
    return db.execute("SELECT * FROM mcqbank_book WHERE id = ?", (book_id,)).fetchone()


def list_chapters(db, book_id):
    return db.execute(
        "SELECT * FROM mcqbank_chapter WHERE book_id = ? ORDER BY number", (book_id,)
    ).fetchall()


def get_chapter(db, chapter_id):
    return db.execute("SELECT * FROM mcqbank_chapter WHERE id = ?", (chapter_id,)).fetchone()


def delete_book(db, book_id):
    db.execute("DELETE FROM mcqbank_book WHERE id = ?", (book_id,))
    db.commit()
