"""Clinical Interpretation domain models."""

from __future__ import annotations

import json

from app.core.base_model import BaseModel
from app.extensions import db

from .constants import FINDING_STATUS_SUGGESTED, RUN_STATUS_GENERATED


class ClinicalInterpretationRun(BaseModel):
    """One clinical data interpretation generation run."""

    __tablename__ = "clinical_interpretation_runs"

    encounter_id = db.Column(db.Integer, db.ForeignKey("clinical_encounters.id"), nullable=False, index=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False, index=True)
    assessment_run_id = db.Column(
        db.Integer, db.ForeignKey("clinical_assessment_runs.id"), nullable=True, index=True
    )
    ai_session_uuid = db.Column(db.String(36), nullable=True, index=True)
    provider_key = db.Column(db.String(32), nullable=True)
    model_name = db.Column(db.String(128), nullable=True)
    status = db.Column(db.String(20), nullable=False, default=RUN_STATUS_GENERATED, index=True)
    clinical_data_sources_json = db.Column(db.Text, nullable=True)
    previous_differential_snapshot_json = db.Column(db.Text, nullable=True)
    knowledge_sources_json = db.Column(db.Text, nullable=True)
    clinical_context_json = db.Column(db.Text, nullable=True)
    version = db.Column(db.Integer, nullable=False, default=1)

    findings = db.relationship("InterpretationFinding", back_populates="run", lazy="dynamic")
    differential_updates = db.relationship("DifferentialUpdateRecord", back_populates="run", lazy="dynamic")

    @property
    def clinical_data_sources(self) -> list[dict]:
        return json.loads(self.clinical_data_sources_json or "[]")

    @clinical_data_sources.setter
    def clinical_data_sources(self, value: list[dict]) -> None:
        self.clinical_data_sources_json = json.dumps(value or [])

    @property
    def previous_differential_snapshot(self) -> list[dict]:
        return json.loads(self.previous_differential_snapshot_json or "[]")

    @previous_differential_snapshot.setter
    def previous_differential_snapshot(self, value: list[dict]) -> None:
        self.previous_differential_snapshot_json = json.dumps(value or [])

    @property
    def knowledge_sources(self) -> list[dict]:
        return json.loads(self.knowledge_sources_json or "[]")

    @knowledge_sources.setter
    def knowledge_sources(self, value: list[dict]) -> None:
        self.knowledge_sources_json = json.dumps(value or [])

    @property
    def clinical_context(self) -> dict:
        return json.loads(self.clinical_context_json or "{}")

    @clinical_context.setter
    def clinical_context(self, value: dict) -> None:
        self.clinical_context_json = json.dumps(value or {})


class InterpretationFinding(BaseModel):
    """AI-generated interpretation finding — immutable physician-review snapshot."""

    __tablename__ = "interpretation_findings"

    run_id = db.Column(
        db.Integer, db.ForeignKey("clinical_interpretation_runs.id"), nullable=False, index=True
    )
    encounter_id = db.Column(db.Integer, db.ForeignKey("clinical_encounters.id"), nullable=False, index=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False, index=True)

    finding_title = db.Column(db.String(200), nullable=False)
    source_type = db.Column(db.String(40), nullable=False, index=True)
    source_data_json = db.Column(db.Text, nullable=True)
    explanation = db.Column(db.Text, nullable=True)
    significance = db.Column(db.Text, nullable=True)
    differential_impact = db.Column(db.Text, nullable=True)
    related_diagnosis = db.Column(db.String(200), nullable=True)
    supporting_diagnoses_json = db.Column(db.Text, nullable=True)
    contradicting_diagnoses_json = db.Column(db.Text, nullable=True)
    missing_information_json = db.Column(db.Text, nullable=True)
    knowledge_references_json = db.Column(db.Text, nullable=True)
    confidence_indicator = db.Column(db.String(20), nullable=False, default="medium")
    ai_session_uuid = db.Column(db.String(36), nullable=True, index=True)
    status = db.Column(db.String(20), nullable=False, default=FINDING_STATUS_SUGGESTED, index=True)
    version = db.Column(db.Integer, nullable=False, default=1)

    run = db.relationship("ClinicalInterpretationRun", back_populates="findings")
    physician_decisions = db.relationship(
        "PhysicianInterpretationDecision", back_populates="finding", lazy="dynamic"
    )

    @property
    def source_data(self) -> dict:
        return json.loads(self.source_data_json or "{}")

    @source_data.setter
    def source_data(self, value: dict) -> None:
        self.source_data_json = json.dumps(value or {})

    @property
    def supporting_diagnoses(self) -> list[str]:
        return json.loads(self.supporting_diagnoses_json or "[]")

    @supporting_diagnoses.setter
    def supporting_diagnoses(self, value: list[str]) -> None:
        self.supporting_diagnoses_json = json.dumps(value or [])

    @property
    def contradicting_diagnoses(self) -> list[str]:
        return json.loads(self.contradicting_diagnoses_json or "[]")

    @contradicting_diagnoses.setter
    def contradicting_diagnoses(self, value: list[str]) -> None:
        self.contradicting_diagnoses_json = json.dumps(value or [])

    @property
    def missing_information(self) -> list[str]:
        return json.loads(self.missing_information_json or "[]")

    @missing_information.setter
    def missing_information(self, value: list[str]) -> None:
        self.missing_information_json = json.dumps(value or [])

    @property
    def knowledge_references(self) -> list[dict]:
        return json.loads(self.knowledge_references_json or "[]")

    @knowledge_references.setter
    def knowledge_references(self, value: list[dict]) -> None:
        self.knowledge_references_json = json.dumps(value or [])


class DifferentialUpdateRecord(BaseModel):
    """Suggested differential update — preserves original assessment history."""

    __tablename__ = "differential_update_records"

    run_id = db.Column(
        db.Integer, db.ForeignKey("clinical_interpretation_runs.id"), nullable=False, index=True
    )
    encounter_id = db.Column(db.Integer, db.ForeignKey("clinical_encounters.id"), nullable=False, index=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False, index=True)

    diagnosis_name = db.Column(db.String(200), nullable=False, index=True)
    previous_confidence = db.Column(db.String(20), nullable=True)
    previous_category = db.Column(db.String(40), nullable=True)
    update_direction = db.Column(db.String(30), nullable=False, index=True)
    reasoning = db.Column(db.Text, nullable=True)
    related_finding_title = db.Column(db.String(200), nullable=True)
    version = db.Column(db.Integer, nullable=False, default=1)

    run = db.relationship("ClinicalInterpretationRun", back_populates="differential_updates")


class PhysicianInterpretationDecision(BaseModel):
    """Physician decision stored separately from AI interpretation findings."""

    __tablename__ = "physician_interpretation_decisions"

    run_id = db.Column(
        db.Integer, db.ForeignKey("clinical_interpretation_runs.id"), nullable=True, index=True
    )
    finding_id = db.Column(db.Integer, db.ForeignKey("interpretation_findings.id"), nullable=True, index=True)
    encounter_id = db.Column(db.Integer, db.ForeignKey("clinical_encounters.id"), nullable=False, index=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False, index=True)

    finding_title = db.Column(db.String(200), nullable=False)
    original_finding_title = db.Column(db.String(200), nullable=True)
    physician_status = db.Column(db.String(20), nullable=False, index=True)
    physician_notes = db.Column(db.Text, nullable=True)
    modified_fields_json = db.Column(db.Text, nullable=True)
    version = db.Column(db.Integer, nullable=False, default=1)

    finding = db.relationship("InterpretationFinding", back_populates="physician_decisions")

    @property
    def modified_fields(self) -> dict:
        return json.loads(self.modified_fields_json or "{}")

    @modified_fields.setter
    def modified_fields(self, value: dict) -> None:
        self.modified_fields_json = json.dumps(value or {})
