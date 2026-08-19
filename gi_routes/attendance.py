"""Attendance routes — activity-based + monthly HOD report."""

from flask import flash, redirect, render_template, request, send_file, session, url_for
import io
from datetime import date

from openpyxl import Workbook

from gi_platform import attendance_service

HOD_ROLES = ('admin', 'specialist')
STAFF_ATTENDANCE_ROLES = ('admin', 'specialist')


def register_attendance_routes(app, *, get_db, login_required, roles_required):
    @app.route('/attendance')
    @login_required
    @roles_required(*STAFF_ATTENDANCE_ROLES)
    def gi_attendance_mine():
        return redirect(url_for('gi_attendance_department'))

    @app.route('/attendance/department')
    @login_required
    @roles_required(*STAFF_ATTENDANCE_ROLES)
    def gi_attendance_department():
        db = get_db()
        today = date.today()
        year = request.args.get('year', type=int) or today.year
        month = request.args.get('month', type=int) or today.month
        summary = db.execute(
            """
            SELECT DISTINCT u.id AS user_id, u.full_name, u.role,
                   0 AS present_days, 0 AS absent_days, 0 AS leave_days, 0 AS active_days
            FROM user u
            WHERE u.role IN ('admin','hod','consultant','specialist','registrar','house_officer','pg_trainee','general_endoscopy')
              AND u.is_approved = 1
            ORDER BY u.full_name
            """
        ).fetchall()
        if request.args.get('computed'):
            summary = attendance_service.compute_monthly_attendance(db, year=year, month=month)
        return render_template(
            'gi/attendance_department.html',
            summary=summary, year=year, month=month,
            module_intro='Department staff attendance overview — admin & specialist only (staff cannot see their own).',
        )

    @app.route('/attendance/generate', methods=['POST'])
    @login_required
    @roles_required(*STAFF_ATTENDANCE_ROLES)
    def gi_attendance_generate():
        year = request.form.get('year', type=int)
        month = request.form.get('month', type=int)
        db = get_db()
        summary = attendance_service.compute_monthly_attendance(db, year=year, month=month)
        flash(f'Attendance computed for {len(summary)} staff.', 'success')
        return redirect(url_for('gi_attendance_department', year=year, month=month, computed=1))

    @app.route('/attendance/adjust', methods=['POST'])
    @login_required
    @roles_required(*STAFF_ATTENDANCE_ROLES)
    def gi_attendance_adjust():
        db = get_db()
        attendance_service.add_adjustment(
            db,
            user_id=request.form.get('user_id', type=int),
            adjustment_date=request.form.get('adjustment_date', ''),
            adjustment_type=request.form.get('adjustment_type', 'leave'),
            notes=request.form.get('notes', ''),
            approved_by_id=session.get('user_id'),
        )
        flash('Attendance adjustment saved.', 'success')
        return redirect(request.referrer or url_for('gi_attendance_department'))

    @app.route('/attendance/export')
    @login_required
    @roles_required(*STAFF_ATTENDANCE_ROLES)
    def gi_attendance_export():
        db = get_db()
        today = date.today()
        year = request.args.get('year', type=int) or today.year
        month = request.args.get('month', type=int) or today.month
        summary = attendance_service.compute_monthly_attendance(db, year=year, month=month)
        wb = Workbook()
        ws = wb.active
        ws.title = 'Attendance'
        ws.append(['Name', 'Role', 'Present', 'Absent', 'Leave', 'Active days'])
        for s in summary:
            ws.append([s['full_name'], s['role'], s['present_days'],
                       s['absent_days'], s['leave_days'], s['active_days']])
        buf = io.BytesIO()
        wb.save(buf)
        return send_file(
            buf, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True, download_name=f'attendance_{year}_{month:02d}.xlsx',
        )
