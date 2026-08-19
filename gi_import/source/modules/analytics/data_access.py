"""Read-only analytics data access layer.

Aggregates references from clinical modules without duplicating source data.
All queries are SELECT-only — never modify clinical records.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from sqlalchemy import func

from app.extensions import db
from app.modules.clinical_assessment.models import ClinicalAssessmentRun, DiagnosisSuggestion
from app.modules.clinical_intake.models import ClinicalIntakeRecord
from app.modules.documentation_ai.models import ClinicalDocumentDraft, SignedClinicalDocument
from app.modules.encounters.models import ClinicalEncounter
from app.modules.patient_journey.constants import FOLLOWUP_STATUS_COMPLETED
from app.modules.patient_journey.models import FollowUpPlan
from app.modules.patients.models import Patient
from app.modules.procedure_execution.models import ProcedureSession
from app.modules.procedures.models import Procedure
from app.modules.reports.models import Report


@dataclass
class AnalyticsFilters:
    department_id: int | None = None
    physician_id: int | None = None
    role_code: str | None = None
    procedure_type_id: int | None = None
    diagnosis_category: str | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "department_id": self.department_id,
            "physician_id": self.physician_id,
            "role_code": self.role_code,
            "procedure_type_id": self.procedure_type_id,
            "diagnosis_category": self.diagnosis_category,
            "date_from": self.date_from.isoformat() if self.date_from else None,
            "date_to": self.date_to.isoformat() if self.date_to else None,
        }


@dataclass
class DataAccessSummary:
    """Lightweight counts from each source for traceability."""

    patients: int = 0
    encounters: int = 0
    procedures: int = 0
    follow_up_plans: int = 0
    document_drafts: int = 0
    signed_documents: int = 0
    sources_queried: list[str] = field(default_factory=list)


class AnalyticsDataAccess:
    """Unified read-only access to clinical data sources."""

    READ_ONLY_SOURCES = (
        "patients",
        "encounters",
        "clinical_intake",
        "clinical_history_ai",
        "clinical_assessment",
        "investigation_planning",
        "clinical_interpretation",
        "management_plan_ai",
        "patient_journey",
        "documentation_ai",
        "investigations",
        "procedure_execution",
        "reports",
        "workforce_identity",
    )

    def _apply_encounter_filters(self, query, filters: AnalyticsFilters):
        query = query.filter(ClinicalEncounter.is_archived.is_(False))
        if filters.department_id is not None:
            query = query.filter(ClinicalEncounter.department_id == filters.department_id)
        if filters.physician_id is not None:
            query = query.filter(ClinicalEncounter.created_by_id == filters.physician_id)
        if filters.date_from is not None:
            query = query.filter(ClinicalEncounter.created_at >= filters.date_from)
        if filters.date_to is not None:
            query = query.filter(ClinicalEncounter.created_at <= filters.date_to)
        if filters.diagnosis_category is not None:
            query = query.join(
                ClinicalAssessmentRun,
                ClinicalAssessmentRun.encounter_id == ClinicalEncounter.id,
            ).join(
                DiagnosisSuggestion,
                DiagnosisSuggestion.assessment_run_id == ClinicalAssessmentRun.id,
            ).filter(DiagnosisSuggestion.category == filters.diagnosis_category)
        return query

    def count_encounters(self, filters: AnalyticsFilters) -> int:
        query = db.session.query(func.count(ClinicalEncounter.id))
        query = self._apply_encounter_filters(query, filters)
        return int(query.scalar() or 0)

    def count_distinct_patients_with_encounters(self, filters: AnalyticsFilters) -> int:
        query = db.session.query(func.count(func.distinct(ClinicalEncounter.patient_id)))
        query = self._apply_encounter_filters(query, filters)
        return int(query.scalar() or 0)

    def count_patients(self, filters: AnalyticsFilters) -> int:
        query = db.session.query(func.count(Patient.id)).filter(Patient.is_archived.is_(False))
        if filters.department_id is not None:
            query = query.filter(Patient.department_id == filters.department_id)
        if filters.date_from is not None:
            query = query.filter(Patient.created_at >= filters.date_from)
        if filters.date_to is not None:
            query = query.filter(Patient.created_at <= filters.date_to)
        return int(query.scalar() or 0)

    def count_procedure_sessions(self, filters: AnalyticsFilters) -> int:
        query = db.session.query(func.count(ProcedureSession.id)).filter(
            ProcedureSession.is_archived.is_(False)
        )
        if filters.department_id is not None:
            query = query.filter(ProcedureSession.department_id == filters.department_id)
        if filters.physician_id is not None:
            query = query.filter(ProcedureSession.endoscopist_id == filters.physician_id)
        if filters.date_from is not None:
            query = query.filter(ProcedureSession.created_at >= filters.date_from)
        if filters.date_to is not None:
            query = query.filter(ProcedureSession.created_at <= filters.date_to)
        if filters.procedure_type_id is not None:
            query = query.join(Procedure, Procedure.id == ProcedureSession.procedure_id).filter(
                Procedure.procedure_type_id == filters.procedure_type_id
            )
        return int(query.scalar() or 0)

    def count_follow_up_plans(self, filters: AnalyticsFilters, *, completed_only: bool = False) -> int:
        query = db.session.query(func.count(FollowUpPlan.id)).filter(FollowUpPlan.is_archived.is_(False))
        if filters.department_id is not None:
            query = query.filter(FollowUpPlan.department_id == filters.department_id)
        if filters.physician_id is not None:
            query = query.filter(FollowUpPlan.responsible_physician_id == filters.physician_id)
        if filters.date_from is not None:
            query = query.filter(FollowUpPlan.created_at >= filters.date_from)
        if filters.date_to is not None:
            query = query.filter(FollowUpPlan.created_at <= filters.date_to)
        if completed_only:
            query = query.filter(FollowUpPlan.status == FOLLOWUP_STATUS_COMPLETED)
        return int(query.scalar() or 0)

    def count_document_drafts(self, filters: AnalyticsFilters) -> int:
        query = db.session.query(func.count(ClinicalDocumentDraft.id)).filter(
            ClinicalDocumentDraft.is_archived.is_(False)
        )
        if filters.department_id is not None:
            query = query.filter(ClinicalDocumentDraft.department_id == filters.department_id)
        if filters.physician_id is not None:
            query = query.filter(ClinicalDocumentDraft.created_by_id == filters.physician_id)
        if filters.date_from is not None:
            query = query.filter(ClinicalDocumentDraft.created_at >= filters.date_from)
        if filters.date_to is not None:
            query = query.filter(ClinicalDocumentDraft.created_at <= filters.date_to)
        return int(query.scalar() or 0)

    def count_signed_documents(self, filters: AnalyticsFilters) -> int:
        query = db.session.query(func.count(SignedClinicalDocument.id)).filter(
            SignedClinicalDocument.is_archived.is_(False)
        )
        if filters.department_id is not None:
            query = query.filter(SignedClinicalDocument.department_id == filters.department_id)
        if filters.physician_id is not None:
            query = query.filter(SignedClinicalDocument.signed_by_id == filters.physician_id)
        if filters.date_from is not None:
            query = query.filter(SignedClinicalDocument.signed_at >= filters.date_from)
        if filters.date_to is not None:
            query = query.filter(SignedClinicalDocument.signed_at <= filters.date_to)
        return int(query.scalar() or 0)

    def source_availability(self) -> dict[str, bool]:
        """Verify read-only source tables are reachable."""
        checks = {
            "patients": db.session.query(func.count(Patient.id)).scalar() is not None,
            "encounters": db.session.query(func.count(ClinicalEncounter.id)).scalar() is not None,
            "clinical_intake": db.session.query(func.count(ClinicalIntakeRecord.id)).scalar() is not None,
            "clinical_assessment": db.session.query(func.count(ClinicalAssessmentRun.id)).scalar() is not None,
            "patient_journey": db.session.query(func.count(FollowUpPlan.id)).scalar() is not None,
            "documentation_ai": db.session.query(func.count(ClinicalDocumentDraft.id)).scalar() is not None,
            "procedure_execution": db.session.query(func.count(ProcedureSession.id)).scalar() is not None,
            "reports": db.session.query(func.count(Report.id)).scalar() is not None,
        }
        return checks

    def build_summary(self, filters: AnalyticsFilters) -> DataAccessSummary:
        return DataAccessSummary(
            patients=self.count_distinct_patients_with_encounters(filters),
            encounters=self.count_encounters(filters),
            procedures=self.count_procedure_sessions(filters),
            follow_up_plans=self.count_follow_up_plans(filters),
            document_drafts=self.count_document_drafts(filters),
            signed_documents=self.count_signed_documents(filters),
            sources_queried=list(self.READ_ONLY_SOURCES),
        )
