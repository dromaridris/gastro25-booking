"""Clinical Documentation Intelligence domain models."""

from __future__ import annotations

import json

from app.core.base_model import BaseModel
from app.extensions import db

from .constants import DOC_STATUS_DRAFT, SECTION_STATUS_DRAFT


class DocumentationTemplate(BaseModel):
    """Configurable document template with sections and field requirements."""

    __tablename__ = "documentation_templates"

    template_key = db.Column(db.String(60), nullable=False, unique=True, index=True)
    document_type = db.Column(db.String(40), nullable=False, index=True)
    name = db.Column(db.String(200), nullable=False)
    specialty_code = db.Column(db.String(64), nullable=True, index=True)
    sections_json = db.Column(db.Text, nullable=False)
    required_fields_json = db.Column(db.Text, nullable=True)
    optional_fields_json = db.Column(db.Text, nullable=True)
    version = db.Column(db.Integer, nullable=False, default=1)
    status = db.Column(db.String(20), nullable=False, default="active", index=True)

    @property
    def sections(self) -> list[dict]:
        return json.loads(self.sections_json or "[]")

    @sections.setter
    def sections(self, value: list[dict]) -> None:
        self.sections_json = json.dumps(value or [])

    @property
    def required_fields(self) -> list[str]:
        return json.loads(self.required_fields_json or "[]")

    @property
    def optional_fields(self) -> list[str]:
        return json.loads(self.optional_fields_json or "[]")


class ClinicalDocumentDraft(BaseModel):
    """Physician-reviewable clinical document draft."""

    __tablename__ = "clinical_document_drafts"

    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False, index=True)
    encounter_id = db.Column(db.Integer, db.ForeignKey("clinical_encounters.id"), nullable=False, index=True)
    template_id = db.Column(db.Integer, db.ForeignKey("documentation_templates.id"), nullable=False, index=True)
    template_key = db.Column(db.String(60), nullable=False, index=True)
    document_type = db.Column(db.String(40), nullable=False, index=True)

    ai_session_uuid = db.Column(db.String(36), nullable=True, index=True)
    provider_key = db.Column(db.String(32), nullable=True)
    model_name = db.Column(db.String(128), nullable=True)
    status = db.Column(db.String(20), nullable=False, default=DOC_STATUS_DRAFT, index=True)
    source_modules_json = db.Column(db.Text, nullable=True)
    knowledge_references_json = db.Column(db.Text, nullable=True)
    clinical_context_json = db.Column(db.Text, nullable=True)
    version = db.Column(db.Integer, nullable=False, default=1)

    template = db.relationship("DocumentationTemplate")
    sections = db.relationship("DocumentSection", back_populates="document", lazy="dynamic")
    version_records = db.relationship("DocumentVersionRecord", back_populates="document", lazy="dynamic")

    @property
    def source_modules(self) -> list[str]:
        return json.loads(self.source_modules_json or "[]")

    @source_modules.setter
    def source_modules(self, value: list[str]) -> None:
        self.source_modules_json = json.dumps(value or [])

    @property
    def knowledge_references(self) -> list[dict]:
        return json.loads(self.knowledge_references_json or "[]")

    @knowledge_references.setter
    def knowledge_references(self, value: list[dict]) -> None:
        self.knowledge_references_json = json.dumps(value or [])

    @property
    def clinical_context(self) -> dict:
        return json.loads(self.clinical_context_json or "{}")

    @clinical_context.setter
    def clinical_context(self, value: dict) -> None:
        self.clinical_context_json = json.dumps(value or {})


class DocumentSection(BaseModel):
    """Generated document section — separate from physician final content."""

    __tablename__ = "document_sections"

    document_id = db.Column(db.Integer, db.ForeignKey("clinical_document_drafts.id"), nullable=False, index=True)
    section_key = db.Column(db.String(60), nullable=False, index=True)
    section_name = db.Column(db.String(200), nullable=False)
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    generated_content = db.Column(db.Text, nullable=True)
    physician_content = db.Column(db.Text, nullable=True)
    source_data_references_json = db.Column(db.Text, nullable=True)
    missing_information_json = db.Column(db.Text, nullable=True)
    conflicting_information_json = db.Column(db.Text, nullable=True)
    is_required = db.Column(db.Boolean, nullable=False, default=True)
    is_complete = db.Column(db.Boolean, nullable=False, default=False)
    approval_status = db.Column(db.String(20), nullable=False, default=SECTION_STATUS_DRAFT, index=True)
    version = db.Column(db.Integer, nullable=False, default=1)

    document = db.relationship("ClinicalDocumentDraft", back_populates="sections")

    @property
    def source_data_references(self) -> list[dict]:
        return json.loads(self.source_data_references_json or "[]")

    @source_data_references.setter
    def source_data_references(self, value: list[dict]) -> None:
        self.source_data_references_json = json.dumps(value or [])

    @property
    def missing_information(self) -> list[str]:
        return json.loads(self.missing_information_json or "[]")

    @missing_information.setter
    def missing_information(self, value: list[str]) -> None:
        self.missing_information_json = json.dumps(value or [])

    @property
    def conflicting_information(self) -> list[str]:
        return json.loads(self.conflicting_information_json or "[]")

    @conflicting_information.setter
    def conflicting_information(self, value: list[str]) -> None:
        self.conflicting_information_json = json.dumps(value or [])

    @property
    def display_content(self) -> str:
        return self.physician_content or self.generated_content or ""


class DocumentVersionRecord(BaseModel):
    """Version history for document revisions."""

    __tablename__ = "document_version_records"

    document_id = db.Column(db.Integer, db.ForeignKey("clinical_document_drafts.id"), nullable=False, index=True)
    version_number = db.Column(db.Integer, nullable=False)
    changed_sections_json = db.Column(db.Text, nullable=True)
    editor_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    change_reason = db.Column(db.Text, nullable=True)
    snapshot_json = db.Column(db.Text, nullable=True)

    document = db.relationship("ClinicalDocumentDraft", back_populates="version_records")

    @property
    def changed_sections(self) -> list[str]:
        return json.loads(self.changed_sections_json or "[]")

    @changed_sections.setter
    def changed_sections(self, value: list[str]) -> None:
        self.changed_sections_json = json.dumps(value or [])

    @property
    def snapshot(self) -> dict:
        return json.loads(self.snapshot_json or "{}")

    @snapshot.setter
    def snapshot(self, value: dict) -> None:
        self.snapshot_json = json.dumps(value or {})


class SignedClinicalDocument(BaseModel):
    """Final signed document — immutable, separate from AI draft."""

    __tablename__ = "signed_clinical_documents"

    draft_id = db.Column(db.Integer, db.ForeignKey("clinical_document_drafts.id"), nullable=False, index=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False, index=True)
    encounter_id = db.Column(db.Integer, db.ForeignKey("clinical_encounters.id"), nullable=False, index=True)
    template_key = db.Column(db.String(60), nullable=False)
    document_type = db.Column(db.String(40), nullable=False, index=True)
    signed_content_json = db.Column(db.Text, nullable=False)
    signed_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    signed_at = db.Column(db.DateTime(timezone=True), nullable=True)
    version = db.Column(db.Integer, nullable=False, default=1)

    draft = db.relationship("ClinicalDocumentDraft")

    @property
    def signed_content(self) -> dict:
        return json.loads(self.signed_content_json or "{}")

    @signed_content.setter
    def signed_content(self, value: dict) -> None:
        self.signed_content_json = json.dumps(value or {})


class PhysicianDocumentAction(BaseModel):
    """Physician actions on documents — edits, approvals, rejections."""

    __tablename__ = "physician_document_actions"

    document_id = db.Column(db.Integer, db.ForeignKey("clinical_document_drafts.id"), nullable=False, index=True)
    section_id = db.Column(db.Integer, db.ForeignKey("document_sections.id"), nullable=True, index=True)
    encounter_id = db.Column(db.Integer, db.ForeignKey("clinical_encounters.id"), nullable=False, index=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False, index=True)

    action_type = db.Column(db.String(20), nullable=False, index=True)
    action_notes = db.Column(db.Text, nullable=True)
    modified_fields_json = db.Column(db.Text, nullable=True)
    version = db.Column(db.Integer, nullable=False, default=1)

    @property
    def modified_fields(self) -> dict:
        return json.loads(self.modified_fields_json or "{}")

    @modified_fields.setter
    def modified_fields(self, value: dict) -> None:
        self.modified_fields_json = json.dumps(value or {})
