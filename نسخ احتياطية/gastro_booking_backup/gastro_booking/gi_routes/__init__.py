"""Register all GI integration routes on Gastro25 Flask app.

Note: ``gi_import/`` is reference-only and must never be registered here
(see GI_IMPORT.md / SITE_AUDIT.md).
"""

from __future__ import annotations

from gi_routes.ai import register_ai_routes
from gi_routes.assessment import register_assessment_routes
from gi_routes.cds import register_cds_routes
from gi_routes.history_ai import register_history_ai_routes
from gi_routes.interpretation import register_interpretation_routes
from gi_routes.investigation_planning import register_investigation_planning_routes
from gi_routes.management_plan import register_management_plan_routes
from gi_routes.documentation_ai import register_documentation_ai_routes
from gi_routes.patient_journey_ai import register_patient_journey_ai_routes
from gi_routes.analytics import register_analytics_routes
from gi_routes.attendance import register_attendance_routes
from gi_routes.governance import register_governance_routes
from gi_routes.journey import register_journey_routes
from gi_routes.permissions import register_permission_routes
from gi_routes.roster import register_roster_routes
from gi_routes.clinical import register_clinical_routes
from gi_routes.knowledge import register_knowledge_routes
from gi_routes.registry import register_registry_routes
from gi_routes.research import register_research_routes
from gi_routes.search import register_search_extension
from gi_routes.users import register_user_api_routes
from gi_routes.workforce import register_workforce_routes
from gi_routes.laboratory import register_laboratory_routes
from gi_routes.history_templates import register_history_template_routes
from gi_routes.history_ai_training import register_history_ai_training_routes
from gi_routes.dept_ops import register_dept_ops_routes
from gi_routes.platform_phases import register_platform_phase_routes
from gi_platform.catalogue_migrate import migrate_knowledge_catalogue, migrate_research_catalogue, patch_investigation_rules


def register_all_gi_routes(app, *, get_db, db_path, login_required, roles_required):
    import sqlite3
    dbconn = sqlite3.connect(db_path)
    dbconn.row_factory = sqlite3.Row
    try:
        migrate_knowledge_catalogue(dbconn)
        migrate_research_catalogue(dbconn)
        patch_investigation_rules(dbconn)
    except Exception as exc:
        app.logger.warning('GI catalogue migration: %s', exc)
    dbconn.close()
    register_knowledge_routes(app, get_db=get_db, login_required=login_required, roles_required=roles_required)
    register_research_routes(app, get_db=get_db, login_required=login_required, roles_required=roles_required)
    register_clinical_routes(app, get_db=get_db, login_required=login_required, roles_required=roles_required)
    register_governance_routes(app, get_db=get_db, login_required=login_required, roles_required=roles_required)
    register_roster_routes(app, get_db=get_db, login_required=login_required, roles_required=roles_required)
    register_attendance_routes(app, get_db=get_db, login_required=login_required, roles_required=roles_required)
    register_permission_routes(app, get_db=get_db, login_required=login_required, roles_required=roles_required)
    register_journey_routes(app, get_db=get_db, login_required=login_required, roles_required=roles_required)
    register_ai_routes(app, get_db=get_db, login_required=login_required, roles_required=roles_required)
    register_cds_routes(app, get_db=get_db, login_required=login_required, roles_required=roles_required)
    register_history_ai_routes(app, get_db=get_db, login_required=login_required, roles_required=roles_required)
    register_assessment_routes(app, get_db=get_db, login_required=login_required, roles_required=roles_required)
    register_interpretation_routes(app, get_db=get_db, login_required=login_required, roles_required=roles_required)
    register_investigation_planning_routes(app, get_db=get_db, login_required=login_required, roles_required=roles_required)
    register_management_plan_routes(app, get_db=get_db, login_required=login_required, roles_required=roles_required)
    register_documentation_ai_routes(app, get_db=get_db, login_required=login_required, roles_required=roles_required)
    register_patient_journey_ai_routes(app, get_db=get_db, login_required=login_required, roles_required=roles_required)
    register_analytics_routes(app, get_db=get_db, login_required=login_required, roles_required=roles_required)
    register_registry_routes(app, get_db=get_db, login_required=login_required, roles_required=roles_required)
    register_workforce_routes(app, get_db=get_db, login_required=login_required, roles_required=roles_required)
    register_laboratory_routes(app, get_db=get_db, login_required=login_required, roles_required=roles_required)
    register_history_template_routes(app, get_db=get_db, login_required=login_required, roles_required=roles_required)
    register_history_ai_training_routes(app, get_db=get_db, login_required=login_required, roles_required=roles_required)
    register_dept_ops_routes(app, get_db=get_db, login_required=login_required, roles_required=roles_required)
    register_platform_phase_routes(app, get_db=get_db, login_required=login_required, roles_required=roles_required)
    register_user_api_routes(app, get_db=get_db, login_required=login_required, roles_required=roles_required)
    register_search_extension(app, get_db=get_db)
