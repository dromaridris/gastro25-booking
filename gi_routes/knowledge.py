"""Knowledge Library routes."""

from flask import flash, redirect, render_template, request, session, url_for

from gi_platform import audit_service, knowledge_service

GI_READ_ROLES = ('admin', 'specialist')
GI_WRITE_ROLES = ('admin', 'specialist')


def register_knowledge_routes(app, *, get_db, login_required, roles_required):
    @app.route('/knowledge-library')
    @login_required
    @roles_required(*GI_READ_ROLES)
    def gi_knowledge_index():
        db = get_db()
        q = request.args.get('q', '').strip()
        status = request.args.get('status') or None
        object_type = request.args.get('object_type') or None
        objects = knowledge_service.list_objects(db, status=status, object_type=object_type, q=q or None)
        stats = db.execute(
            """
            SELECT object_type, COUNT(*) AS c FROM gi_knowledge_object
            GROUP BY object_type ORDER BY c DESC
            """
        ).fetchall()
        total = db.execute("SELECT COUNT(*) AS c FROM gi_knowledge_object").fetchone()['c']
        return render_template(
            'gi/knowledge_index.html', objects=objects, q=q, status=status,
            object_type=object_type, stats=stats, total=total,
            module_intro='Published clinical concepts, guidelines, and scores — admin & specialist only.',
        )

    @app.route('/knowledge-library/registry')
    @login_required
    @roles_required(*GI_READ_ROLES)
    def gi_knowledge_registry():
        db = get_db()
        reg_stats = knowledge_service.registry_stats(db)
        recent = knowledge_service.list_objects(db, limit=20)
        return render_template(
            'gi/knowledge_registry.html', reg_stats=reg_stats, recent=recent,
        )

    @app.route('/knowledge-library/<int:object_id>')
    @login_required
    @roles_required(*GI_READ_ROLES)
    def gi_knowledge_detail(object_id):
        db = get_db()
        obj = knowledge_service.get_object(db, object_id)
        if not obj:
            flash('Knowledge object not found.', 'error')
            return redirect(url_for('gi_knowledge_index'))
        links = knowledge_service.list_links(db, object_id)
        provenance = knowledge_service.list_provenance(db, object_id)
        from gi_platform import import_service
        import_file = import_service.file_path_for_object(db, object_id)
        import json
        try:
            imported_body = json.loads(obj['body_json'] or '{}')
        except (json.JSONDecodeError, TypeError):
            imported_body = {}
        return render_template(
            'gi/knowledge_detail.html', obj=obj, links=links,
            provenance=provenance, has_import_file=bool(import_file),
            imported_body=imported_body if isinstance(imported_body, dict) else {},
        )

    @app.route('/knowledge-library/new', methods=['GET', 'POST'])
    @login_required
    @roles_required(*GI_WRITE_ROLES)
    def gi_knowledge_new():
        if request.method == 'POST':
            slug = (request.form.get('slug') or '').strip()
            title = (request.form.get('title') or '').strip()
            if not slug or not title:
                flash('Slug and title are required.', 'error')
            else:
                oid = knowledge_service.create_object(
                    get_db(), slug=slug, title=title,
                    object_type=request.form.get('object_type') or 'concept',
                    summary=(request.form.get('summary') or '').strip(),
                    created_by=session.get('user_id'),
                )
                audit_service.log_event(
                    get_db(), action='knowledge_create', entity_type='gi_knowledge_object',
                    entity_id=oid, user_id=session.get('user_id'),
                )
                flash('Knowledge object created as draft.', 'success')
                return redirect(url_for('gi_knowledge_index'))
        return render_template('gi/knowledge_form.html')

    @app.route('/knowledge-library/<int:object_id>/status', methods=['POST'])
    @login_required
    @roles_required(*GI_WRITE_ROLES)
    def gi_knowledge_status(object_id):
        status = (request.form.get('status') or '').strip()
        if status in ('draft', 'review', 'published', 'archived'):
            knowledge_service.update_object_status(get_db(), object_id, status)
            audit_service.log_event(
                get_db(), action='knowledge_status', entity_type='gi_knowledge_object',
                entity_id=object_id, user_id=session.get('user_id'), details={'status': status},
            )
            flash(f'Status updated to {status}.', 'success')
        return redirect(url_for('gi_knowledge_detail', object_id=object_id))

    @app.route('/knowledge-library/<int:object_id>/delete', methods=['POST'])
    @login_required
    @roles_required('admin', 'hod')
    def gi_knowledge_delete(object_id):
        from gi_platform.constants import has_full_access
        if not has_full_access(session.get('role')):
            flash('Only Admin or HOD can delete knowledge objects.', 'error')
            return redirect(url_for('gi_knowledge_index'))
        obj = knowledge_service.get_object(get_db(), object_id)
        if not obj:
            flash('Knowledge object not found.', 'error')
            return redirect(url_for('gi_knowledge_index'))
        title = obj['title']
        knowledge_service.delete_object(get_db(), object_id)
        audit_service.log_event(
            get_db(), action='knowledge_delete', entity_type='gi_knowledge_object',
            entity_id=object_id, user_id=session.get('user_id'), details={'title': title},
        )
        flash(f'Permanently deleted "{title}".', 'success')
        return redirect(url_for('gi_knowledge_index'))

    @app.route('/knowledge-library/review')
    @login_required
    @roles_required('admin', 'specialist')
    def gi_knowledge_review():
        pending = knowledge_service.list_pending_reviews(get_db())
        return render_template('gi/knowledge_review.html', pending=pending)

    @app.route('/knowledge-library/review/<int:object_id>/approve', methods=['POST'])
    @login_required
    @roles_required('admin', 'specialist')
    def gi_knowledge_approve_review(object_id):
        knowledge_service.approve_review(get_db(), object_id)
        audit_service.log_event(
            get_db(), action='knowledge_review_approved', entity_type='gi_knowledge_object',
            entity_id=object_id, user_id=session.get('user_id'),
        )
        flash('Object published after review.', 'success')
        return redirect(url_for('gi_knowledge_review'))

    @app.route('/knowledge-library/activation')
    @login_required
    @roles_required('admin', 'specialist')
    def gi_knowledge_activation():
        pending = knowledge_service.list_pending_activations(get_db())
        return render_template('gi/knowledge_activation.html', pending=pending)

    @app.route('/knowledge-library/activation/<int:activation_id>/resolve', methods=['POST'])
    @login_required
    @roles_required('admin', 'specialist')
    def gi_knowledge_resolve_activation(activation_id):
        approved = request.form.get('decision') == 'approve'
        knowledge_service.resolve_activation(
            get_db(), activation_id, approved=approved,
            resolved_by=session.get('user_id'),
            notes=(request.form.get('notes') or '').strip(),
        )
        audit_service.log_event(
            get_db(), action='knowledge_activation_' + ('approved' if approved else 'rejected'),
            entity_type='gi_knowledge_activation', entity_id=activation_id,
            user_id=session.get('user_id'),
        )
        flash('Activation request processed.', 'success')
        return redirect(url_for('gi_knowledge_activation'))

    @app.route('/knowledge-library/<int:object_id>/activate', methods=['POST'])
    @login_required
    @roles_required('admin', 'specialist')
    def gi_knowledge_request_activation(object_id):
        knowledge_service.request_activation(
            get_db(), object_id, session.get('user_id'),
            notes=(request.form.get('notes') or '').strip(),
        )
        flash('Activation request submitted.', 'success')
        return redirect(url_for('gi_knowledge_detail', object_id=object_id))

    @app.route('/knowledge-library/guidelines')
    @login_required
    @roles_required(*GI_READ_ROLES)
    def gi_guidelines_index():
        objects = knowledge_service.list_objects(get_db(), object_type='guideline', status='published')
        return render_template('gi/guidelines.html', guidelines=objects)
