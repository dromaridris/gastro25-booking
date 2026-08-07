"""Research Platform — Sprint 5A-RES + Sprint 6B variable framework models."""

import json

from app.core.base_model import BaseModel, utcnow
from app.extensions import db

SOURCE_PATIENT_FIELD = "patient_field"
SOURCE_HISTORY_ANSWER = "history_answer"
SOURCE_HISTORY_DIAGNOSIS = "history_confirmed_diagnosis"
SOURCE_LAB_RESULT = "lab_result"
SOURCE_IMAGING_STUDY = "imaging_study"
SOURCE_MEDICATION_ENTRY = "medication_entry"
SOURCE_REPORT_FIELD = "report_field"
SOURCE_PROCEDURE_FIELD = "procedure_field"
SOURCE_FOLLOW_UP_FIELD = "follow_up_field"

ALL_SOURCE_TYPES = (
    SOURCE_PATIENT_FIELD,
    SOURCE_HISTORY_ANSWER,
    SOURCE_HISTORY_DIAGNOSIS,
    SOURCE_LAB_RESULT,
    SOURCE_IMAGING_STUDY,
    SOURCE_MEDICATION_ENTRY,
    SOURCE_REPORT_FIELD,
    SOURCE_PROCEDURE_FIELD,
    SOURCE_FOLLOW_UP_FIELD,
)

ENROLLMENT_STATUS_ACTIVE = "active"
ENROLLMENT_STATUS_WITHDRAWN = "withdrawn"

ALL_ENROLLMENT_STATUSES = (ENROLLMENT_STATUS_ACTIVE, ENROLLMENT_STATUS_WITHDRAWN)


class DiseaseRegistryDefinition(BaseModel):
    __tablename__ = "disease_registry_definitions"

    code = db.Column(db.String(50), nullable=False, unique=True, index=True)
    name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)
    knowledge_topic_key = db.Column(db.String(80), nullable=True)
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    is_active = db.Column(db.Boolean, nullable=False, default=True)


class ResearchVariableGroup(BaseModel):
    """Logical grouping of variables within a registry/study."""

    __tablename__ = "research_variable_groups"

    code = db.Column(db.String(50), nullable=False, index=True)
    registry_code = db.Column(db.String(50), nullable=False, index=True)
    name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    __table_args__ = (
        db.UniqueConstraint("registry_code", "code", name="uq_research_variable_group_registry_code"),
    )


class ResearchVariableDefinition(BaseModel):
    __tablename__ = "research_variable_definitions"

    code = db.Column(db.String(80), nullable=False, unique=True, index=True)
    stable_id = db.Column(db.String(80), nullable=False, unique=True, index=True)
    registry_code = db.Column(db.String(50), nullable=False, index=True)
    group_code = db.Column(db.String(50), nullable=True, index=True)
    name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)
    category = db.Column(db.String(50), nullable=True, index=True)
    source_module = db.Column(db.String(40), nullable=True, index=True)
    source_type = db.Column(db.String(40), nullable=False)
    source_key = db.Column(db.String(120), nullable=False)
    data_type = db.Column(db.String(20), nullable=False, default="text")
    value_type = db.Column(db.String(20), nullable=False, default="text")
    value_origin = db.Column(db.String(30), nullable=False, default="clinical_reference")
    is_required = db.Column(db.Boolean, nullable=False, default=False)
    validation_rules_json = db.Column(db.Text, nullable=True)
    allowed_values_json = db.Column(db.Text, nullable=True)
    attachment_config_json = db.Column(db.Text, nullable=True)
    version = db.Column(db.Integer, nullable=False, default=1)
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    updated_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    updated_by = db.relationship("User", foreign_keys=[updated_by_id])

    def validation_rules(self) -> dict:
        if not self.validation_rules_json:
            return {}
        try:
            parsed = json.loads(self.validation_rules_json)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}

    def allowed_values(self) -> list:
        if not self.allowed_values_json:
            return []
        try:
            parsed = json.loads(self.allowed_values_json)
            return parsed if isinstance(parsed, list) else []
        except json.JSONDecodeError:
            return []

    def attachment_config(self) -> dict:
        if not self.attachment_config_json:
            return {}
        try:
            parsed = json.loads(self.attachment_config_json)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}


class ResearchVariableVersion(BaseModel):
    """Immutable snapshot when a variable definition is published/updated."""

    __tablename__ = "research_variable_versions"

    variable_code = db.Column(db.String(80), nullable=False, index=True)
    version = db.Column(db.Integer, nullable=False)
    snapshot_json = db.Column(db.Text, nullable=False)
    published_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    published_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    published_by = db.relationship("User", foreign_keys=[published_by_id])

    __table_args__ = (
        db.UniqueConstraint("variable_code", "version", name="uq_research_variable_version"),
    )


class ResearchVariableValue(BaseModel):
    """
    Manually entered research values — never writes to clinical modules.
    """

    __tablename__ = "research_variable_values"

    variable_code = db.Column(db.String(80), nullable=False, index=True)
    registry_code = db.Column(db.String(50), nullable=False, index=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False, index=True)
    enrollment_id = db.Column(db.Integer, db.ForeignKey("registry_enrollments.id"), nullable=True, index=True)
    variable_version = db.Column(db.Integer, nullable=False, default=1)
    value_text = db.Column(db.Text, nullable=True)
    value_numeric = db.Column(db.Numeric(14, 4), nullable=True)
    value_json = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), nullable=False, default="draft", index=True)
    entered_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    entered_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    patient = db.relationship("Patient", foreign_keys=[patient_id])
    enrollment = db.relationship("RegistryEnrollment", foreign_keys=[enrollment_id])
    entered_by = db.relationship("User", foreign_keys=[entered_by_id])

    __table_args__ = (
        db.UniqueConstraint(
            "variable_code",
            "patient_id",
            "enrollment_id",
            name="uq_research_variable_value_patient_enrollment",
        ),
    )


class RegistryEnrollment(BaseModel):
    __tablename__ = "registry_enrollments"

    registry_code = db.Column(db.String(50), nullable=False, index=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False, index=True)
    index_encounter_id = db.Column(db.Integer, db.ForeignKey("clinical_encounters.id"), nullable=True)
    enrolled_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    enrolled_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    status = db.Column(db.String(20), nullable=False, default=ENROLLMENT_STATUS_ACTIVE, index=True)
    notes = db.Column(db.Text, nullable=True)

    patient = db.relationship("Patient", foreign_keys=[patient_id])
    index_encounter = db.relationship("ClinicalEncounter", foreign_keys=[index_encounter_id])
    enrolled_by = db.relationship("User", foreign_keys=[enrolled_by_id])

    __table_args__ = (
        db.UniqueConstraint("registry_code", "patient_id", name="uq_registry_enrollment_patient"),
    )
