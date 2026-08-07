"""
Initial RBAC data, for seeding only.

IMPORTANT DISTINCTION: this file existing does not contradict "don't
hardcode roles/permissions in Python." Nothing in the running
application imports this module at request time — app/engines/
permission_engine.py queries the `roles`/`permissions`/`role_permissions`
tables directly and has no import of this file at all. This module is
read exactly once per environment, by seed_initial_rbac() in
app/modules/rbac/services.py (invoked via scripts/seed_rbac.py), the same
way you'd seed any other reference data (a countries table, a currency
list) from a fixture file. After seeding, the database is the only
source of truth; changing a role's permissions after this point means
calling assign_permission()/revoke_permission() (or, from Sprint 1B
onward, the admin UI) — editing this file again does nothing unless you
re-run the seed script, and re-running it never overwrites hand-made
changes (see seed_initial_rbac()'s upsert-only logic).
"""

PERMISSIONS = [
    {"code": "user:manage", "name": "Manage Users", "category": "users",
     "description": "Create, edit, change role, deactivate/reactivate user accounts."},
    {"code": "user:view", "name": "View User Directory", "category": "users",
     "description": "View the list of users and their profiles."},

    {"code": "audit_log:view", "name": "View Audit Log", "category": "audit",
     "description": "View the system-wide audit trail."},

    {"code": "knowledge_library:edit", "name": "Edit Knowledge Library", "category": "knowledge_library",
     "description": "Create and modify official guideline documents."},
    {"code": "knowledge_library:suggest", "name": "Suggest Knowledge Library Changes", "category": "knowledge_library",
     "description": "Submit suggested edits to guideline documents for review."},
    {"code": "knowledge_library:view", "name": "View Knowledge Library", "category": "knowledge_library",
     "description": "View official guideline documents."},

    {"code": "research:export", "name": "Export Research Data", "category": "research",
     "description": "Export research datasets. Restricted to authorized senior users."},
    {"code": "research:view", "name": "View Research Data", "category": "research",
     "description": "View research datasets."},
    {"code": "research:edit", "name": "Edit Research Data", "category": "research",
     "description": "Modify research datasets."},
    {"code": "research:variable_manage", "name": "Manage Research Variables", "category": "research",
     "description": "Create, update, version and archive research variable definitions. Head of Department only."},
    {"code": "research:variable_enter", "name": "Enter Research Variable Values", "category": "research",
     "description": "Enter manual research variable values without modifying the clinical record."},
    {"code": "research:study_manage", "name": "Manage Research Studies", "category": "research",
     "description": "Create, update, archive research studies and cohort criteria. Head of Department only."},
    {"code": "research:study_review", "name": "Review Research Cases", "category": "research",
     "description": "Review and manage assigned research study cases."},

    {"code": "report:sign", "name": "Sign Reports", "category": "reports",
     "description": "Finalize and sign endoscopy/procedure reports."},
    {"code": "report:draft", "name": "Draft Reports", "category": "reports",
     "description": "Create and edit draft reports."},
    {"code": "report:view", "name": "View Reports", "category": "reports",
     "description": "View finalized reports."},

    {"code": "patient:view", "name": "View Patients", "category": "patients",
     "description": "View patient records."},
    {"code": "patient:edit", "name": "Edit Patients", "category": "patients",
     "description": "Edit patient records."},

    {"code": "appointment:view", "name": "View Appointments", "category": "appointments",
     "description": "View the appointment schedule."},
    {"code": "appointment:edit", "name": "Manage Appointments", "category": "appointments",
     "description": "Create, reschedule, check in, complete, cancel, or mark appointments "
                     "as no-show. Granted to scheduling staff and on-call senior clinical roles."},
    {"code": "appointment:override", "name": "Override Booking Restrictions", "category": "appointments",
     "description": "Override Sunday/holiday/daily-cap restrictions when booking endoscopy slots."},
    {"code": "appointment:capacity_manage", "name": "Manage Booking Capacity", "category": "appointments",
     "description": "Change department endoscopy daily caps, sub-quota, and holiday calendar."},

    {"code": "procedure_catalogue:manage", "name": "Manage Procedure Catalogue", "category": "procedures",
     "description": "Add, edit, archive, or restore procedure types and endoscopy rooms. "
                     "Sprint 2B: administrator-tier, mirrors user:manage -- not the same "
                     "permission as booking or running an actual procedure."},
    {"code": "procedure:view", "name": "View Procedures", "category": "procedures",
     "description": "View procedure bookings, the daily endoscopy list, and the waiting list."},
    {"code": "procedure:edit", "name": "Book Procedures", "category": "procedures",
     "description": "Create a procedure booking for a procedure type that does NOT require "
                     "special authorization, change its procedure type/priority, and "
                     "assign/reassign its endoscopist or room. Sprint 2B: explicit product "
                     "decision -- a procedure type flagged requires_special_authorization in "
                     "the catalogue requires procedure:special_authorization instead (see "
                     "that permission's description). This is a policy/authorization "
                     "distinction the catalogue controls, not a clinical-complexity judgment "
                     "encoded here."},
    {"code": "procedure:workflow", "name": "Run Procedure Workflow", "category": "procedures",
     "description": "Move a procedure through the daily workflow (waiting list, ready, in "
                     "room, finished, cancelled) and assign/reassign its room. Sprint 2B: "
                     "explicit product decision -- day-to-day endoscopy-unit workflow is "
                     "nursing-driven, so this is deliberately broader than procedure:edit "
                     "and is unaffected by whether the procedure type requires special "
                     "authorization."},
    {"code": "procedure:special_authorization", "name": "Book Advanced Procedures", "category": "procedures",
     "description": "Book advanced or restricted procedure types (for example ERCP, EUS, advanced therapeutic "
                     "endoscopy). Required when the catalogue marks a type as requires_special_authorization. "
                     "Granted to Consultant level and above."},

    {"code": "procedure_execution:view", "name": "View Procedure Execution", "category": "procedure_execution",
     "description": "View procedure execution sessions, team assignments, time tracking, "
                     "sedation, safety checklist, and outcomes. Sprint 2C: same visibility "
                     "boundary as procedure:view."},
    {"code": "procedure_execution:edit", "name": "Edit Procedure Execution", "category": "procedure_execution",
     "description": "Edit team assignments, time tracking, sedation category, safety "
                     "checklist, procedure outcome, and cancel during execution. Sprint 2C: "
                     "mirrors procedure:workflow's role set -- day-to-day execution is "
                     "nursing-driven."},

    {"code": "encounter:view", "name": "View Clinical Encounters", "category": "encounters",
     "description": "View clinical encounters and encounter hubs."},
    {"code": "encounter:create", "name": "Create Clinical Encounters", "category": "encounters",
     "description": "Start and close clinical encounters (OPD, admission, follow-up)."},

    {"code": "investigation:view", "name": "View Investigations", "category": "investigations",
     "description": "View investigation orders, laboratory results, imaging studies, and timelines."},
    {"code": "investigation:request", "name": "Request Investigations", "category": "investigations",
     "description": "Place investigation orders and mark samples collected."},
    {"code": "investigation:result_enter", "name": "Enter Investigation Results", "category": "investigations",
     "description": "Enter laboratory values and imaging findings."},
    {"code": "investigation:review", "name": "Review Investigations", "category": "investigations",
     "description": "Review and sign off available investigation results."},
    {"code": "investigation:catalogue_manage", "name": "Manage Investigation Catalogue", "category": "investigations",
     "description": "Add, edit, archive investigation catalogue items and panels."},

    {"code": "medication:view", "name": "View Medications", "category": "medications",
     "description": "View medication lists and patient medication timeline."},
    {"code": "medication:document", "name": "Document Medications", "category": "medications",
     "description": "Add, edit, and stop medication entries on encounters."},
    {"code": "medication:review", "name": "Review Medications", "category": "medications",
     "description": "Review and sign off medication entries."},
    {"code": "medication:catalogue_manage", "name": "Manage Medication Catalogue", "category": "medications",
     "description": "Add, edit, archive medication formulary items."},

    {"code": "history:view", "name": "View Clinical History", "category": "clinical_history",
     "description": "View adaptive history sessions, narratives, and follow-up entries."},
    {"code": "history:document", "name": "Document Clinical History", "category": "clinical_history",
     "description": "Conduct adaptive interviews, edit generated history narratives."},
    {"code": "history:confirm_diagnosis", "name": "Confirm Diagnosis", "category": "clinical_history",
     "description": "Confirm working diagnosis and access management guidance."},
    {"code": "history:follow_up", "name": "Record Follow-up", "category": "clinical_history",
     "description": "Create chronological follow-up entries (append-only)."},
    {"code": "history:catalogue_manage", "name": "Manage History Catalogue", "category": "clinical_history",
     "description": "Manage chief complaints, question trees, and reasoning rules."},

    {"code": "workforce:view_own", "name": "View Own Portfolio", "category": "workforce",
     "description": "View own auto-generated portfolio, dashboard and performance analytics."},
    {"code": "workforce:view_department", "name": "View Department Training", "category": "workforce",
     "description": "Monitor all trainees and department workload summaries. Head of Department."},
    {"code": "workforce:supervise", "name": "Supervise Portfolio Entries", "category": "workforce",
     "description": "Supervisor-verify portfolio entries for official training statistics."},
    {"code": "workforce:verify_department", "name": "Department Portfolio Verification", "category": "workforce",
     "description": "Department-level verification and locking of portfolio entries. Head of Department."},
    {"code": "workforce:adjust_attendance", "name": "Adjust Attendance", "category": "workforce",
     "description": "Manual attendance adjustments for teaching, meetings, leave, conferences. HoD only."},

    {"code": "dept_ops:view", "name": "View Department Operations", "category": "dept_ops",
     "description": "View department operations dashboards, rooms, scopes, waiting list and resources."},
    {"code": "dept_ops:manage", "name": "Manage Department Operations", "category": "dept_ops",
     "description": "Full department operations management. Head of Department."},
    {"code": "dept_ops:room_manage", "name": "Manage Room Operations", "category": "dept_ops",
     "description": "Update room status, staff assignments and schedule slots."},
    {"code": "dept_ops:scope_manage", "name": "Manage Endoscopes", "category": "dept_ops",
     "description": "Register scopes, update status, maintenance and reprocessing."},
    {"code": "dept_ops:consumable_manage", "name": "Manage Consumables", "category": "dept_ops",
     "description": "Manage consumable inventory and stock movements."},
    {"code": "dept_ops:waiting_list", "name": "Manage Waiting List", "category": "dept_ops",
     "description": "Add and schedule waiting list entries."},
    {"code": "dept_ops:roster_manage", "name": "Manage Duty Roster", "category": "dept_ops",
     "description": "Create and edit duty roster entries."},
    {"code": "dept_ops:announce", "name": "Publish Announcements", "category": "dept_ops",
     "description": "Publish department announcements and notices."},
    {"code": "dept_ops:message", "name": "Send Internal Messages", "category": "dept_ops",
     "description": "Send internal department messages."},

    {"code": "governance:view", "name": "View Clinical Governance", "category": "governance",
     "description": "View governance dashboard, incidents, M&M, audits and documents."},
    {"code": "governance:manage", "name": "Manage Clinical Governance", "category": "governance",
     "description": "Full governance administration. Head of Department."},
    {"code": "governance:incident_create", "name": "Report Clinical Incidents", "category": "governance",
     "description": "Create incident and near-miss reports."},
    {"code": "governance:incident_review", "name": "Review Clinical Incidents", "category": "governance",
     "description": "Review, investigate and close incident reports."},
    {"code": "governance:mm_participate", "name": "Participate in M&M", "category": "governance",
     "description": "Create and participate in mortality & morbidity conferences."},
    {"code": "governance:audit_manage", "name": "Manage Audit Projects", "category": "governance",
     "description": "Create and manage departmental audit projects."},
    {"code": "governance:document_manage", "name": "Manage Controlled Documents", "category": "governance",
     "description": "Create, approve and version controlled SOPs, protocols and policies."},
    {"code": "governance:kpi_view", "name": "View Quality Indicators", "category": "governance",
     "description": "View automatically calculated quality KPIs."},
    {"code": "governance:checklist_complete", "name": "Complete Governance Checklists", "category": "governance",
     "description": "Record checklist compliance for safety and reprocessing."},

    {"code": "branding:manage", "name": "Manage Branding", "category": "branding",
     "description": "Configure hospital white-label branding, logos, colours and theme."},

    {"code": "workforce_identity:invite_manage", "name": "Manage Training Invitations", "category": "workforce_identity",
     "description": "Create, revoke and manage trainee invitation links."},
    {"code": "workforce_identity:account_manage", "name": "Manage Training Account Lifecycle", "category": "workforce_identity",
     "description": "Extend, suspend, or close time-limited training accounts."},
    {"code": "workforce_identity:duty_coordinate", "name": "Coordinate Duty Schedules", "category": "workforce_identity",
     "description": "Approve shift swaps and manage duty schedule coordination."},
    {"code": "workforce_identity:duty_view", "name": "View Duty Schedule", "category": "workforce_identity",
     "description": "View personal duties and today's on-call team."},
    {"code": "workforce_identity:swap_request", "name": "Request Duty Swaps", "category": "workforce_identity",
     "description": "Submit shift swap requests."},
    {"code": "workforce_identity:dashboard_view", "name": "View Workforce Identity Dashboard", "category": "workforce_identity",
     "description": "View HoD workforce identity dashboard with trainees, invitations, and duty overview."},

    {"code": "clinical_ai:view", "name": "View Clinical AI", "category": "clinical_ai",
     "description": "View Clinical AI infrastructure status and session metadata."},
    {"code": "clinical_ai:use", "name": "Use Clinical AI", "category": "clinical_ai",
     "description": "Execute Clinical AI infrastructure requests. Trainee roles require CLINICAL_AI_TRAINEE_ENABLED."},
    {"code": "clinical_ai:configure", "name": "Configure Clinical AI", "category": "clinical_ai",
     "description": "Inspect and configure Clinical AI provider settings. Head of Department only."},

    {"code": "analytics:view", "name": "View Analytics", "category": "analytics",
     "description": "View clinical analytics metrics and snapshots."},
    {"code": "analytics:configure", "name": "Configure Analytics", "category": "analytics",
     "description": "Configure metric definitions and activation status. Head of Department only."},
    {"code": "analytics:export", "name": "Export Analytics", "category": "analytics",
     "description": "Export analytics metric results."},

    {"code": "inpatient:view", "name": "View Ward Beds", "category": "inpatient",
     "description": "View ward, room, and bed occupancy boards."},
    {"code": "inpatient:manage", "name": "Manage Ward Beds", "category": "inpatient",
     "description": "Admit, transfer, discharge, and update bed status."},

    {"code": "consult:view", "name": "View Consult Requests", "category": "consult",
     "description": "View inter-department consultation requests."},
    {"code": "consult:request", "name": "Request Consultation", "category": "consult",
     "description": "Create consultation requests."},
    {"code": "consult:respond", "name": "Respond to Consultations", "category": "consult",
     "description": "Accept, complete, reject consultation requests."},

    {"code": "patient_document:view", "name": "View Patient Documents", "category": "patient_documents",
     "description": "View uploaded patient files and external reports."},
    {"code": "patient_document:upload", "name": "Upload Patient Documents", "category": "patient_documents",
     "description": "Upload PDFs, images, and external reports to patient record."},

    {"code": "consent:view", "name": "View Consent Forms", "category": "consent",
     "description": "View procedure consent forms and records."},
    {"code": "consent:sign", "name": "Sign Consent Forms", "category": "consent",
     "description": "Record patient consent signatures."},
    {"code": "consent:manage", "name": "Manage Consent Templates", "category": "consent",
     "description": "Configure consent form templates. Head of Department."},

    {"code": "clinical_document:view", "name": "View Clinical Documents", "category": "clinical_documents",
     "description": "View discharge summaries, certificates, and letters."},
    {"code": "clinical_document:create", "name": "Create Clinical Documents", "category": "clinical_documents",
     "description": "Generate discharge summaries and clinical letters."},
    {"code": "clinical_document:print", "name": "Print Clinical Documents", "category": "clinical_documents",
     "description": "Print branded certificates and discharge summaries."},

    {"code": "notification:view", "name": "View Notifications", "category": "notifications",
     "description": "View internal notification centre."},

    {"code": "calendar:view", "name": "View Department Calendar", "category": "calendar",
     "description": "View unified calendar of clinics, procedures, duties, and education."},

    {"code": "education:view", "name": "View Education Activities", "category": "education",
     "description": "View conferences, CME, journal clubs, and seminars."},
    {"code": "education:record", "name": "Record Education Activities", "category": "education",
     "description": "Log attendance at training and CME events."},
    {"code": "education:manage", "name": "Manage Education Catalogue", "category": "education",
     "description": "Manage department education events. Head of Department."},

    {"code": "data:export", "name": "Export Clinical Data", "category": "data_exchange",
     "description": "Export patients, registries, and backups."},
    {"code": "data:import", "name": "Import Clinical Data", "category": "data_exchange",
     "description": "Import CSV/JSON data. Head of Department."},

    {"code": "archive_storage:view", "name": "View Archive Storage", "category": "archive_storage",
     "description": "Search and restore archived attachments."},
    {"code": "archive_storage:manage", "name": "Manage Archive Policies", "category": "archive_storage",
     "description": "Configure retention and archive policies."},

    {"code": "search:global", "name": "Global Search", "category": "search",
     "description": "Search across patients, appointments, and procedures."},

    {"code": "pharma_banner:manage", "name": "Manage Educational Banner", "category": "branding",
     "description": "Upload rotating pharmaceutical educational banner slides."},
]

ROLES = [
    {"code": "system_administrator", "name": "System Administrator",
     "description": "Bootstrap/system-level account. Not a clinical role — see "
                     "scripts/bootstrap_superadmin.py. Auto-granted every permission "
                     "at seed time as a secondary defense; the primary access "
                     "guarantee is User.is_superuser, not this role's grants.",
     "is_system": True},
    {"code": "head_of_department", "name": "Head of Department",
     "description": "Department lead. Full administrative authority.", "is_system": True},
    {"code": "core_consultant", "name": "Core Consultant",
     "description": "Senior consultant with Knowledge Library and user-management authority.",
     "is_system": True},
    {"code": "consultant", "name": "Consultant",
     "description": "Attending consultant.", "is_system": True},
    {"code": "senior_registrar", "name": "Senior Registrar",
     "description": "Senior registrar or fellow.", "is_system": True},
    {"code": "postgraduate_trainee", "name": "Postgraduate Trainee",
     "description": "Postgraduate clinical trainee — can book basic endoscopy only, not advanced procedures.",
     "is_system": True},
    {"code": "house_officer", "name": "House Officer",
     "description": "Most junior doctor — clinical documentation without procedure booking.",
     "is_system": True},
    {"code": "nurse", "name": "Ward Nurse",
     "description": "Ward nursing staff.", "is_system": True},
    {"code": "endoscopy_nurse", "name": "Endoscopy Nurse",
     "description": "Endoscopy unit nursing staff.", "is_system": True},
    {"code": "endoscopy_technician", "name": "Endoscopy Technician",
     "description": "Endoscopy unit technician.", "is_system": True},
    {"code": "reception_staff", "name": "Appointment & Reception Staff",
     "description": "Front desk, registration and appointment scheduling.", "is_system": True},
    {"code": "research_coordinator", "name": "Research Coordinator",
     "description": "Coordinates the research registry.", "is_system": True},
    {"code": "admin_staff", "name": "Administrative Staff",
     "description": "Non-clinical administrative staff.", "is_system": True},
    {"code": "visiting_trainee", "name": "Visiting Trainee",
     "description": "Temporary visiting trainee with time-limited account.", "is_system": True},
    {"code": "training_coordinator", "name": "Training Coordinator",
     "description": "Manages trainee invitations and account lifecycle. Delegated by HoD.", "is_system": True},
    {"code": "duty_coordinator", "name": "Duty Coordinator",
     "description": "Coordinates duty schedules and approves shift swaps.", "is_system": True},
]

# The role assigned to the bootstrap Super Administrator account (see
# scripts/bootstrap_superadmin.py and app/modules/users/services.py's
# bootstrap_superadmin()). Its actual access guarantee comes from
# User.is_superuser (checked in app/engines/permission_engine.py), not
# from this role's grants — but seed_initial_rbac() also auto-grants it
# every permission that exists, as a secondary defense, so it's
# deliberately excluded from the hand-maintained ROLE_PERMISSIONS dict
# below (see seed_initial_rbac()'s special-cased loop for this role).
SUPERUSER_ROLE_CODE = "system_administrator"

# role_code -> [permission_code, ...]. This is literally the same
# assignment the old ROLE_PERMISSIONS dict encoded — the difference is
# this is read ONCE at seed time to populate role_permissions rows, not
# consulted by the engine on every request thereafter.
ROLE_PERMISSIONS = {
    "head_of_department": {
        "knowledge_library:edit", "knowledge_library:view",
        "research:export", "research:view", "research:edit",
        "research:variable_manage", "research:variable_enter",
        "research:study_manage", "research:study_review",
        "report:sign", "report:draft", "report:view",
        "patient:view", "patient:edit",
        "appointment:view", "appointment:edit", "appointment:override", "appointment:capacity_manage",
        "procedure_catalogue:manage", "procedure:view", "procedure:edit",
        "procedure:workflow", "procedure:special_authorization",
        "procedure_execution:view", "procedure_execution:edit",
        "encounter:view", "encounter:create",
        "investigation:view", "investigation:request", "investigation:result_enter",
        "investigation:review", "investigation:catalogue_manage",
        "medication:view", "medication:document", "medication:review", "medication:catalogue_manage",
        "history:view", "history:document", "history:confirm_diagnosis", "history:follow_up", "history:catalogue_manage",
        "workforce:view_own", "workforce:view_department", "workforce:supervise", "workforce:verify_department", "workforce:adjust_attendance",
        "dept_ops:view", "dept_ops:manage", "dept_ops:room_manage", "dept_ops:scope_manage",
        "dept_ops:consumable_manage", "dept_ops:waiting_list", "dept_ops:roster_manage",
        "dept_ops:announce", "dept_ops:message",
        "governance:view", "governance:manage", "governance:incident_create", "governance:incident_review",
        "governance:mm_participate", "governance:audit_manage", "governance:document_manage",
        "governance:kpi_view", "governance:checklist_complete",
        "branding:manage",
        "workforce_identity:invite_manage", "workforce_identity:account_manage",
        "workforce_identity:duty_coordinate", "workforce_identity:duty_view",
        "workforce_identity:swap_request", "workforce_identity:dashboard_view",
        "user:manage", "user:view", "audit_log:view",
        "clinical_ai:view", "clinical_ai:use", "clinical_ai:configure",
        "analytics:view", "analytics:configure", "analytics:export",
        "inpatient:view", "inpatient:manage",
        "consult:view", "consult:request", "consult:respond",
        "patient_document:view", "patient_document:upload",
        "consent:view", "consent:sign", "consent:manage",
        "clinical_document:view", "clinical_document:create", "clinical_document:print",
        "notification:view",
        "calendar:view",
        "education:view", "education:record", "education:manage",
        "data:export", "data:import",
        "archive_storage:view", "archive_storage:manage",
        "search:global",
        "pharma_banner:manage",
    },
    "core_consultant": {
        "knowledge_library:edit", "knowledge_library:view",
        "research:export", "research:view", "research:edit",
        "research:variable_enter", "research:study_review",
        "report:sign", "report:draft", "report:view",
        "patient:view", "patient:edit",
        "appointment:view", "appointment:edit", "appointment:override",
        "procedure_catalogue:manage", "procedure:view", "procedure:edit",
        "procedure:workflow", "procedure:special_authorization",
        "procedure_execution:view", "procedure_execution:edit",
        "encounter:view", "encounter:create",
        "investigation:view", "investigation:request", "investigation:result_enter",
        "investigation:review", "investigation:catalogue_manage",
        "medication:view", "medication:document", "medication:review", "medication:catalogue_manage",
        "history:view", "history:document", "history:confirm_diagnosis", "history:follow_up", "history:catalogue_manage",
        "workforce:view_own", "workforce:supervise",
        "dept_ops:view", "dept_ops:room_manage", "dept_ops:scope_manage", "dept_ops:message",
        "governance:view", "governance:incident_create", "governance:incident_review",
        "governance:mm_participate", "governance:kpi_view",
        "user:manage", "user:view", "audit_log:view",
        "clinical_ai:view", "clinical_ai:use",
        "analytics:view",
        "inpatient:view", "inpatient:manage",
        "consult:view", "consult:request", "consult:respond",
        "patient_document:view", "patient_document:upload",
        "consent:view", "consent:sign", "consent:manage",
        "clinical_document:view", "clinical_document:create", "clinical_document:print",
        "notification:view", "calendar:view",
        "education:view", "education:record", "education:manage",
        "data:export", "archive_storage:view",
        "search:global", "pharma_banner:manage",
    },
    "consultant": {
        "research:view", "research:variable_enter", "research:study_review",
        "report:sign", "report:draft", "report:view",
        "patient:view", "patient:edit",
        "appointment:view", "appointment:edit", "appointment:override",
        "procedure:view", "procedure:edit", "procedure:workflow",
        "procedure:special_authorization",
        "procedure_execution:view", "procedure_execution:edit",
        "encounter:view", "encounter:create",
        "investigation:view", "investigation:request", "investigation:review",
        "medication:view", "medication:document", "medication:review",
        "history:view", "history:document", "history:confirm_diagnosis", "history:follow_up",
        "workforce:view_own", "workforce:supervise",
        "dept_ops:view", "dept_ops:message",
        "governance:view", "governance:incident_create", "governance:mm_participate", "governance:kpi_view",
        "clinical_ai:view", "clinical_ai:use",
        "analytics:view",
        "inpatient:view",
        "consult:view", "consult:request", "consult:respond",
        "patient_document:view", "patient_document:upload",
        "consent:view", "consent:sign",
        "clinical_document:view", "clinical_document:create", "clinical_document:print",
        "notification:view", "calendar:view",
        "education:view", "education:record",
        "search:global",
    },
    "senior_registrar": {
        "research:variable_enter",
        "report:draft", "report:view",
        "patient:view", "patient:edit",
        "appointment:view", "appointment:edit",
        "procedure:view", "procedure:edit", "procedure:workflow",
        "procedure_execution:view", "procedure_execution:edit",
        "encounter:view", "encounter:create",
        "investigation:view", "investigation:request", "investigation:result_enter",
        "medication:view", "medication:document",
        "history:view", "history:document", "history:follow_up",
        "workforce:view_own",
        "workforce_identity:duty_view", "workforce_identity:swap_request",
        "clinical_ai:view", "clinical_ai:use",
        "analytics:view",
        "inpatient:view",
        "consult:view", "consult:request",
        "patient_document:view", "patient_document:upload",
        "consent:view", "consent:sign",
        "clinical_document:view", "clinical_document:create",
        "notification:view", "calendar:view",
        "education:view", "education:record",
        "search:global",
    },
    "postgraduate_trainee": {
        "patient:view", "patient:edit",
        "appointment:view",
        "report:draft", "report:view",
        "encounter:view", "encounter:create",
        "investigation:view", "investigation:request", "investigation:result_enter",
        "medication:view", "medication:document",
        "history:view", "history:document", "history:follow_up",
        "procedure:view", "procedure:edit", "procedure:workflow",
        "procedure_execution:view", "procedure_execution:edit",
        "research:variable_enter",
        "workforce:view_own",
        "workforce_identity:duty_view", "workforce_identity:swap_request",
        "clinical_ai:view", "clinical_ai:use",
        "analytics:view",
        "inpatient:view",
        "consult:view", "consult:request",
        "patient_document:view", "patient_document:upload",
        "consent:view", "consent:sign",
        "clinical_document:view", "clinical_document:create",
        "notification:view", "calendar:view",
        "education:view", "education:record",
        "search:global",
    },
    "house_officer": {
        "patient:view", "patient:edit",
        "appointment:view",
        "report:view",
        "encounter:view", "encounter:create",
        "investigation:view", "investigation:request", "investigation:result_enter",
        "medication:view", "medication:document",
        "history:view", "history:document", "history:follow_up",
        "research:variable_enter",
        "workforce:view_own",
        "workforce_identity:duty_view", "workforce_identity:swap_request",
        "clinical_ai:view", "clinical_ai:use",
        "analytics:view",
        "inpatient:view",
        "consult:view", "consult:request",
        "patient_document:view",
        "consent:view",
        "clinical_document:view",
        "notification:view", "calendar:view",
        "education:view", "education:record",
        "search:global",
    },
    "nurse": {
        "patient:view", "appointment:view", "report:view",
        "procedure:view", "procedure:workflow",
        "procedure_execution:view", "procedure_execution:edit",
        "medication:view",
        "history:view",
        "workforce:view_own",
        "dept_ops:view", "dept_ops:room_manage", "dept_ops:message",
        "governance:incident_create", "governance:checklist_complete",
        # NOT procedure:edit / procedure:special_authorization — per
        # explicit Sprint 2B decision, nurses run the day-to-day
        # endoscopy-unit workflow (waiting list / ready / in room /
        # finished / cancelled, plus room assignment) alongside doctors,
        # but do not book procedures or decide who performs them.
        "inpatient:view", "inpatient:manage",
        "patient_document:view",
        "consent:view",
        "notification:view", "calendar:view",
        "search:global",
    },
    "research_coordinator": {
        "research:view", "research:edit", "research:variable_enter",
        # NOT research:export — restricted to authorized senior users per
        # project rules; grant it to a specific role/user explicitly if a
        # research coordinator is separately authorized, rather than
        # broadening this default set.
        # NOT appointment:view/edit, NOT any procedure:* — mirrors this
        # role's existing exclusion from patient:view; research
        # coordinators don't see clinical scheduling/procedure data any
        # more than they see patient records.
    },
    "admin_staff": {
        "patient:view", "appointment:view", "user:view",
        # NOT appointment:edit — assumption, mirrored from patient:edit's
        # existing exclusion of this role, per explicit Sprint 2A decision
        # restricting booking authority to Head of Department / Core
        # Consultant only. The daily-appointment-limit feature was
        # requested alongside broader booking access, but the explicit
        # follow-up answer restricted appointment:edit to those two roles
        # specifically -- if front-desk booking access is wanted later,
        # grant appointment:edit to admin_staff via the RBAC admin
        # utilities (no code change needed).
        "procedure:view", "procedure_execution:view",
        "encounter:view",
        "investigation:view",
        "medication:view",
        "history:view",
        # NOT procedure:edit/workflow/special_authorization — mirrors this
        # role's existing appointment:edit exclusion; admin staff see the
        # daily list/schedule but don't run clinical procedure workflow.
        # NOT procedure_execution:edit — view-only, same boundary as
        # procedure:workflow exclusion above.
    },
    "endoscopy_nurse": {
        "patient:view", "appointment:view", "report:view",
        "procedure:view", "procedure:workflow",
        "procedure_execution:view", "procedure_execution:edit",
        "medication:view", "history:view",
        "workforce:view_own",
        "dept_ops:view", "dept_ops:room_manage", "dept_ops:scope_manage", "dept_ops:message",
        "governance:incident_create", "governance:checklist_complete",
        "inpatient:view", "inpatient:manage",
        "patient_document:view",
        "consent:view",
        "notification:view", "calendar:view",
        "search:global",
    },
    "endoscopy_technician": {
        "patient:view", "appointment:view", "report:view",
        "procedure:view", "procedure:workflow",
        "procedure_execution:view", "procedure_execution:edit",
        "workforce:view_own",
        "dept_ops:view", "dept_ops:room_manage", "dept_ops:scope_manage", "dept_ops:message",
        "governance:incident_create", "governance:checklist_complete",
        "inpatient:view",
        "patient_document:view",
        "notification:view", "calendar:view",
        "search:global",
    },
    "reception_staff": {
        "patient:view", "patient:edit", "appointment:view", "appointment:edit",
        "procedure:view", "procedure_execution:view", "encounter:view",
        "user:view",
        "dept_ops:view", "dept_ops:waiting_list", "dept_ops:message",
        "patient_document:view",
        "notification:view", "calendar:view",
        "search:global",
    },
    "visiting_trainee": {
        "patient:view", "report:view", "encounter:view",
        "investigation:view", "medication:view", "history:view",
        "workforce:view_own",
        "workforce_identity:duty_view", "workforce_identity:swap_request",
        "user:view",
        "clinical_ai:view", "clinical_ai:use",
    },
    "training_coordinator": {
        "user:view", "workforce:view_department", "workforce:view_own",
        "workforce_identity:invite_manage", "workforce_identity:account_manage",
        "workforce_identity:duty_view", "workforce_identity:dashboard_view",
    },
    "duty_coordinator": {
        "user:view", "dept_ops:view", "dept_ops:roster_manage",
        "workforce:view_own",
        "workforce_identity:duty_coordinate", "workforce_identity:duty_view",
        "workforce_identity:swap_request",
    },
}
