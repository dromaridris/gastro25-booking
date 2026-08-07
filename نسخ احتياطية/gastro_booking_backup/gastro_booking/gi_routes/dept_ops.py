"""Unit Operations routes — endoscopy department day-to-day operations."""

from flask import flash, redirect, render_template, request, session, url_for

from gi_platform import dept_ops_service as svc
from gi_platform.dept_ops_constants import (
    ALL_CONSUMABLE_CATEGORIES,
    ALL_PRIORITIES,
    ALL_ROOM_STATUSES,
    ALL_ROOM_TYPES,
    ALL_SCOPE_TYPES,
    ALL_SHIFT_TYPES,
    ANN_CATEGORIES,
    REPROCESSING_STEPS,
    STOCK_ADJUSTMENT,
    STOCK_RECEIPT,
    STOCK_USAGE,
)

VIEW_ROLES = (
    'admin', 'hod', 'consultant', 'specialist', 'nurse_manager',
    'endoscopy_staff', 'scheduler', 'staff_nurse', 'registrar',
)
MANAGE_ROLES = ('admin', 'hod', 'nurse_manager', 'endoscopy_staff')


def register_dept_ops_routes(app, *, get_db, login_required, roles_required):
    @app.route('/dept-ops/')
    @login_required
    @roles_required(*VIEW_ROLES)
    def dept_ops_home():
        db = get_db()
        svc.ensure_dept_ops_seed(db)
        ctx = svc.dashboard_context(db, user_id=session.get('user_id'))
        return render_template('gi/dept_ops/home.html', **ctx)

    @app.route('/dept-ops/rooms', methods=['GET', 'POST'])
    @login_required
    @roles_required(*VIEW_ROLES)
    def dept_ops_rooms():
        db = get_db()
        svc.ensure_dept_ops_seed(db)
        if request.method == 'POST' and session.get('role') in MANAGE_ROLES:
            action = (request.form.get('action') or '').strip()
            try:
                if action == 'create':
                    svc.create_room(
                        db,
                        name=request.form.get('name', ''),
                        room_type=request.form.get('room_type', 'general'),
                        created_by=session.get('user_id'),
                    )
                    flash('Room created.', 'success')
                elif action == 'status':
                    svc.update_room_status(
                        db,
                        room_id=request.form.get('room_id', type=int),
                        status=request.form.get('status', ''),
                        notes=request.form.get('notes', ''),
                    )
                    flash('Room status updated.', 'success')
            except ValueError as exc:
                flash(str(exc), 'error')
            return redirect(url_for('dept_ops_rooms'))
        rooms = svc.list_rooms(db)
        return render_template(
            'gi/dept_ops/rooms.html',
            rooms=rooms,
            room_types=ALL_ROOM_TYPES,
            room_statuses=ALL_ROOM_STATUSES,
            can_manage=session.get('role') in MANAGE_ROLES,
        )

    @app.route('/dept-ops/scopes', methods=['GET', 'POST'])
    @login_required
    @roles_required(*VIEW_ROLES)
    def dept_ops_scopes():
        db = get_db()
        if request.method == 'POST' and session.get('role') in MANAGE_ROLES:
            action = (request.form.get('action') or '').strip()
            try:
                if action == 'create':
                    svc.create_scope(
                        db,
                        scope_code=request.form.get('scope_code', ''),
                        scope_type=request.form.get('scope_type', 'gastroscope'),
                        model=request.form.get('model', ''),
                        serial_number=request.form.get('serial_number', ''),
                        created_by=session.get('user_id'),
                    )
                    flash('Scope registered.', 'success')
                elif action == 'status':
                    svc.update_scope_status(
                        db,
                        scope_id=request.form.get('scope_id', type=int),
                        status=request.form.get('status', ''),
                        location=request.form.get('location', ''),
                    )
                    flash('Scope status updated.', 'success')
            except ValueError as exc:
                flash(str(exc), 'error')
            return redirect(url_for('dept_ops_scopes'))
        scopes = svc.list_scopes(db)
        return render_template(
            'gi/dept_ops/scopes.html',
            scopes=scopes,
            scope_types=ALL_SCOPE_TYPES,
            can_manage=session.get('role') in MANAGE_ROLES,
        )

    @app.route('/dept-ops/scopes/<int:scope_id>')
    @login_required
    @roles_required(*VIEW_ROLES)
    def dept_ops_scope_detail(scope_id):
        db = get_db()
        scope = svc.get_scope(db, scope_id)
        if not scope:
            flash('Scope not found.', 'error')
            return redirect(url_for('dept_ops_scopes'))
        history = svc.scope_reprocessing_history(db, scope_id)
        return render_template(
            'gi/dept_ops/scope_detail.html',
            scope=scope,
            history=history,
            reprocessing_steps=REPROCESSING_STEPS,
            can_manage=session.get('role') in MANAGE_ROLES,
        )

    @app.route('/dept-ops/reprocessing', methods=['GET', 'POST'])
    @login_required
    @roles_required(*VIEW_ROLES)
    def dept_ops_reprocessing():
        db = get_db()
        if request.method == 'POST' and session.get('role') in MANAGE_ROLES:
            action = (request.form.get('action') or '').strip()
            try:
                if action == 'start':
                    svc.start_reprocessing(
                        db,
                        scope_id=request.form.get('scope_id', type=int),
                        user_id=session.get('user_id'),
                    )
                    flash('Reprocessing cycle started.', 'success')
                elif action == 'advance':
                    svc.advance_reprocessing_step(
                        db,
                        cycle_id=request.form.get('cycle_id', type=int),
                        user_id=session.get('user_id'),
                        notes=request.form.get('notes', ''),
                    )
                    flash('Reprocessing step recorded.', 'success')
            except ValueError as exc:
                flash(str(exc), 'error')
            return redirect(url_for('dept_ops_reprocessing'))
        queue = svc.cleaning_queue(db)
        scopes = svc.list_scopes(db)
        return render_template(
            'gi/dept_ops/reprocessing.html',
            queue=queue,
            scopes=scopes,
            reprocessing_steps=REPROCESSING_STEPS,
            can_manage=session.get('role') in MANAGE_ROLES,
        )

    @app.route('/dept-ops/consumables', methods=['GET', 'POST'])
    @login_required
    @roles_required(*VIEW_ROLES)
    def dept_ops_consumables():
        db = get_db()
        if request.method == 'POST' and session.get('role') in MANAGE_ROLES:
            action = (request.form.get('action') or '').strip()
            try:
                if action == 'create':
                    svc.create_consumable(
                        db,
                        name=request.form.get('name', ''),
                        category=request.form.get('category', 'other'),
                        current_stock=request.form.get('current_stock', 0, type=int) or 0,
                        minimum_stock=request.form.get('minimum_stock', 0, type=int) or 0,
                        unit=request.form.get('unit', 'each'),
                        created_by=session.get('user_id'),
                    )
                    flash('Consumable added.', 'success')
                elif action == 'movement':
                    svc.record_stock_movement(
                        db,
                        consumable_id=request.form.get('consumable_id', type=int),
                        movement_type=request.form.get('movement_type', ''),
                        quantity=request.form.get('quantity', 0, type=int) or 0,
                        notes=request.form.get('notes', ''),
                        recorded_by=session.get('user_id'),
                    )
                    flash('Stock movement recorded.', 'success')
            except ValueError as exc:
                flash(str(exc), 'error')
            return redirect(url_for('dept_ops_consumables'))
        items = svc.list_consumables(db)
        low = svc.low_stock_items(db)
        return render_template(
            'gi/dept_ops/consumables.html',
            items=items,
            low_stock=low,
            categories=ALL_CONSUMABLE_CATEGORIES,
            movement_types=(STOCK_USAGE, STOCK_RECEIPT, STOCK_ADJUSTMENT),
            can_manage=session.get('role') in MANAGE_ROLES,
        )

    @app.route('/dept-ops/waiting-list', methods=['GET', 'POST'])
    @login_required
    @roles_required(*VIEW_ROLES)
    def dept_ops_waiting_list():
        db = get_db()
        if request.method == 'POST':
            action = (request.form.get('action') or '').strip()
            try:
                if action == 'add':
                    svc.add_waiting_list_entry(
                        db,
                        patient_name=request.form.get('patient_name', ''),
                        mrn=request.form.get('mrn', ''),
                        procedure_type=request.form.get('procedure_type', ''),
                        priority=request.form.get('priority', 'routine'),
                        consultant_name=request.form.get('consultant_name', ''),
                        scheduled_date=(request.form.get('scheduled_date') or '').strip() or None,
                        created_by=session.get('user_id'),
                    )
                    flash('Patient added to waiting list.', 'success')
                elif action == 'schedule':
                    svc.schedule_waiting_entry(
                        db,
                        entry_id=request.form.get('entry_id', type=int),
                        scheduled_date=request.form.get('scheduled_date', ''),
                    )
                    flash('Waiting list entry scheduled.', 'success')
            except ValueError as exc:
                flash(str(exc), 'error')
            return redirect(url_for('dept_ops_waiting_list'))
        entries = svc.list_waiting_list(db)
        summary = svc.waiting_list_summary(db)
        return render_template(
            'gi/dept_ops/waiting_list.html',
            entries=entries,
            summary=summary,
            priorities=ALL_PRIORITIES,
        )

    @app.route('/dept-ops/announcements', methods=['GET', 'POST'])
    @login_required
    @roles_required(*VIEW_ROLES)
    def dept_ops_announcements():
        db = get_db()
        if request.method == 'POST' and session.get('role') in MANAGE_ROLES:
            try:
                svc.create_announcement(
                    db,
                    title=request.form.get('title', ''),
                    body=request.form.get('body', ''),
                    category=request.form.get('category', 'notice'),
                    published_by_id=session.get('user_id'),
                )
                flash('Announcement published.', 'success')
            except ValueError as exc:
                flash(str(exc), 'error')
            return redirect(url_for('dept_ops_announcements'))
        announcements = svc.list_announcements(db)
        return render_template(
            'gi/dept_ops/announcements.html',
            announcements=announcements,
            categories=ANN_CATEGORIES,
            can_manage=session.get('role') in MANAGE_ROLES,
        )

    @app.route('/dept-ops/messages', methods=['GET', 'POST'])
    @login_required
    @roles_required(*VIEW_ROLES)
    def dept_ops_messages():
        db = get_db()
        uid = session.get('user_id')
        if request.method == 'POST':
            try:
                svc.send_message(
                    db,
                    sender_id=uid,
                    subject=request.form.get('subject', ''),
                    body=request.form.get('body', ''),
                    recipient_id=request.form.get('recipient_id', type=int),
                    message_scope=request.form.get('message_scope', 'direct'),
                )
                flash('Message sent.', 'success')
            except ValueError as exc:
                flash(str(exc), 'error')
            return redirect(url_for('dept_ops_messages'))
        messages = svc.list_messages(db, uid)
        staff = svc.list_staff_users(db)
        return render_template('gi/dept_ops/messages.html', messages=messages, staff=staff)

    @app.route('/dept-ops/roster', methods=['GET', 'POST'])
    @login_required
    @roles_required(*VIEW_ROLES)
    def dept_ops_roster():
        db = get_db()
        if request.method == 'POST' and session.get('role') in MANAGE_ROLES:
            try:
                svc.set_roster_entry(
                    db,
                    user_id=request.form.get('user_id', type=int),
                    roster_date=request.form.get('roster_date', ''),
                    shift_type=request.form.get('shift_type', 'day'),
                    is_on_call=1 if request.form.get('is_on_call') else 0,
                    notes=request.form.get('notes', ''),
                    created_by=session.get('user_id'),
                )
                flash('Roster entry saved.', 'success')
            except ValueError as exc:
                flash(str(exc), 'error')
            return redirect(url_for('dept_ops_roster'))
        roster = svc.roster_for_week(db)
        staff = svc.list_staff_users(db)
        return render_template(
            'gi/dept_ops/roster.html',
            roster=roster,
            staff=staff,
            shift_types=ALL_SHIFT_TYPES,
            can_manage=session.get('role') in MANAGE_ROLES,
        )
