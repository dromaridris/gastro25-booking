"""MCQ question bank routes.

Two clearly separated sections, exactly as requested:
- Manager section (/mcq-bank/admin/...): admin, hod, specialist, registrar
  only - upload books, run extraction, review/approve/reject/edit questions,
  generate + assign quizzes.
- Student section (/mcq-bank/...): any logged-in user - solve questions,
  track progress, see assigned quizzes. Never exposes internal fields
  (content_type, confidence_flag, raw_extracted_text, source_location,
  pipeline/chunk/OCR details) - those are stripped before they ever reach
  a student-facing response.
"""
from __future__ import annotations

import os
import re
import uuid

from flask import flash, jsonify, redirect, render_template, request, session, url_for

from mcq_bank.constants import CAN_MANAGE_MCQ_BANK
from mcq_bank import (
    book_service, content_service, daily_target_service, progress_service, quiz_service, jobs,
)
from mcq_bank.extractors.mcq.schema import student_view

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'mcq_bank_uploads')
os.makedirs(UPLOAD_DIR, exist_ok=True)


def _save_upload(file_storage):
    orig = file_storage.filename or 'upload.pdf'
    safe = re.sub(r'[^\w.\-]', '_', orig)
    stored = f"{uuid.uuid4().hex}_{safe}"
    path = os.path.join(UPLOAD_DIR, stored)
    file_storage.save(path)
    return path


def register_mcq_bank_routes(app, *, get_db, db_path, login_required, roles_required):

    # ================= MANAGER SECTION =================

    @app.route('/mcq-bank/admin')
    @login_required
    @roles_required(*CAN_MANAGE_MCQ_BANK)
    def mcqbank_admin_dashboard():
        db = get_db()
        books = book_service.list_books(db)
        summaries = []
        for b in books:
            summaries.append({
                'book': b,
                'pending': content_service.admin_count_items(db, book_id=b['id'], status='pending_review'),
                'approved': content_service.admin_count_items(db, book_id=b['id'], status='approved'),
                'rejected': content_service.admin_count_items(db, book_id=b['id'], status='rejected'),
            })
        return render_template('mcq_bank/admin_dashboard.html', summaries=summaries)

    @app.route('/mcq-bank/admin/upload', methods=['GET', 'POST'])
    @login_required
    @roles_required(*CAN_MANAGE_MCQ_BANK)
    def mcqbank_upload():
        if request.method == 'POST':
            file = request.files.get('file')
            book_name = request.form.get('book_name', '').strip()
            if not file or not book_name:
                flash('Book name and file are required.', 'error')
                return render_template('mcq_bank/upload.html')

            save_path = _save_upload(file)
            db = get_db()
            book = book_service.create_book(db, book_name, source_filename=file.filename)
            job_id = jobs.create_job(db, book['id'], content_type='mcq')
            jobs.start_extraction_job_async(db_path, job_id, book['id'], save_path)
            return redirect(url_for('mcqbank_job_progress', job_id=job_id))

        return render_template('mcq_bank/upload.html')

    @app.route('/mcq-bank/admin/jobs/<int:job_id>')
    @login_required
    @roles_required(*CAN_MANAGE_MCQ_BANK)
    def mcqbank_job_progress(job_id):
        return render_template('mcq_bank/job_progress.html', job_id=job_id)

    @app.route('/mcq-bank/admin/api/jobs/<int:job_id>')
    @login_required
    @roles_required(*CAN_MANAGE_MCQ_BANK)
    def mcqbank_api_job_status(job_id):
        job = jobs.get_job(get_db(), job_id)
        if job is None:
            return jsonify({'error': 'not found'}), 404
        return jsonify(job)

    @app.route('/mcq-bank/admin/review/<int:book_id>')
    @login_required
    @roles_required(*CAN_MANAGE_MCQ_BANK)
    def mcqbank_review(book_id):
        db = get_db()
        book = book_service.get_book(db, book_id)
        chapters = book_service.list_chapters(db, book_id)

        chapter_id = request.args.get('chapter_id', type=int)
        status = request.args.get('status') or None
        confidence_flag = request.args.get('confidence_flag') or None
        search = request.args.get('search') or None
        page = request.args.get('page', default=1, type=int)
        per_page = 20

        items = content_service.admin_list_items(
            db, book_id=book_id, chapter_id=chapter_id, status=status,
            confidence_flag=confidence_flag, search=search,
            limit=per_page, offset=(page - 1) * per_page,
        )
        total = content_service.admin_count_items(
            db, book_id=book_id, chapter_id=chapter_id, status=status,
            confidence_flag=confidence_flag, search=search,
        )

        return render_template(
            'mcq_bank/review.html', book=book, chapters=chapters, items=items,
            chapter_by_id={c['id']: c for c in chapters},
            chapter_id=chapter_id, status=status, confidence_flag=confidence_flag,
            search=search or '', page=page, per_page=per_page, total=total,
        )

    @app.route('/mcq-bank/admin/api/items/<int:item_id>', methods=['PATCH'])
    @login_required
    @roles_required(*CAN_MANAGE_MCQ_BANK)
    def mcqbank_api_update_item(item_id):
        data = request.get_json(force=True)
        db = get_db()
        if 'payload' in data:
            content_service.admin_update_payload(db, item_id, data['payload'])
        if 'status' in data:
            content_service.admin_set_status(db, item_id, data['status'])
        return jsonify(content_service.admin_get_item(db, item_id))

    @app.route('/mcq-bank/admin/api/books/<int:book_id>/bulk_approve', methods=['POST'])
    @login_required
    @roles_required(*CAN_MANAGE_MCQ_BANK)
    def mcqbank_api_bulk_approve(book_id):
        chapter_id = request.get_json(force=True).get('chapter_id')
        content_service.admin_bulk_approve_high_confidence(get_db(), book_id, chapter_id)
        return jsonify({'ok': True})

    @app.route('/mcq-bank/admin/api/books/<int:book_id>', methods=['DELETE'])
    @login_required
    @roles_required(*CAN_MANAGE_MCQ_BANK)
    def mcqbank_api_delete_book(book_id):
        db = get_db()
        book = book_service.get_book(db, book_id)
        if book and book['source_filename']:
            # stored files use a uuid-prefixed name on disk (see _save_upload) -
            # nothing to clean up here since it's already deleted post-extraction
            # by jobs.py on success; this covers the failed-job leftover case.
            pass
        book_service.delete_book(db, book_id)
        return jsonify({'ok': True})

    # ---- Quiz generation (HOD/admin/specialist/registrar) ----

    @app.route('/mcq-bank/admin/quiz/generate', methods=['GET', 'POST'])
    @login_required
    @roles_required(*CAN_MANAGE_MCQ_BANK)
    def mcqbank_generate_quiz():
        db = get_db()
        if request.method == 'POST':
            title = request.form.get('title', '').strip() or 'Quick Quiz'
            question_count = request.form.get('question_count', type=int) or 20
            book_id = request.form.get('book_id', type=int) or None
            chapter_id = request.form.get('chapter_id', type=int) or None
            user_ids = [int(x) for x in request.form.getlist('user_ids') if x]

            quiz = quiz_service.generate_quiz(
                db, title, question_count, session.get('user_id'),
                book_id=book_id, chapter_id=chapter_id,
            )
            if not quiz:
                flash('No approved questions available for that selection.', 'error')
                return redirect(url_for('mcqbank_generate_quiz'))

            assigned = quiz_service.assign_quiz_to_users(db, quiz['id'], user_ids, session.get('user_id'))
            flash(f'Quiz "{quiz["title"]}" created and assigned to {assigned} user(s).', 'success')
            return redirect(url_for('mcqbank_admin_dashboard'))

        books = book_service.list_books(db)
        users = db.execute("SELECT id, full_name, username, role FROM user ORDER BY full_name").fetchall()
        return render_template('mcq_bank/generate_quiz.html', books=books, users=users)

    # ================= STUDENT SECTION =================

    @app.route('/mcq-bank')
    @login_required
    def mcqbank_dashboard():
        db = get_db()
        uid = session.get('user_id')
        books = book_service.list_books(db)
        book_summaries = []
        for b in books:
            total = content_service.admin_count_items(db, book_id=b['id'], status='approved')
            if total == 0:
                continue
            chapters = book_service.list_chapters(db, b['id'])
            book_summaries.append({'book': b, 'total_approved': total, 'chapters': chapters})

        my_quizzes = quiz_service.list_my_assigned_quizzes(db, uid, status='pending')
        daily_target = daily_target_service.get_status(db, uid)
        return render_template(
            'mcq_bank/dashboard.html',
            book_summaries=book_summaries,
            my_quizzes=my_quizzes,
            daily_target=daily_target,
        )

    @app.route('/mcq-bank/api/daily-target', methods=['GET', 'POST'])
    @login_required
    def mcqbank_api_daily_target():
        db = get_db()
        uid = session.get('user_id')
        if request.method == 'GET':
            return jsonify(daily_target_service.get_status(db, uid))

        data = request.get_json(silent=True) or {}
        # Form posts from dashboard settings also accepted.
        if not data and request.form:
            enabled_vals = request.form.getlist('enabled')
            # Form checkbox: any "1"/"on"/"true" enables; absent = disabled.
            enabled = any(v in ('1', 'true', 'on', 'yes') for v in enabled_vals)
            data = {
                'enabled': enabled,
                'target_count': request.form.get('target_count', type=int),
            }
        enabled = bool(data.get('enabled'))
        target_count = data.get('target_count')
        try:
            target_count = int(target_count) if target_count is not None else None
        except (TypeError, ValueError):
            target_count = None
        status = daily_target_service.set_settings(
            db, uid, enabled=enabled, target_count=target_count,
        )
        if request.is_json:
            return jsonify(status)
        flash(
            'Daily target saved.' if status['enabled'] else 'Daily target disabled.',
            'success',
        )
        return redirect(url_for('mcqbank_dashboard'))

    @app.route('/mcq-bank/solve')
    @login_required
    def mcqbank_solve():
        book_id = request.args.get('book_id', type=int)
        chapter_id = request.args.get('chapter_id', type=int)
        topic = request.args.get('topic')
        wrong_only = request.args.get('wrong_only') == '1'
        random_mode = request.args.get('random') == '1'
        question_code = (request.args.get('code') or '').strip().upper()

        db = get_db()
        uid = session.get('user_id')
        book = book_service.get_book(db, book_id) if book_id else None
        chapter = book_service.get_chapter(db, chapter_id) if chapter_id else None
        daily_target = daily_target_service.get_status(db, uid)

        return render_template(
            'mcq_bank/solve.html',
            book_id=book_id, chapter_id=chapter_id, topic=topic or '',
            wrong_only='1' if wrong_only else '0',
            random='1' if random_mode else '0',
            question_code=question_code,
            book=book, chapter=chapter,
            daily_target=daily_target,
        )

    def _resolve(db, args):
        book_id = args.get('book_id', type=int)
        chapter_id = args.get('chapter_id', type=int)
        topic = args.get('topic') or None
        wrong_only = args.get('wrong_only') == '1'
        question_code = (args.get('code') or '').strip().upper() or None

        base_scope_key, base_item_ids = progress_service.resolve_scope(
            db, book_id=book_id, chapter_id=chapter_id, topic=topic,
            question_code=question_code,
        )
        if wrong_only:
            scope_key = f"wrong::{base_scope_key}"
            item_ids = progress_service.get_wrong_only_items(db, session.get('user_id'), base_scope_key)
        else:
            scope_key, item_ids = base_scope_key, base_item_ids
        return scope_key, item_ids

    @app.route('/mcq-bank/api/next')
    @login_required
    def mcqbank_api_next():
        db = get_db()
        uid = session.get('user_id')
        scope_key, item_ids = _resolve(db, request.args)
        random_order = request.args.get('random') == '1'
        cycle = progress_service.get_or_create_current_cycle(db, uid, scope_key)
        progress_service.ensure_cycle_progress_rows(db, uid, scope_key, cycle, item_ids)

        next_id = progress_service.get_next_question(db, uid, scope_key, cycle, item_ids, random_order=random_order)
        stats = progress_service.get_stats(db, uid, scope_key, cycle)
        daily_target = daily_target_service.get_status(db, uid)

        if next_id is None:
            progress_service.maybe_complete_cycle(db, uid, scope_key, cycle)
            return jsonify({
                'done': True, 'stats': stats, 'scope_key': scope_key,
                'cycle_number': cycle, 'daily_target': daily_target,
            })

        item = content_service.student_get_item(db, next_id)
        payload = item['payload']
        edit_url = None
        if session.get('role') in CAN_MANAGE_MCQ_BANK:
            edit_url = url_for(
                'mcqbank_review', book_id=item['book_id'], search=item['question_code'],
            )
        return jsonify({
            'done': False, 'item_id': next_id, 'scope_key': scope_key, 'cycle_number': cycle,
            'question': student_view(payload, reveal_answer=False), 'stats': stats,
            'question_code': item['question_code'], 'edit_url': edit_url,
            'daily_target': daily_target,
        })

    @app.route('/mcq-bank/api/answer', methods=['POST'])
    @login_required
    def mcqbank_api_answer():
        db = get_db()
        uid = session.get('user_id')
        data = request.get_json(force=True)
        result = progress_service.submit_answer(
            db, uid, data['item_id'], data['scope_key'],
            data['cycle_number'], data['selected_option'],
        )
        if result is None:
            return jsonify({'error': 'item not found'}), 404
        result['stats'] = progress_service.get_stats(db, uid, data['scope_key'], data['cycle_number'])
        if 'daily_target' not in result:
            result['daily_target'] = daily_target_service.get_status(db, uid)
        return jsonify(result)

    @app.route('/mcq-bank/api/new_cycle', methods=['POST'])
    @login_required
    def mcqbank_api_new_cycle():
        db = get_db()
        data = request.get_json(force=True)
        cycle = progress_service.get_or_create_current_cycle(db, session.get('user_id'), data['scope_key'])
        return jsonify({'cycle_number': cycle})

    # ---- Taking an assigned quiz ----

    def _require_quiz_assignment(db, quiz_id, user_id):
        quiz = db.execute("SELECT * FROM mcqbank_quiz WHERE id = ?", (quiz_id,)).fetchone()
        if not quiz:
            return None, None
        assigned = db.execute(
            "SELECT 1 FROM mcqbank_quiz_assignment WHERE quiz_id = ? AND user_id = ?",
            (quiz_id, user_id),
        ).fetchone()
        if not assigned and session.get('role') not in CAN_MANAGE_MCQ_BANK:
            return quiz, False
        return quiz, True

    @app.route('/mcq-bank/quiz/<int:quiz_id>/take')
    @login_required
    def mcqbank_take_quiz(quiz_id):
        db = get_db()
        quiz, allowed = _require_quiz_assignment(db, quiz_id, session.get('user_id'))
        if not quiz:
            flash('Quiz not found.', 'error')
            return redirect(url_for('mcqbank_dashboard'))
        if not allowed:
            flash('This quiz is not assigned to you.', 'error')
            return redirect(url_for('mcqbank_dashboard'))
        items = quiz_service.get_quiz_items(db, quiz_id)
        return render_template('mcq_bank/take_quiz.html', quiz=quiz, items_count=len(items))

    @app.route('/mcq-bank/api/quiz/<int:quiz_id>/items')
    @login_required
    def mcqbank_api_quiz_items(quiz_id):
        db = get_db()
        quiz, allowed = _require_quiz_assignment(db, quiz_id, session.get('user_id'))
        if not quiz:
            return jsonify({'error': 'not found'}), 404
        if not allowed:
            return jsonify({'error': 'forbidden'}), 403
        rows = quiz_service.get_quiz_items(db, quiz_id)
        import json
        out = []
        for r in rows:
            payload = json.loads(r['payload_json'])
            out.append({
                'content_item_id': r['content_item_id'],
                'position': r['position'],
                'question_code': r['question_code'],
                'question': student_view(payload, reveal_answer=False),
            })
        return jsonify(out)

    @app.route('/mcq-bank/api/quiz/<int:quiz_id>/submit', methods=['POST'])
    @login_required
    def mcqbank_api_quiz_submit(quiz_id):
        db = get_db()
        uid = session.get('user_id')
        quiz, allowed = _require_quiz_assignment(db, quiz_id, uid)
        if not quiz:
            return jsonify({'error': 'not found'}), 404
        if not allowed:
            return jsonify({'error': 'forbidden'}), 403
        answers = request.get_json(force=True).get('answers', [])  # [{content_item_id, selected_option}]
        prior = db.execute(
            "SELECT status FROM mcqbank_quiz_assignment WHERE quiz_id = ? AND user_id = ?",
            (quiz_id, uid),
        ).fetchone()
        first_submit = not prior or prior['status'] != 'done'

        correct = 0
        results = []
        for a in answers:
            payload = content_service.student_get_item_payload(db, a['content_item_id'])
            if not payload:
                continue
            is_correct = a['selected_option'] == payload['correct_answer']
            correct += 1 if is_correct else 0
            results.append({
                'content_item_id': a['content_item_id'], 'is_correct': is_correct,
                **student_view(payload, reveal_answer=True),
            })
        quiz_service.record_quiz_result(db, quiz_id, uid, correct, len(answers))
        daily_target = daily_target_service.get_status(db, uid)
        if first_submit and answers:
            daily_target = daily_target_service.record_solves(db, uid, len(answers))
        return jsonify({
            'correct': correct, 'total': len(answers), 'results': results,
            'daily_target': daily_target,
        })
