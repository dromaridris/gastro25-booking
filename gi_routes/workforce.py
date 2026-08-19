"""Workforce task board routes."""

from flask import flash, redirect, render_template, request, session, url_for

from gi_platform import workforce_service, research_service, governance_clinical_service, user_mention_service
from gi_platform.constants import can_delete_task

WORKFORCE_ROLES = (
    'admin', 'hod', 'consultant', 'specialist', 'registrar', 'general_endoscopy',
    'house_officer', 'pg_trainee', 'nurse_manager', 'staff_nurse',
)


def register_workforce_routes(app, *, get_db, login_required, roles_required):
    @app.route('/ward/tasks')
    @login_required
    @roles_required(*WORKFORCE_ROLES)
    def gi_workforce_board():
        db = get_db()
        user_id = session.get('user_id') or 0
        user = db.execute('SELECT role FROM user WHERE id = ?', (user_id,)).fetchone()
        role = user['role'] if user else ''
        training_assignments = governance_clinical_service.list_training_assignments_for_user(
            db, user_id,
        )
        mention_assignments = user_mention_service.list_mention_assignments_for_user(
            db, user_id,
        )
        from gi_platform import notification_service
        notification_service.mark_my_tasks_seen(db, user_id)
        upcoming_presentations = governance_clinical_service.list_upcoming_presentations(db)
        research_projects = research_service.list_registries_for_user(db, user_id)
        from mcq_bank import quiz_service
        quiz_assignments = quiz_service.list_my_assigned_quizzes(db, user_id)
        from gi_platform import nav_permissions as navperm
        return render_template(
            'gi/workforce_board.html',
            role=role,
            training_assignments=training_assignments,
            mention_assignments=mention_assignments,
            upcoming_presentations=upcoming_presentations,
            research_projects=research_projects,
            quiz_assignments=quiz_assignments,
            can_delete_task=can_delete_task(role),
            module_intro=navperm.intro('my_tasks'),
        )

    @app.route('/ward/patient/<int:ward_patient_id>/tasks', methods=['GET', 'POST'])
    @login_required
    @roles_required(*WORKFORCE_ROLES)
    def gi_patient_tasks(ward_patient_id):
        db = get_db()
        user_id = session.get('user_id')
        user = db.execute('SELECT role FROM user WHERE id = ?', (user_id,)).fetchone()
        role = user['role'] if user else ''
        if request.method == 'POST':
            workforce_service.create_task(
                db, ward_patient_id=ward_patient_id,
                task_type=(request.form.get('task_type') or 'history').strip(),
                title=(request.form.get('title') or '').strip(),
                assigned_role=(request.form.get('assigned_role') or '').strip(),
                notes=(request.form.get('notes') or '').strip(),
                created_by=user_id,
            )
            flash('Task created.', 'success')
            return redirect(url_for('gi_patient_tasks', ward_patient_id=ward_patient_id))
        tasks = workforce_service.list_tasks_for_patient(db, ward_patient_id)
        return render_template(
            'gi/patient_tasks.html',
            ward_patient_id=ward_patient_id,
            tasks=tasks,
            task_types=workforce_service.TASK_TYPES,
            role=role,
            can_delete_task=can_delete_task(role),
        )

    @app.route('/ward/training-assignments/<int:assignment_id>/status', methods=['POST'])
    @login_required
    @roles_required(*WORKFORCE_ROLES)
    def gi_training_assignment_status(assignment_id):
        db = get_db()
        ok = governance_clinical_service.complete_training_assignment(
            db, assignment_id, session.get('user_id') or 0,
        )
        if ok:
            flash('Presentation marked done.', 'success')
        else:
            flash('Assignment not found or you are not the presenter.', 'error')
        return redirect(request.referrer or url_for('gi_workforce_board'))

    @app.route('/ward/training-assignments/<int:assignment_id>/delete', methods=['POST'])
    @login_required
    @roles_required(*WORKFORCE_ROLES)
    def gi_training_assignment_delete(assignment_id):
        db = get_db()
        user = db.execute('SELECT role FROM user WHERE id = ?', (session.get('user_id'),)).fetchone()
        role = user['role'] if user else ''
        if not can_delete_task(role):
            flash('You do not have permission to delete this assignment.', 'error')
            return redirect(request.referrer or url_for('gi_workforce_board'))
        ok = governance_clinical_service.delete_training_assignment(db, assignment_id)
        if ok:
            flash('Assignment removed.', 'success')
        else:
            flash('Assignment not found.', 'error')
        return redirect(request.referrer or url_for('gi_workforce_board'))

    @app.route('/ward/tasks/<int:task_id>/status', methods=['POST'])
    @login_required
    @roles_required(*WORKFORCE_ROLES)
    def gi_task_status(task_id):
        db = get_db()
        user_id = session.get('user_id')
        user = db.execute('SELECT role FROM user WHERE id = ?', (user_id,)).fetchone()
        role = user['role'] if user else ''
        task = workforce_service.get_task(db, task_id)
        if not workforce_service.can_complete_task(task, user_id=user_id, role=role):
            flash('You do not have permission to complete this task.', 'error')
            return redirect(request.referrer or url_for('gi_workforce_board'))
        status = (request.form.get('status') or 'done').strip()
        workforce_service.update_task_status(db, task_id, status)
        flash('Task updated.', 'success')
        return redirect(request.referrer or url_for('gi_workforce_board'))

    @app.route('/ward/tasks/<int:task_id>/delete', methods=['POST'])
    @login_required
    @roles_required(*WORKFORCE_ROLES)
    def gi_task_delete(task_id):
        db = get_db()
        user = db.execute('SELECT role FROM user WHERE id = ?', (session.get('user_id'),)).fetchone()
        role = user['role'] if user else ''
        if not can_delete_task(role):
            flash('You do not have permission to delete this task.', 'error')
            return redirect(request.referrer or url_for('gi_workforce_board'))
        task = workforce_service.get_task(db, task_id)
        ward_patient_id = task['ward_patient_id'] if task else None
        ok = workforce_service.delete_task(db, task_id)
        if ok:
            flash('Task deleted.', 'success')
        else:
            flash('Task not found.', 'error')
        if ward_patient_id:
            return redirect(url_for('gi_patient_tasks', ward_patient_id=ward_patient_id))
        return redirect(request.referrer or url_for('gi_workforce_board'))
