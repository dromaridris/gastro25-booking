"""Ward module SQLite schema — additive only, never alters ERCP tables."""


def init_ward_schema(dbconn) -> None:
    dbconn.executescript(
        """
        CREATE TABLE IF NOT EXISTS ward (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            slug TEXT NOT NULL UNIQUE,
            regular_bed_count INTEGER NOT NULL DEFAULT 30,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS ward_bed (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ward_id INTEGER NOT NULL REFERENCES ward(id),
            label TEXT NOT NULL,
            bed_kind TEXT NOT NULL DEFAULT 'regular',
            sort_order INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'available',
            is_active INTEGER NOT NULL DEFAULT 1,
            UNIQUE (ward_id, label)
        );

        CREATE TABLE IF NOT EXISTS ward_patient (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mrn TEXT,
            patient_name TEXT NOT NULL,
            age TEXT,
            gender TEXT,
            referral TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS ward_admission (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ward_patient_id INTEGER NOT NULL REFERENCES ward_patient(id),
            bed_id INTEGER NOT NULL REFERENCES ward_bed(id),
            admitted_at TEXT NOT NULL DEFAULT (datetime('now')),
            discharged_at TEXT,
            admitted_by_user_id INTEGER REFERENCES user(id),
            notes TEXT,
            is_active INTEGER NOT NULL DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS ward_movement (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ward_patient_id INTEGER NOT NULL REFERENCES ward_patient(id),
            from_bed_id INTEGER REFERENCES ward_bed(id),
            to_bed_id INTEGER REFERENCES ward_bed(id),
            movement_type TEXT NOT NULL,
            notes TEXT,
            moved_at TEXT NOT NULL DEFAULT (datetime('now')),
            moved_by_user_id INTEGER REFERENCES user(id)
        );

        CREATE TABLE IF NOT EXISTS ward_clinical_note (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ward_patient_id INTEGER NOT NULL REFERENCES ward_patient(id),
            note_type TEXT NOT NULL,
            body TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            created_by_user_id INTEGER REFERENCES user(id)
        );
        """
    )
    _seed_default_ward(dbconn)
    dbconn.commit()


def _seed_default_ward(dbconn) -> None:
    row = dbconn.execute("SELECT id FROM ward WHERE slug = 'gastro-25'").fetchone()
    if row:
        ward_id = row['id']
    else:
        cur = dbconn.execute(
            "INSERT INTO ward (name, slug, regular_bed_count) VALUES (?, ?, ?)",
            ('Gastroenterology Ward 25', 'gastro-25', 30),
        )
        ward_id = cur.lastrowid
        for n in range(1, 31):
            dbconn.execute(
                "INSERT OR IGNORE INTO ward_bed (ward_id, label, bed_kind, sort_order, status) VALUES (?, ?, 'regular', ?, 'available')",
                (ward_id, f'Bed {n}', n),
            )
