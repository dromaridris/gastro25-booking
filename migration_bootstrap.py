"""Wire ward module and GI import into Gastro25 without modifying ERCP code."""

from __future__ import annotations

from flask import session, url_for

from procedure_extensions import (
    ADVANCED_PROCEDURES,
    ADVANCED_PROCEDURE_LABELS,
    booking_procedure_groups,
    merge_procedure_labels,
)
from gi_routes import register_all_gi_routes
from ward.routes import register_ward_routes
from db_schema_registry import ensure_all_schemas_for_path, install_schema_guard


def register_migration_extensions(app, *, app_globals, get_db, db_path, login_required, roles_required):
    """Register ward routes, extended booking procedures, and ward schema."""

    labels = app_globals['PROCEDURE_LABELS']
    labels.update(ADVANCED_PROCEDURE_LABELS)
    app_globals['ADVANCED_PROCEDURES'] = ADVANCED_PROCEDURES

    ensure_all_schemas_for_path(db_path)
    install_schema_guard(app, get_db)

    @app.before_request
    def _attach_current_user_id():
        from flask import request as flask_request
        if session.get('user_id') is not None:
            flask_request.current_user_id = session['user_id']

    register_ward_routes(app, login_required=login_required, roles_required=roles_required, get_db=get_db)
    from procedure_reports.routes import register_procedure_report_routes
    register_procedure_report_routes(app, get_db=get_db, login_required=login_required, roles_required=roles_required)
    from advanced_reports.routes import register_advanced_report_routes
    register_advanced_report_routes(app, get_db=get_db, login_required=login_required, roles_required=roles_required)
    from egd_reports.routes import register_egd_routes
    register_egd_routes(app, get_db=get_db, login_required=login_required, roles_required=roles_required)
    from colonoscopy_reports.routes import register_colonoscopy_routes
    register_colonoscopy_routes(app, get_db=get_db, login_required=login_required, roles_required=roles_required)
    register_all_gi_routes(
        app, get_db=get_db, db_path=db_path,
        login_required=login_required, roles_required=roles_required,
    )
    from mcq_bank.routes import register_mcq_bank_routes
    register_mcq_bank_routes(
        app, get_db=get_db, db_path=db_path,
        login_required=login_required, roles_required=roles_required,
    )
    from clinical_intelligence.routes import register_clinical_intelligence_routes
    register_clinical_intelligence_routes(
        app, get_db=get_db, login_required=login_required, roles_required=roles_required,
    )
    from clinical_knowledge_platform.workflow import register_ckp_routes
    register_ckp_routes(
        app, get_db=get_db, login_required=login_required, roles_required=roles_required,
    )
    from clinical_knowledge_platform.documentation.routes import register_documentation_routes
    register_documentation_routes(
        app, get_db=get_db, login_required=login_required, roles_required=roles_required,
    )
    from clinical_knowledge_platform.cds.routes import register_cds_routes
    register_cds_routes(
        app, get_db=get_db, login_required=login_required, roles_required=roles_required,
    )
    from clinical_knowledge_platform.longitudinal.routes import register_longitudinal_routes
    register_longitudinal_routes(
        app, get_db=get_db, login_required=login_required, roles_required=roles_required,
    )
    from clinical_knowledge_platform.research.routes import register_research_platform_routes
    register_research_platform_routes(
        app, get_db=get_db, login_required=login_required, roles_required=roles_required,
    )
    from clinical_knowledge_platform.enterprise.routes import register_enterprise_routes
    register_enterprise_routes(
        app, get_db=get_db, login_required=login_required, roles_required=roles_required,
    )

    # Orphan book/knowledge PDFs after extraction — free disk (patient docs untouched).
    try:
        from gi_platform.import_service import cleanup_stale_import_uploads
        cleanup_stale_import_uploads()
    except Exception:
        pass
    try:
        import os
        mcq_dir = os.path.join(os.path.dirname(__file__), 'data', 'mcq_bank_uploads')
        if os.path.isdir(mcq_dir):
            for name in os.listdir(mcq_dir):
                path = os.path.join(mcq_dir, name)
                if os.path.isfile(path):
                    try:
                        os.remove(path)
                    except OSError:
                        pass
    except Exception:
        pass

    @app.after_request
    def _track_clinical_activity(response):
        """Record site activity for attendance/logbook without modifying ERCP core."""
        from flask import request as flask_request
        try:
            if flask_request.method == 'POST' and session.get('user_id'):
                from gi_platform import activity_service
                dbconn = get_db()
                activity_service.try_record_from_request(
                    dbconn, user_id=session.get('user_id'),
                    method=flask_request.method, path=flask_request.path,
                )
        except Exception:
            pass
        return response

    @app.context_processor
    def _inject_migration_flags():
        def procedure_report_url(procedure_type, appointment_id):
            from advanced_reports.configs import PROCEDURE_REGISTRY
            from advanced_reports.procedure_catalog import DILATATION_ALIASES
            mapping = {
                'upper_gi': 'upper_gi_report_view',
                'colonoscopy': 'colonoscopy_report_view',
                'eus': 'eus_report_view',
                'capsule_endoscopy': 'capsule_report_view',
                'dilatation': 'dilatation_report_view',
            }
            for key, cfg in PROCEDURE_REGISTRY.items():
                if cfg['procedure_type'] in mapping:
                    continue
                mapping[cfg['procedure_type']] = f'{key}_report_view'
            if procedure_type in DILATATION_ALIASES:
                procedure_type = 'dilatation'
            endpoint = mapping.get(procedure_type)
            if endpoint and appointment_id:
                try:
                    return url_for(endpoint, appointment_id=appointment_id)
                except Exception:
                    return None
            return None
        groups = booking_procedure_groups(labels)
        return {
            'WARD_ENABLED': True,
            'GI_INTEGRATION_ENABLED': True,
            'PROCEDURE_LABELS': labels,
            'procedure_report_url': procedure_report_url,
            'booking_advanced': groups['advanced'],
        }
