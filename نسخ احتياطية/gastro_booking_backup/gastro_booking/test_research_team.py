"""Research team management for HOD."""

import json
import os
import sqlite3
import tempfile

from gi_platform.research_service import (
    assign_hod_project,
    get_registry,
    remove_team_member,
    team_user_ids,
    update_registry_team,
)

fd, path = tempfile.mkstemp(suffix='.db')
os.close(fd)
db = sqlite3.connect(path)
db.row_factory = sqlite3.Row
db.executescript(
    """
    CREATE TABLE gi_research_registry (
        id INTEGER PRIMARY KEY, code TEXT, title TEXT, description TEXT,
        lead_user_id INT, team_user_ids TEXT, assigned_by_hod_id INT,
        hod_status TEXT, status TEXT, created_by INT
    );
    CREATE TABLE user (id INTEGER PRIMARY KEY, username TEXT, full_name TEXT, is_approved INT);
    """
)
db.execute("INSERT INTO user (id, username, full_name, is_approved) VALUES (1,'lead','Lead',1),(2,'a','A',1),(3,'b','B',1)")
rid = assign_hod_project(db, code='X', title='Test', lead_user_id=1, team_user_ids=[2, 3], assigned_by_hod_id=1)
assert team_user_ids(get_registry(db, rid)) == [2, 3]

update_registry_team(db, rid, lead_user_id=2, team_user_ids=[3])
reg = get_registry(db, rid)
assert reg['lead_user_id'] == 2
assert team_user_ids(reg) == [3]

remove_team_member(db, rid, 3)
assert team_user_ids(get_registry(db, rid)) == []

assert not remove_team_member(db, rid, 2)
print('Research team management tests passed')
