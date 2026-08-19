"""Workforce & Training Platform constants — Sprint 7A."""

# Portfolio activity types (auto-generated from clinical work)
ACTIVITY_ENCOUNTER = "encounter"
ACTIVITY_HISTORY_TAKING = "history_taking"
ACTIVITY_DIAGNOSIS_CONFIRMATION = "diagnosis_confirmation"
ACTIVITY_FOLLOW_UP = "follow_up"
ACTIVITY_PROCEDURE = "procedure_participation"
ACTIVITY_REPORT_AUTHORED = "report_authored"
ACTIVITY_REPORT_SUPERVISED = "report_supervised"
ACTIVITY_LAB_REVIEW = "lab_review"
ACTIVITY_IMAGING_REVIEW = "imaging_review"
ACTIVITY_RESEARCH = "research_participation"
ACTIVITY_PROCEDURE_SKILL = "procedure_skill"

ALL_ACTIVITY_TYPES = (
    ACTIVITY_ENCOUNTER,
    ACTIVITY_HISTORY_TAKING,
    ACTIVITY_DIAGNOSIS_CONFIRMATION,
    ACTIVITY_FOLLOW_UP,
    ACTIVITY_PROCEDURE,
    ACTIVITY_REPORT_AUTHORED,
    ACTIVITY_REPORT_SUPERVISED,
    ACTIVITY_LAB_REVIEW,
    ACTIVITY_IMAGING_REVIEW,
    ACTIVITY_RESEARCH,
    ACTIVITY_PROCEDURE_SKILL,
)

# Procedure participation roles (from ProcedureSession team assignment)
ROLE_PRIMARY_OPERATOR = "primary_operator"
ROLE_ASSISTANT = "assistant"
ROLE_OBSERVER = "observer"
ROLE_REPORTING_PHYSICIAN = "reporting_physician"
ROLE_SEDATION_PHYSICIAN = "sedation_physician"
ROLE_ENDOSCOPY_NURSE = "endoscopy_nurse"
ROLE_TECHNICIAN = "technician"

ALL_PARTICIPATION_ROLES = (
    ROLE_PRIMARY_OPERATOR,
    ROLE_ASSISTANT,
    ROLE_OBSERVER,
    ROLE_REPORTING_PHYSICIAN,
    ROLE_SEDATION_PHYSICIAN,
    ROLE_ENDOSCOPY_NURSE,
    ROLE_TECHNICIAN,
)

# Trainee competency subtypes for procedure tallies
SUBTYPE_OBSERVED = "observed"
SUBTYPE_ASSISTED = "assisted"
SUBTYPE_INDEPENDENT = "independent"
SUBTYPE_POLYPECTOMY = "polypectomy"
SUBTYPE_BIOPSY = "biopsy"

# Verification lifecycle
VERIFY_DRAFT = "draft"
VERIFY_SUPERVISOR = "supervisor_verified"
VERIFY_DEPARTMENT = "department_verified"
VERIFY_LOCKED = "locked"

ALL_VERIFY_STATUSES = (VERIFY_DRAFT, VERIFY_SUPERVISOR, VERIFY_DEPARTMENT, VERIFY_LOCKED)

# Countable toward official training statistics
OFFICIAL_VERIFY_STATUSES = (VERIFY_SUPERVISOR, VERIFY_DEPARTMENT, VERIFY_LOCKED)

# Manual attendance adjustment types (HoD only)
ADJUST_TEACHING = "teaching"
ADJUST_MEETING = "academic_meeting"
ADJUST_LEAVE = "official_leave"
ADJUST_CONFERENCE = "conference"

ALL_ADJUSTMENT_TYPES = (ADJUST_TEACHING, ADJUST_MEETING, ADJUST_LEAVE, ADJUST_CONFERENCE)

# Source modules (for deduplication — never duplicate clinical data)
SOURCE_ENCOUNTERS = "encounters"
SOURCE_CLINICAL_HISTORY = "clinical_history"
SOURCE_PROCEDURE_EXECUTION = "procedure_execution"
SOURCE_REPORTS = "reports"
SOURCE_INVESTIGATIONS = "investigations"
SOURCE_RESEARCH = "research"
SOURCE_CLINICAL_REPORTS = "clinical_reports"

# Competency progress status
STATUS_NOT_STARTED = "not_started"
STATUS_IN_PROGRESS = "in_progress"
STATUS_COMPETENT = "competent"

ALL_COMPETENCY_STATUSES = (STATUS_NOT_STARTED, STATUS_IN_PROGRESS, STATUS_COMPETENT)

# Procedure competency categories mapped from report_template_key
COMPETENCY_UPPER_GI = "upper_gi_endoscopy"
COMPETENCY_COLONOSCOPY = "colonoscopy"
COMPETENCY_ERCP = "ercp"
COMPETENCY_EUS = "eus"
COMPETENCY_OTHER = "other_procedure"

TEMPLATE_TO_COMPETENCY = {
    "upper_gi": COMPETENCY_UPPER_GI,
    "upper_gi_v2": COMPETENCY_UPPER_GI,
    "colonoscopy": COMPETENCY_COLONOSCOPY,
    "colonoscopy_v2": COMPETENCY_COLONOSCOPY,
    "flex_sig_v2": COMPETENCY_COLONOSCOPY,
    "proctoscopy_v2": COMPETENCY_COLONOSCOPY,
    "ercp": COMPETENCY_ERCP,
    "eus": COMPETENCY_EUS,
}

# Trainee role codes (for competency subtype inference)
TRAINEE_ROLE_CODES = frozenset({"house_officer", "senior_registrar", "postgraduate_trainee"})

# Role codes for dashboard routing
ROLE_HEAD = "head_of_department"
ROLE_CONSULTANT = "consultant"
ROLE_CORE_CONSULTANT = "core_consultant"
ROLE_SENIOR_REGISTRAR = "senior_registrar"
ROLE_POSTGRADUATE_TRAINEE = "postgraduate_trainee"
ROLE_HOUSE_OFFICER = "house_officer"
ROLE_NURSE = "nurse"
ROLE_ENDOSCOPY_NURSE = "endoscopy_nurse"
ROLE_ENDOSCOPY_TECH = "endoscopy_technician"
ROLE_RECEPTION = "reception_staff"
