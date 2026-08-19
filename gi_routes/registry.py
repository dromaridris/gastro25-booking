"""Clinical GI registry dashboard and procedure/diagnosis hubs."""

from flask import flash, redirect, render_template, request, session, url_for

from gi_platform import clinical_registry_service as crs
from gi_platform.clinical_registry_catalog import BUILTIN_DISEASE_GROUPS, PROCEDURE_CARDS
from gi_registry.master_registry import BRANCH_REGISTRY, gi_module_inventory, list_branches


CLINICAL_REGISTRY_ROLES = (
    'admin', 'specialist', 'hod', 'consultant', 'registrar', 'nurse_manager',
    'house_officer', 'pg_trainee', 'general_endoscopy', 'staff_nurse',
)
DIAGNOSIS_MANAGE_ROLES = ('admin', 'specialist', 'hod', 'consultant')


def register_registry_routes(app, *, get_db, login_required, roles_required):
    @app.route('/gi-registry')
    @login_required
    @roles_required(*CLINICAL_REGISTRY_ROLES)
    def gi_registry_dashboard():
        db = get_db()
        period = (request.args.get('period') or 'all').strip()
        data = crs.build_dashboard(db, period=period)
        from gi_platform import nav_permissions as navperm
        return render_template(
            'gi/clinical_registry_dashboard.html',
            **data,
            module_intro=navperm.intro('clinical_registry'),
            can_manage_diagnoses=session.get('role') in DIAGNOSIS_MANAGE_ROLES,
        )

    @app.route('/gi-registry/dev-map')
    @login_required
    @roles_required('admin', 'specialist')
    def gi_registry_dev_map():
        """Developer-only module inventory — hidden unless GASTRO25_DEV_MAP=1."""
        from gi_platform import nav_permissions as navperm
        if not navperm.dev_map_enabled():
            return ('Not found', 404)
        return render_template(
            'gi/registry_dev_map.html',
            branches=list_branches(),
            modules=gi_module_inventory(),
            branch_count=len(BRANCH_REGISTRY),
            module_intro=navperm.intro('registry_dev_map'),
        )

    @app.route('/gi-registry/procedure/<procedure_key>')
    @login_required
    @roles_required(*CLINICAL_REGISTRY_ROLES)
    def gi_registry_procedure_hub(procedure_key):
        db = get_db()
        hub = crs.procedure_hub(db, procedure_key)
        if not hub:
            flash('Procedure registry not found.', 'error')
            return redirect(url_for('gi_registry_dashboard'))
        from app import PROCEDURE_LABELS
        from procedure_extensions import ADVANCED_PROCEDURE_LABELS
        labels = {**PROCEDURE_LABELS, **ADVANCED_PROCEDURE_LABELS}
        return render_template(
            'gi/registry_procedure_hub.html',
            hub=hub,
            procedure_key=procedure_key,
            procedure_label=labels.get(procedure_key, hub['card']['title']),
        )

    @app.route('/gi-registry/diagnosis/<code>')
    @login_required
    @roles_required(*CLINICAL_REGISTRY_ROLES)
    def gi_registry_diagnosis_hub(code):
        db = get_db()
        hub = crs.diagnosis_hub(db, code)
        if not hub:
            flash('Diagnosis registry not found.', 'error')
            return redirect(url_for('gi_registry_dashboard'))
        return render_template('gi/registry_diagnosis_hub.html', hub=hub, code=code)

    @app.route('/gi-registry/diagnoses/add', methods=['POST'])
    @login_required
    @roles_required(*DIAGNOSIS_MANAGE_ROLES)
    def gi_registry_add_diagnosis():
        db = get_db()
        name = (request.form.get('disease_name') or '').strip()
        code = (request.form.get('disease_code') or '').strip()
        if not name:
            flash('Diagnosis name is required.', 'error')
            return redirect(url_for('gi_registry_dashboard') + '#diagnoses')
        try:
            crs.add_registry_diagnosis(
                db,
                disease_code=code or name.lower().replace(' ', '_'),
                disease_name=name,
                created_by=session.get('user_id'),
            )
            flash(f'Registry card added for {name}.', 'success')
        except Exception as exc:
            flash(str(exc), 'error')
        return redirect(url_for('gi_registry_dashboard') + '#diagnoses')
