"""
Department service layer. Deliberately minimal for Sprint 1A: only
Gastroenterology exists, and there's no department CRUD UI yet (creating
a second department is currently a manual DB insert — see
scripts/seed_foundation.py — not a feature of this sprint). This function
exists so User Management can list departments for a dropdown without
querying the Department model directly from routes/forms.
"""

from app.modules.department.models import Department


def list_active_departments():
    return Department.query.filter_by(is_active=True).order_by(Department.name.asc()).all()
