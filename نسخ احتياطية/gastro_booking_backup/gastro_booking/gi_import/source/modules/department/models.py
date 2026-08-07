"""
Department is the unit that department_id (on every other table) points
to. It's deliberately a plain db.Model, not a BaseModel subclass — a
department_id column pointing to itself would be circular and meaningless.

Today: exactly one row exists (Gastroenterology). Adding a second
department/hospital later is INSERT INTO departments, not a migration.
"""

from datetime import datetime, timezone

from app.extensions import db


class Department(db.Model):
    __tablename__ = "departments"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, unique=True)
    code = db.Column(db.String(20), nullable=False, unique=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def __repr__(self):
        return f"<Department {self.code}: {self.name}>"
