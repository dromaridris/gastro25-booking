"""Admin permission grants — roster manager assignments."""

from flask import flash, redirect, render_template, request, session, url_for

from gi_platform.constants import ROSTER_PERMISSIONS, ROSTER_PERMISSION_LABELS
from gi_platform import permission_service

ADMIN_ROLES = ('admin', 'specialist', 'hod')


def register_permission_routes(app, *, get_db, login_required, roles_required):
    @app.route('/admin/permissions', methods=['GET', 'POST'])
    @login_required
    @roles_required(*ADMIN_ROLES)
    def gi_admin_permissions():
        db = get_db()
        users = db.execute(
            "SELECT id, full_name, username, role FROM user WHERE is_approved = 1 ORDER BY full_name"
        ).fetchall()
        grants = permission_service.list_all_grants(db)

        if request.method == 'POST':
            action = request.form.get('action')
            user_id = request.form.get('user_id', type=int)
            perm = request.form.get('permission_code', '')
            if action == 'grant' and user_id and perm in ROSTER_PERMISSIONS:
                permission_service.grant_permission(
                    db, user_id, perm, session.get('user_id'),
                )
                flash('Permission granted.', 'success')
            elif action == 'revoke' and user_id and perm:
                permission_service.revoke_permission(db, user_id, perm)
                flash('Permission revoked.', 'success')
            return redirect(url_for('gi_admin_permissions'))

        user_perms = {u['id']: permission_service.list_user_permissions(db, u['id']) for u in users}
        return render_template(
            'gi/admin_permissions.html',
            users=users, grants=grants, user_perms=user_perms,
            permissions=ROSTER_PERMISSIONS,
            permission_labels=ROSTER_PERMISSION_LABELS,
        )
