"""Read-only quality analytics data access."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from app.extensions import db
from app.modules.analytics.data_access import AnalyticsFilters
from app.modules.clinical_governance.models import ClinicalIncident
from app.modules.clinical_reports.models import ClinicalReportMetric
from app.modules.dept_ops.models import WaitingListEntry
from app.modules.documentation_ai.models import ClinicalDocumentDraft, DocumentSection, SignedClinicalDocument
from app.modules.encounters.models import ENCOUNTER_STATUS_OPEN, ClinicalEncounter
from app.modules.patient_journey.constants import (
    FOLLOWUP_STATUS_COMPLETED,
    FOLLOWUP_STATUS_MISSED,
    NEXT_ACTION_ESCALATE,
    OUTCOME_LOST_TO_FOLLOWUP,
)
from app.modules.patient_journey.models import ClinicalOutcomeRecord, FollowUpEvent, FollowUpPlan
from app.modules.procedure_execution.models import OUTCOME_COMPLETED, ProcedureSession
from app.modules.reports.models import Report, STATUS_DRAFT, STATUS_FINALIZED, STATUS_LOCKED


@dataclass
class QualityDataAccess:
    """Unified read-only access for quality and KPI metrics."""

    def _encounter_query(self, filters: AnalyticsFilters):
        query = ClinicalEncounter.query.filter_by(is_archived=False)
        if filters.department_id is not None:
            query = query.filter_by(department_id=filters.department_id)
        if filters.physician_id is not None:
            query = query.filter_by(created_by_id=filters.physician_id)
        if filters.date_from is not None:
            query = query.filter(ClinicalEncounter.created_at >= filters.date_from)
        if filters.date_to is not None:
            query = query.filter(ClinicalEncounter.created_at <= filters.date_to)
        return query

    def count_encounters(self, filters: AnalyticsFilters) -> int:
        return self._encounter_query(filters).count()

    def count_open_encounters(self, filters: AnalyticsFilters) -> int:
        return self._encounter_query(filters).filter_by(status=ENCOUNTER_STATUS_OPEN).count()

    def count_follow_up_plans(self, filters: AnalyticsFilters) -> int:
        query = FollowUpPlan.query.filter_by(is_archived=False)
        if filters.department_id is not None:
            query = query.filter_by(department_id=filters.department_id)
        if filters.physician_id is not None:
            query = query.filter_by(responsible_physician_id=filters.physician_id)
        if filters.date_from is not None:
            query = query.filter(FollowUpPlan.created_at >= filters.date_from)
        if filters.date_to is not None:
            query = query.filter(FollowUpPlan.created_at <= filters.date_to)
        return query.count()

    def count_completed_follow_ups(self, filters: AnalyticsFilters) -> int:
        query = FollowUpPlan.query.filter_by(is_archived=False, status=FOLLOWUP_STATUS_COMPLETED)
        if filters.department_id is not None:
            query = query.filter_by(department_id=filters.department_id)
        if filters.date_from is not None:
            query = query.filter(FollowUpPlan.created_at >= filters.date_from)
        if filters.date_to is not None:
            query = query.filter(FollowUpPlan.created_at <= filters.date_to)
        return query.count()

    def count_lost_to_follow_up(self, filters: AnalyticsFilters) -> int:
        outcomes = ClinicalOutcomeRecord.query.filter_by(
            is_archived=False, outcome=OUTCOME_LOST_TO_FOLLOWUP
        )
        if filters.department_id is not None:
            outcomes = outcomes.filter_by(department_id=filters.department_id)
        if filters.date_from is not None:
            outcomes = outcomes.filter(ClinicalOutcomeRecord.created_at >= filters.date_from)
        if filters.date_to is not None:
            outcomes = outcomes.filter(ClinicalOutcomeRecord.created_at <= filters.date_to)
        missed = FollowUpPlan.query.filter_by(is_archived=False, status=FOLLOWUP_STATUS_MISSED)
        if filters.department_id is not None:
            missed = missed.filter_by(department_id=filters.department_id)
        return outcomes.count() + missed.count()

    def documentation_completeness_stats(self, filters: AnalyticsFilters) -> tuple[int, int, int]:
        query = DocumentSection.query.join(
            ClinicalDocumentDraft, ClinicalDocumentDraft.id == DocumentSection.document_id
        ).filter(ClinicalDocumentDraft.is_archived.is_(False), DocumentSection.is_archived.is_(False))
        if filters.department_id is not None:
            query = query.filter(ClinicalDocumentDraft.department_id == filters.department_id)
        if filters.date_from is not None:
            query = query.filter(ClinicalDocumentDraft.created_at >= filters.date_from)
        if filters.date_to is not None:
            query = query.filter(ClinicalDocumentDraft.created_at <= filters.date_to)
        total_required = query.filter(DocumentSection.is_required.is_(True)).count()
        complete_required = query.filter(
            DocumentSection.is_required.is_(True), DocumentSection.is_complete.is_(True)
        ).count()
        drafts = ClinicalDocumentDraft.query.filter_by(is_archived=False)
        if filters.department_id is not None:
            drafts = drafts.filter_by(department_id=filters.department_id)
        return complete_required, total_required, drafts.count()

    def procedure_completion_stats(self, filters: AnalyticsFilters) -> tuple[int, int]:
        query = ProcedureSession.query.filter_by(is_archived=False)
        if filters.department_id is not None:
            query = query.filter_by(department_id=filters.department_id)
        if filters.physician_id is not None:
            query = query.filter_by(endoscopist_id=filters.physician_id)
        if filters.date_from is not None:
            query = query.filter(ProcedureSession.created_at >= filters.date_from)
        if filters.date_to is not None:
            query = query.filter(ProcedureSession.created_at <= filters.date_to)
        total = query.count()
        completed = query.filter_by(outcome=OUTCOME_COMPLETED).count()
        return completed, total

    def complication_reporting_stats(self, filters: AnalyticsFilters) -> tuple[int, int]:
        metrics = ClinicalReportMetric.query.filter(
            ClinicalReportMetric.metric_key == "immediate_complication",
            ClinicalReportMetric.is_archived.is_(False),
        )
        if filters.department_id is not None:
            metrics = metrics.filter_by(department_id=filters.department_id)
        if filters.date_from is not None:
            metrics = metrics.filter(ClinicalReportMetric.created_at >= filters.date_from)
        if filters.date_to is not None:
            metrics = metrics.filter(ClinicalReportMetric.created_at <= filters.date_to)
        documented = metrics.filter(ClinicalReportMetric.metric_value.isnot(None)).count()
        reported = metrics.filter(ClinicalReportMetric.metric_value == "True").count()
        return reported, documented

    def report_finalization_hours(self, filters: AnalyticsFilters) -> tuple[list[float], int]:
        query = Report.query.filter(
            Report.is_archived.is_(False),
            Report.status.in_([STATUS_FINALIZED, STATUS_LOCKED]),
            Report.finalized_at.isnot(None),
        )
        if filters.department_id is not None:
            query = query.filter_by(department_id=filters.department_id)
        if filters.date_from is not None:
            query = query.filter(Report.created_at >= filters.date_from)
        if filters.date_to is not None:
            query = query.filter(Report.created_at <= filters.date_to)
        hours: list[float] = []
        for report in query.all():
            if report.finalized_at and report.created_at:
                delta = report.finalized_at - report.created_at
                hours.append(delta.total_seconds() / 3600)
        return hours, query.count()

    def waiting_time_days(self, filters: AnalyticsFilters) -> tuple[list[float], int]:
        query = WaitingListEntry.query.filter_by(is_archived=False, status="active")
        if filters.department_id is not None:
            query = query.filter_by(department_id=filters.department_id)
        now = datetime.now(timezone.utc)
        days: list[float] = []
        for entry in query.all():
            if entry.listed_at:
                days.append((now - entry.listed_at).total_seconds() / 86400)
        return days, query.count()

    def documentation_delay_hours(self, filters: AnalyticsFilters) -> tuple[list[float], int]:
        query = SignedClinicalDocument.query.filter(
            SignedClinicalDocument.is_archived.is_(False),
            SignedClinicalDocument.signed_at.isnot(None),
        )
        if filters.department_id is not None:
            query = query.filter_by(department_id=filters.department_id)
        if filters.date_from is not None:
            query = query.filter(SignedClinicalDocument.signed_at >= filters.date_from)
        if filters.date_to is not None:
            query = query.filter(SignedClinicalDocument.signed_at <= filters.date_to)
        hours: list[float] = []
        for doc in query.all():
            encounter = ClinicalEncounter.query.get(doc.encounter_id)
            if encounter and encounter.created_at and doc.signed_at:
                hours.append((doc.signed_at - encounter.created_at).total_seconds() / 3600)
        return hours, query.count()

    def incident_stats(self, filters: AnalyticsFilters) -> tuple[int, dict[str, int]]:
        query = ClinicalIncident.query.filter_by(is_archived=False)
        if filters.department_id is not None:
            query = query.filter_by(department_id=filters.department_id)
        if filters.date_from is not None:
            query = query.filter(ClinicalIncident.incident_date >= filters.date_from)
        if filters.date_to is not None:
            query = query.filter(ClinicalIncident.incident_date <= filters.date_to)
        by_category: dict[str, int] = {}
        for incident in query.all():
            by_category[incident.category] = by_category.get(incident.category, 0) + 1
        return query.count(), by_category

    def escalation_count(self, filters: AnalyticsFilters) -> int:
        query = FollowUpEvent.query.filter_by(is_archived=False, next_action=NEXT_ACTION_ESCALATE)
        if filters.department_id is not None:
            query = query.filter_by(department_id=filters.department_id)
        if filters.date_from is not None:
            query = query.filter(FollowUpEvent.created_at >= filters.date_from)
        if filters.date_to is not None:
            query = query.filter(FollowUpEvent.created_at <= filters.date_to)
        return query.count()

    def monthly_encounter_counts(self, filters: AnalyticsFilters) -> list[dict]:
        rows = self._encounter_query(filters).all()
        buckets: dict[str, int] = {}
        for row in rows:
            key = row.created_at.strftime("%Y-%m")
            buckets[key] = buckets.get(key, 0) + 1
        return [{"month": month, "count": count} for month, count in sorted(buckets.items())]

    def monthly_procedure_counts(self, filters: AnalyticsFilters) -> list[dict]:
        query = ProcedureSession.query.filter_by(is_archived=False)
        if filters.department_id is not None:
            query = query.filter_by(department_id=filters.department_id)
        if filters.date_from is not None:
            query = query.filter(ProcedureSession.created_at >= filters.date_from)
        if filters.date_to is not None:
            query = query.filter(ProcedureSession.created_at <= filters.date_to)
        buckets: dict[str, int] = {}
        for row in query.all():
            key = row.created_at.strftime("%Y-%m")
            buckets[key] = buckets.get(key, 0) + 1
        return [{"month": month, "count": count} for month, count in sorted(buckets.items())]

    def hospital_encounter_count(self, filters: AnalyticsFilters) -> int:
        hospital_filters = AnalyticsFilters(
            physician_id=filters.physician_id,
            date_from=filters.date_from,
            date_to=filters.date_to,
        )
        return self.count_encounters(hospital_filters)
