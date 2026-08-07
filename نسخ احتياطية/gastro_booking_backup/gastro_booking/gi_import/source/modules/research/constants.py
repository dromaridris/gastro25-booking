"""Research platform constants — Sprint 6B variable framework."""

# Variable data types
TYPE_BOOLEAN = "boolean"
TYPE_INTEGER = "integer"
TYPE_DECIMAL = "decimal"
TYPE_TEXT = "text"
TYPE_DATE = "date"
TYPE_DATETIME = "datetime"
TYPE_SINGLE_CHOICE = "single_choice"
TYPE_MULTIPLE_CHOICE = "multiple_choice"
TYPE_CALCULATED = "calculated"

ALL_DATA_TYPES = (
    TYPE_BOOLEAN,
    TYPE_INTEGER,
    TYPE_DECIMAL,
    TYPE_TEXT,
    TYPE_DATE,
    TYPE_DATETIME,
    TYPE_SINGLE_CHOICE,
    TYPE_MULTIPLE_CHOICE,
    TYPE_CALCULATED,
)

# How a variable obtains its value
ORIGIN_CLINICAL_REFERENCE = "clinical_reference"
ORIGIN_MANUAL_ENTRY = "manual_entry"
ORIGIN_CALCULATED = "calculated"

ALL_VALUE_ORIGINS = (ORIGIN_CLINICAL_REFERENCE, ORIGIN_MANUAL_ENTRY, ORIGIN_CALCULATED)

# Clinical modules attachable without modifying owner modules
MODULE_CLINICAL_HISTORY = "clinical_history"
MODULE_PROCEDURES = "procedures"
MODULE_REPORTS = "reports"
MODULE_LABORATORY = "laboratory"
MODULE_IMAGING = "imaging"
MODULE_MEDICATIONS = "medications"
MODULE_FOLLOW_UP = "follow_up"
MODULE_PATIENTS = "patients"

ALL_SOURCE_MODULES = (
    MODULE_CLINICAL_HISTORY,
    MODULE_PROCEDURES,
    MODULE_REPORTS,
    MODULE_LABORATORY,
    MODULE_IMAGING,
    MODULE_MEDICATIONS,
    MODULE_FOLLOW_UP,
    MODULE_PATIENTS,
)

# Manual value entry status
VALUE_STATUS_DRAFT = "draft"
VALUE_STATUS_SUBMITTED = "submitted"
VALUE_STATUS_LOCKED = "locked"

ALL_VALUE_STATUSES = (VALUE_STATUS_DRAFT, VALUE_STATUS_SUBMITTED, VALUE_STATUS_LOCKED)

# Map legacy source_type to source_module
SOURCE_TYPE_TO_MODULE = {
    "patient_field": MODULE_PATIENTS,
    "history_answer": MODULE_CLINICAL_HISTORY,
    "history_confirmed_diagnosis": MODULE_CLINICAL_HISTORY,
    "lab_result": MODULE_LABORATORY,
    "imaging_study": MODULE_IMAGING,
    "medication_entry": MODULE_MEDICATIONS,
    "report_field": MODULE_REPORTS,
    "procedure_field": MODULE_PROCEDURES,
    "follow_up_field": MODULE_FOLLOW_UP,
}

# Map legacy value_type seed to data_type
LEGACY_VALUE_TYPE_MAP = {
    "text": TYPE_TEXT,
    "number": TYPE_DECIMAL,
    "boolean": TYPE_BOOLEAN,
    "date": TYPE_DATE,
    "datetime": TYPE_DATETIME,
}
