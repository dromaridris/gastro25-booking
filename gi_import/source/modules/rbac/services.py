"""
RBAC service layer.

Three kinds of functions here:
1. Read helpers (list_roles, list_permissions, get_role_by_code) used by
   forms/routes that need to populate dropdowns or validate a role code.
2. Admin utilities (assign_permission, revoke_permission, create_role,
   deactivate_role) — callable from a Python shell, a script, or (Sprint
   1B) a web UI. These are the "admin utilities" role/permission
   management is done through for now.
3. seed_initial_rbac() — idempotent seeding from seed_data.py, safe to
   re-run (upserts by code, never overwrites a permission grant that was
   changed by hand after seeding).
"""

from app.core.exceptions import NotFoundError, ValidationError
from app.extensions import db
from app.modules.rbac.models import Permission, Role, RolePermission
from app.modules.rbac import seed_data


def list_roles(include_inactive: bool = False):
    query = Role.query
    if not include_inactive:
        query = query.filter_by(is_active=True)
    return query.order_by(Role.name.asc()).all()


def list_permissions():
    return Permission.query.order_by(Permission.category.asc(), Permission.code.asc()).all()


def get_role_by_code(code: str) -> Role:
    role = Role.query.filter_by(code=code).first()
    if role is None:
        raise NotFoundError(f"No role with code '{code}'")
    return role


def get_permission_by_code(code: str) -> Permission:
    permission = Permission.query.filter_by(code=code).first()
    if permission is None:
        raise NotFoundError(f"No permission with code '{code}'")
    return permission


def create_role(code: str, name: str, description: str = None, is_system: bool = False) -> Role:
    if Role.query.filter_by(code=code).first() is not None:
        raise ValidationError(f"Role code '{code}' already exists.")
    role = Role(code=code, name=name, description=description, is_system=is_system)
    db.session.add(role)
    db.session.commit()
    return role


def create_permission(code: str, name: str, description: str = None, category: str = None) -> Permission:
    if Permission.query.filter_by(code=code).first() is not None:
        raise ValidationError(f"Permission code '{code}' already exists.")
    permission = Permission(code=code, name=name, description=description, category=category)
    db.session.add(permission)
    db.session.commit()
    return permission


def assign_permission(role: Role, permission: Permission, granted_by_id: int = None) -> RolePermission:
    existing = RolePermission.query.filter_by(role_id=role.id, permission_id=permission.id).first()
    if existing is not None:
        return existing  # idempotent — assigning an already-granted permission is a no-op
    link = RolePermission(role_id=role.id, permission_id=permission.id, granted_by_id=granted_by_id)
    db.session.add(link)
    db.session.commit()
    return link


def revoke_permission(role: Role, permission: Permission) -> None:
    link = RolePermission.query.filter_by(role_id=role.id, permission_id=permission.id).first()
    if link is not None:
        db.session.delete(link)
        db.session.commit()


def deactivate_role(role: Role) -> Role:
    """Roles are retired via is_active, never deleted — deleting a role
    row that existing users still reference via role_id would break
    those users' FK integrity and their historical audit trail."""
    role.is_active = False
    db.session.commit()
    return role


def sync_role_catalog() -> list[str]:
    """
    Upsert role definitions from seed_data.ROLES so dropdowns (Change Role,
    invitations) always include newer roles such as postgraduate_trainee
    even when the database was created before they existed.
    """
    updated: list[str] = []
    for role_data in seed_data.ROLES:
        existing = Role.query.filter_by(code=role_data["code"]).first()
        if existing is None:
            db.session.add(Role(**role_data))
            updated.append(role_data["code"])
        else:
            existing.name = role_data["name"]
            if role_data.get("description") is not None:
                existing.description = role_data["description"]
            if existing.is_active is False and role_data.get("is_system"):
                existing.is_active = True
    db.session.commit()
    return updated


def migrate_legacy_training_roles() -> None:
    """
    Older demo databases used code ``trainee`` or display names like
    ``House Officer / Intern``. Normalise those rows so Change Role always
    offers ``postgraduate_trainee`` as a distinct option.
    """
    from app.modules.auth.models import User

    legacy_trainee = Role.query.filter_by(code="trainee").first()
    pg_trainee = Role.query.filter_by(code="postgraduate_trainee").first()

    if legacy_trainee is not None and pg_trainee is None:
        legacy_trainee.code = "postgraduate_trainee"
        legacy_trainee.name = "Postgraduate Trainee"
        legacy_trainee.is_active = True
        pg_trainee = legacy_trainee
    elif legacy_trainee is not None and pg_trainee is not None:
        User.query.filter_by(role_id=legacy_trainee.id).update(
            {User.role_id: pg_trainee.id},
            synchronize_session=False,
        )
        legacy_trainee.is_active = False

    pg_trainee = Role.query.filter_by(code="postgraduate_trainee").first()
    if pg_trainee is None:
        spec = next(r for r in seed_data.ROLES if r["code"] == "postgraduate_trainee")
        pg_trainee = Role(**spec)
        db.session.add(pg_trainee)
    else:
        pg_trainee.name = "Postgraduate Trainee"
        pg_trainee.is_active = True

    house_officer = Role.query.filter_by(code="house_officer").first()
    if house_officer is not None:
        house_officer.name = "House Officer"

    db.session.commit()


def ensure_role_catalog() -> None:
    """Idempotent — safe on every app start and before role dropdowns."""
    sync_role_catalog()
    migrate_legacy_training_roles()


def role_choices_for_forms() -> list[tuple[str, str]]:
    """
    Assignable roles for user-management dropdowns. Built from seed_data.ROLES
    so Postgraduate Trainee is never missing even on stale demo databases.
    """
    ensure_role_catalog()

    db_by_code = {role.code: role for role in list_roles(include_inactive=False)}
    training_codes = {
        "postgraduate_trainee",
        "house_officer",
        "senior_registrar",
        "visiting_trainee",
    }

    choices: list[tuple[str, str]] = []
    seen: set[str] = set()
    for role_data in seed_data.ROLES:
        code = role_data["code"]
        if code == seed_data.SUPERUSER_ROLE_CODE:
            continue
        label = db_by_code[code].name if code in db_by_code else role_data["name"]
        choices.append((code, label))
        seen.add(code)

    for role in list_roles(include_inactive=False):
        if role.code in seen or role.code == seed_data.SUPERUSER_ROLE_CODE:
            continue
        choices.append((role.code, role.name))

    choices.sort(
        key=lambda item: (
            0 if item[0] in training_codes else 1,
            item[1].lower(),
        )
    )
    return choices


def seed_initial_rbac() -> dict:
    """
    Idempotent. Safe to run on every deploy / every `make seed`:
    - Creates any permission from seed_data.PERMISSIONS that doesn't
      already exist by code. Never modifies an existing one (so a
      description you've hand-edited in the DB survives a re-seed).
    - Creates any role from seed_data.ROLES that doesn't already exist
      by code. Same non-destructive rule.
    - Grants any (role, permission) pair from seed_data.ROLE_PERMISSIONS
      that isn't already granted. Never revokes a grant that was removed
      from seed_data.py after the fact — that would silently undo an
      admin's deliberate change. Removing a default grant going forward
      is a revoke_permission() call, not an edit to this file.

    Returns a summary dict for the calling script to print.
    """
    created_permissions = []
    for perm_data in seed_data.PERMISSIONS:
        if Permission.query.filter_by(code=perm_data["code"]).first() is None:
            db.session.add(Permission(**perm_data))
            created_permissions.append(perm_data["code"])
    db.session.commit()

    created_roles = []
    for role_data in seed_data.ROLES:
        existing = Role.query.filter_by(code=role_data["code"]).first()
        if existing is None:
            db.session.add(Role(**role_data))
            created_roles.append(role_data["code"])
        else:
            existing.name = role_data["name"]
            if role_data.get("description") is not None:
                existing.description = role_data["description"]
    db.session.commit()

    granted = []
    for role_code, permission_codes in seed_data.ROLE_PERMISSIONS.items():
        role = Role.query.filter_by(code=role_code).first()
        if role is None:
            continue
        for permission_code in permission_codes:
            permission = Permission.query.filter_by(code=permission_code).first()
            if permission is None:
                continue
            existing = RolePermission.query.filter_by(
                role_id=role.id, permission_id=permission.id
            ).first()
            if existing is None:
                db.session.add(RolePermission(role_id=role.id, permission_id=permission.id))
                granted.append(f"{role_code} -> {permission_code}")
    db.session.commit()

    # Secondary defense for the Super Administrator role: grant it EVERY
    # permission that exists, not a hand-maintained list — so it stays in
    # sync automatically as new modules add new permissions, as long as
    # this seed script gets re-run. The actual access guarantee is
    # User.is_superuser (bypasses this entirely, see permission_engine.py);
    # this loop just means the role itself isn't a trap if is_superuser
    # is ever unset on an account by mistake.
    system_admin_role = Role.query.filter_by(code=seed_data.SUPERUSER_ROLE_CODE).first()
    if system_admin_role is not None:
        for permission in Permission.query.all():
            existing = RolePermission.query.filter_by(
                role_id=system_admin_role.id, permission_id=permission.id
            ).first()
            if existing is None:
                db.session.add(
                    RolePermission(role_id=system_admin_role.id, permission_id=permission.id)
                )
                granted.append(f"{seed_data.SUPERUSER_ROLE_CODE} -> {permission.code} (auto, all permissions)")
    db.session.commit()

    return {
        "created_permissions": created_permissions,
        "created_roles": created_roles,
        "granted": granted,
    }
