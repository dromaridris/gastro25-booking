"""User mention API and HOD account management."""

from flask import flash, jsonify, redirect, render_template, request, session, url_for

from gi_platform import user_mention_service

ACCOUNT_MANAGER_ROLES = ('admin', 'hod')


def register_user_api_routes(app, *, get_db, login_required, roles_required=None):
    roles_required = roles_required or (lambda *a, **k: lambda f: f)

    @app.route('/api/users/mentions')
    @login_required
    def api_user_mentions():
        db = get_db()
        q = request.args.get('q', '')
        users = user_mention_service.list_mentionable_users(db, q=q, limit=25)
        return jsonify(users)

    @app.route('/api/notifications')
    @login_required
    def api_notifications():
        db = get_db()
        from gi_platform import notification_service
        items = notification_service.list_unread(db, session.get('user_id') or 0, limit=15)
        return jsonify([
            {
                'id': n['id'],
                'title': n['title'],
                'body': n['body'] or '',
                'link_url': n['link_url'] or '',
                'created_at': n['created_at'],
            }
            for n in items
        ])

    @app.route('/api/notifications/<int:notification_id>/read', methods=['POST'])
    @login_required
    def api_notification_read(notification_id):
        from gi_platform import notification_service
        notification_service.mark_read(get_db(), notification_id, session.get('user_id') or 0)
        return jsonify({'ok': True})

    @app.route('/notifications')
    @login_required
    def gi_notifications():
        db = get_db()
        from gi_platform import notification_service
        items = notification_service.list_all(db, session.get('user_id') or 0, limit=100)
        return render_template('gi/notifications.html', notifications=items)

    @app.route('/admin/user-accounts', methods=['GET', 'POST'])
    @login_required
    @roles_required(*ACCOUNT_MANAGER_ROLES)
    def gi_user_accounts():
        db = get_db()
        from gi_platform import nav_permissions as navperm

        if request.method == 'POST':
            user_id = request.form.get('user_id', type=int)
            new_role = (request.form.get('role') or '').strip()
            expires_raw = (request.form.get('role_expires_at') or '').strip()
            clear_expiry = bool(request.form.get('clear_expiry'))

            if not user_id:
                flash('User not specified.', 'error')
                return redirect(url_for('gi_user_accounts'))

            target = db.execute('SELECT * FROM user WHERE id = ?', (user_id,)).fetchone()
            if not target:
                flash('User not found.', 'error')
                return redirect(url_for('gi_user_accounts'))

            from app import ALL_ROLES
            if new_role and new_role in ALL_ROLES:
                db.execute('UPDATE user SET role = ? WHERE id = ?', (new_role, user_id))
                flash(f"Role updated to {new_role} for {target['username']}.", 'success')
            elif new_role:
                flash('Invalid role selected.', 'error')
                return redirect(url_for('gi_user_accounts'))

            if clear_expiry:
                db.execute('UPDATE user SET role_expires_at = NULL WHERE id = ?', (user_id,))
                flash(f'Expiry cleared for {target["username"]}.', 'success')
            elif expires_raw:
                db.execute(
                    'UPDATE user SET role_expires_at = ? WHERE id = ?',
                    (f'{expires_raw}T23:59:59', user_id),
                )
                flash(f'Access expiry set to {expires_raw} for {target["username"]}.', 'success')

            db.commit()
            return redirect(url_for('gi_user_accounts', q=request.form.get('search_q', '')))

        q = (request.args.get('q') or '').strip()
        users = db.execute(
            """
            SELECT id, username, full_name, role, is_approved, created_at, role_expires_at
            FROM user
            WHERE is_approved = 1
            """
            + (' AND (full_name LIKE ? COLLATE NOCASE OR username LIKE ? COLLATE NOCASE)' if q else '')
            + " ORDER BY full_name",
            ([f'%{q}%', f'%{q}%'] if q else []),
        ).fetchall()
        from app import ALL_ROLES, ROLE_LABELS
        return render_template(
            'gi/user_accounts.html',
            users=users,
            all_roles=ALL_ROLES,
            role_labels=ROLE_LABELS,
            q=q,
            module_intro=navperm.intro('user_accounts'),
        )
