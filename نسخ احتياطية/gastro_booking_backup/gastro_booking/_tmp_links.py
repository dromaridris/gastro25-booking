import sqlite3
c = sqlite3.connect("gastro_booking.db")
print("link cols:", [x[1] for x in c.execute("PRAGMA table_info(gi_knowledge_link)")])
print("links:", c.execute("SELECT * FROM gi_knowledge_link").fetchall())
for r in c.execute(
    "SELECT id, slug, title, status, LENGTH(body_json) AS blen FROM gi_knowledge_object WHERE object_type='guideline'"
):
    print("guideline:", dict(zip(["id","slug","title","status","blen"], r)))
