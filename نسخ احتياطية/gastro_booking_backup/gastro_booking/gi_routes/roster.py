"""On-call roster routes — separate trainee and house officer managers."""

from flask import flash, redirect, render_template, request, send_file, session, url_for
import io
from datetime import date

from gi_platform.constants import ROSTER_TYPE_HOUSE_OFFICER, ROSTER_TYPE_TRAINEE, ROSTER_TYPE_LABELS, SHIFT_TYPES
from gi_platform import permission_service, roster_service

ADMIN_ROLES = ('admin', 'hod', 'specialist')


def register_roster_routes(app, *, get_db, login_required, roles_required):
    def _check_roster_access(db, roster_type):
        uid = session.get('user_id')
        if not permission_service.can_manage_roster(db, uid, roster_type):
            flash('You do not have permission to manage this roster.', 'error')
            return False
        return True

    @app.route('/roster')
    @login_required
    def gi_roster_index():
        db = get_db()
        uid = session.get('user_id')
        can_trainee = permission_service.can_manage_roster(db, uid, ROSTER_TYPE_TRAINEE)
        can_ho = permission_service.can_manage_roster(db, uid, ROSTER_TYPE_HOUSE_OFFICER)
        return render_template(
            'gi/roster_index.html',
            can_trainee=can_trainee, can_ho=can_ho,
            labels=ROSTER_TYPE_LABELS,
            module_intro='On-call rosters for PG trainees and house officers.',
        )

    @app.route('/roster/<roster_type>')
    @login_required
    def gi_roster_list(roster_type):
        if roster_type not in (ROSTER_TYPE_TRAINEE, ROSTER_TYPE_HOUSE_OFFICER):
            flash('Invalid roster type.', 'error')
            return redirect(url_for('gi_roster_index'))
        db = get_db()
        if not _check_roster_access(db, roster_type):
            return redirect(url_for('gi_roster_index'))
        periods = roster_service.list_periods(db, roster_type)
        return render_template(
            'gi/roster_list.html', roster_type=roster_type,
            periods=periods, label=ROSTER_TYPE_LABELS[roster_type],
        )

    @app.route('/roster/<roster_type>/<year_month>', methods=['GET', 'POST'])
    @login_required
    def gi_roster_edit(roster_type, year_month):
        if roster_type not in (ROSTER_TYPE_TRAINEE, ROSTER_TYPE_HOUSE_OFFICER):
            return redirect(url_for('gi_roster_index'))
        db = get_db()
        if not _check_roster_access(db, roster_type):
            return redirect(url_for('gi_roster_index'))

        period_id = roster_service.get_or_create_period(
            db, roster_type=roster_type, year_month=year_month,
            created_by=session.get('user_id'),
        )
        period = roster_service.get_period(db, period_id)

        if request.method == 'POST':
            action = request.form.get('action')
            if action == 'assign':
                uids = [int(x) for x in request.form.getlist('user_ids') if x]
                roster_service.set_shift_assignments(
                    db, period_id=period_id,
                    roster_date=request.form.get('roster_date', ''),
                    shift_type=request.form.get('shift_type', 'on_call'),
                    user_ids=uids,
                    notes=request.form.get('notes', ''),
                )
                flash('Shift updated.', 'success')
            elif action == 'publish':
                notified = roster_service.publish_period(db, period_id, session.get('user_id'))
                flash(f'Roster published — {len(notified)} staff notified.', 'success')
            elif action == 'import' and request.files.get('excel_file'):
                count = roster_service.import_excel(
                    db, period_id=period_id,
                    file_bytes=request.files['excel_file'].read(),
                    role_filter=roster_type,
                )
                flash(f'Imported {count} shift rows from Excel.', 'success')
            return redirect(url_for('gi_roster_edit', roster_type=roster_type, year_month=year_month))

        grid = roster_service.get_period_grid(db, period_id)
        staff = roster_service.eligible_staff(db, roster_type)
        year, month = map(int, year_month.split('-'))
        import calendar
        days_in_month = calendar.monthrange(year, month)[1]
        days = [date(year, month, d).isoformat() for d in range(1, days_in_month + 1)]
        return render_template(
            'gi/roster_edit.html',
            roster_type=roster_type, year_month=year_month, period=period,
            grid=grid, staff=staff, days=days, shift_types=SHIFT_TYPES,
            label=ROSTER_TYPE_LABELS[roster_type],
        )

    @app.route('/roster/<roster_type>/<year_month>/export')
    @login_required
    def gi_roster_export(roster_type, year_month):
        db = get_db()
        if not _check_roster_access(db, roster_type):
            return redirect(url_for('gi_roster_index'))
        period = db.execute(
            'SELECT id FROM gi_duty_roster_period WHERE roster_type = ? AND year_month = ?',
            (roster_type, year_month),
        ).fetchone()
        if not period:
            flash('Roster not found.', 'error')
            return redirect(url_for('gi_roster_list', roster_type=roster_type))
        data = roster_service.export_excel(db, period['id'])
        return send_file(
            io.BytesIO(data),
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f'roster_{roster_type}_{year_month}.xlsx',
        )

    @app.route('/roster/<roster_type>/new/<year_month>')
    @login_required
    def gi_roster_new_month(roster_type, year_month):
        if roster_type not in (ROSTER_TYPE_TRAINEE, ROSTER_TYPE_HOUSE_OFFICER):
            return redirect(url_for('gi_roster_index'))
        db = get_db()
        if not _check_roster_access(db, roster_type):
            return redirect(url_for('gi_roster_index'))
        roster_service.get_or_create_period(
            db, roster_type=roster_type, year_month=year_month,
            created_by=session.get('user_id'),
        )
        return redirect(url_for('gi_roster_edit', roster_type=roster_type, year_month=year_month))

    @app.route('/roster/my-duties')
    @login_required
    def gi_my_duties():
        db = get_db()
        duties = roster_service.my_duties(db, session.get('user_id'))
        return render_template(
            'gi/my_duties.html', duties=duties, labels=ROSTER_TYPE_LABELS,
            module_intro='Your published on-call roster assignments for the month.',
        )
