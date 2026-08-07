"""Clinical Interpretation orchestration services."""

from __future__ import annotations

from typing import Any

from app.core.exceptions import NotFoundError, ValidationError
from app.engines import audit_engine
from app.extensions import db
from app.modules.clinical_assessment import services as assessment_services
from app.modules.clinical_history_ai.constants import SESSION_STATUS_APPROVED
from app.modules.clinical_history_ai.models import GuidedHistorySession
from app.modules.clinical_interpretation.constants import (
    AUDIT_PREFIX,
    DECISION_ACCEPTED,
    DECISION_MANUAL,
    DECISION_MODIFIED,
    DECISION_REJECTED,
    FINDING_STATUS_SUGGESTED,
    RUN_STATUS_GENERATED,
    RUN_STATUS_REVIEWED,
)
from app.modules.clinical_interpretation.context_builder import InterpretationContextBuilder
from app.modules.clinical_interpretation.diagnostic_update import DiagnosticUpdateEngine
from app.modules.clinical_interpretation.interpretation_engine import (
    InterpretationAIGenerator,
    InterpretationEngine,
)
from app.modules.clinical_interpretation.models import (
    ClinicalInterpretationRun,
    DifferentialUpdateRecord,
    InterpretationFinding,
    PhysicianInterpretationDecision,
)
from app.modules.clinical_interpretation.permissions import (
    require_clinical_interpretation_use,
    require_clinical_interpretation_view,
)
from app.modules.encounters.models import ClinicalEncounter
from app.modules.investigations.models import (
    ImagingStudy,
    LabResultSet,
    RESULT_STATUS_AVAILABLE,
    RESULT_STATUS_REVIEWED,
)


def generate_interpretation(acting_user, encounter_id: int) -> ClinicalInterpretationRun:
    require_clinical_interpretation_use(acting_user)

    encounter = ClinicalEncounter.query.get(encounter_id)
    if encounter is None or encounter.is_archived:
        raise NotFoundError(f"No encounter with id {encounter_id}")

    history_session = GuidedHistorySession.query.filter_by(
        encounter_id=encounter_id, is_archived=False
    ).first()
    if history_session is None or history_session.status != SESSION_STATUS_APPROVED:
        raise ValidationError("Approved structured history is required before clinical interpretation.")

    assessment = assessment_services.get_latest_run_for_encounter(acting_user, encounter_id)
    if assessment is None:
        raise ValidationError("Differential assessment is required before clinical interpretation.")

    if not _has_interpretable_results(encounter.patient_id):
        raise ValidationError(
            "No available laboratory, imaging, or procedure results to interpret for this patient."
        )

    context = InterpretationContextBuilder().build(acting_user, encounter_id)
    engine = InterpretationEngine()
    findings = engine.generate(context)

    ai_result = InterpretationAIGenerator().generate(
        acting_user,
        encounter_id=encounter.id,
        patient_id=encounter.patient_id,
        clinical_context=context,
        deterministic_findings=findings,
    )

    differential_engine = DiagnosticUpdateEngine()
    differential_updates = differential_engine.generate(
        previous_differential=context.get("previous_differential_snapshot") or [],
        interpretation_findings=findings,
    )

    run = ClinicalInterpretationRun(
        encounter_id=encounter.id,
        patient_id=encounter.patient_id,
        assessment_run_id=assessment.id,
        ai_session_uuid=ai_result["ai_session_uuid"],
        provider_key=ai_result["provider_key"],
        model_name=ai_result["model_name"],
        status=RUN_STATUS_GENERATED,
        clinical_data_sources=context.get("clinical_data_sources") or [],
        previous_differential_snapshot=context.get("previous_differential_snapshot") or [],
        knowledge_sources=context.get("knowledge_sources") or [],
        clinical_context=context,
        department_id=encounter.department_id,
        created_by_id=acting_user.id,
    )
    db.session.add(run)
    db.session.flush()

    for item in findings:
        finding = InterpretationFinding(
            run_id=run.id,
            encounter_id=encounter.id,
            patient_id=encounter.patient_id,
            finding_title=item["finding_title"],
            source_type=item["source_type"],
            source_data=item.get("source_data") or {},
            explanation=item.get("explanation"),
            significance=item.get("significance"),
            differential_impact=item.get("differential_impact"),
            related_diagnosis=item.get("related_diagnosis"),
            supporting_diagnoses=item.get("supporting_diagnoses") or [],
            contradicting_diagnoses=item.get("contradicting_diagnoses") or [],
            missing_information=item.get("missing_information") or [],
            knowledge_references=item.get("knowledge_references") or [],
            confidence_indicator=item.get("confidence_indicator", "medium"),
            ai_session_uuid=ai_result["ai_session_uuid"],
            status=FINDING_STATUS_SUGGESTED,
            version=item.get("version", 1),
            department_id=encounter.department_id,
            created_by_id=acting_user.id,
        )
        db.session.add(finding)

    for item in differential_updates:
        record = DifferentialUpdateRecord(
            run_id=run.id,
            encounter_id=encounter.id,
            patient_id=encounter.patient_id,
            diagnosis_name=item["diagnosis_name"],
            previous_confidence=item.get("previous_confidence"),
            previous_category=item.get("previous_category"),
            update_direction=item["update_direction"],
            reasoning=item.get("reasoning"),
            related_finding_title=item.get("related_finding_title"),
            version=item.get("version", 1),
            department_id=encounter.department_id,
            created_by_id=acting_user.id,
        )
        db.session.add(record)

    db.session.commit()

    audit_engine.log(
        action=f"{AUDIT_PREFIX}.generation_completed",
        user=acting_user,
        target_type="ClinicalInterpretationRun",
        target_id=run.id,
        details={
            "encounter_id": encounter.id,
            "ai_session_uuid": run.ai_session_uuid,
            "data_sources": run.clinical_data_sources,
            "knowledge_sources": run.knowledge_sources,
            "finding_count": len(findings),
            "differential_update_count": len(differential_updates),
        },
    )
    audit_engine.log(
        action=f"{AUDIT_PREFIX}.suggestions_displayed",
        user=acting_user,
        target_type="ClinicalInterpretationRun",
        target_id=run.id,
        details={
            "finding_titles": [f["finding_title"] for f in findings],
            "differential_updates": [u["diagnosis_name"] for u in differential_updates],
        },
    )
    return run


def _has_interpretable_results(patient_id: int) -> bool:
    for result_set in LabResultSet.query.filter_by(patient_id=patient_id, is_archived=False).all():
        if result_set.status in (RESULT_STATUS_AVAILABLE, RESULT_STATUS_REVIEWED):
            return True
    for study in ImagingStudy.query.filter_by(patient_id=patient_id, is_archived=False).all():
        if study.status in (RESULT_STATUS_AVAILABLE, RESULT_STATUS_REVIEWED):
            return True
    return False


def get_run(acting_user, run_id: int) -> ClinicalInterpretationRun:
    require_clinical_interpretation_view(acting_user)
    run = ClinicalInterpretationRun.query.get(run_id)
    if run is None or run.is_archived:
        raise NotFoundError(f"No interpretation run with id {run_id}")
    return run


def get_latest_run_for_encounter(acting_user, encounter_id: int) -> ClinicalInterpretationRun | None:
    require_clinical_interpretation_view(acting_user)
    return (
        ClinicalInterpretationRun.query.filter_by(encounter_id=encounter_id, is_archived=False)
        .order_by(ClinicalInterpretationRun.created_at.desc())
        .first()
    )


def get_interpretation_view(acting_user, encounter_id: int) -> dict[str, Any]:
    run = get_latest_run_for_encounter(acting_user, encounter_id)
    if run is None:
        return {
            "run": None,
            "findings": [],
            "differential_updates": [],
            "decisions": [],
            "previous_differential_snapshot": [],
        }

    findings = (
        InterpretationFinding.query.filter_by(run_id=run.id, is_archived=False)
        .order_by(InterpretationFinding.id)
        .all()
    )
    updates = (
        DifferentialUpdateRecord.query.filter_by(run_id=run.id, is_archived=False)
        .order_by(DifferentialUpdateRecord.id)
        .all()
    )
    decisions = (
        PhysicianInterpretationDecision.query.filter_by(encounter_id=encounter_id, is_archived=False)
        .order_by(PhysicianInterpretationDecision.created_at.desc())
        .all()
    )

    return {
        "run": run_to_dict(run),
        "findings": [finding_to_dict(f) for f in findings],
        "differential_updates": [update_to_dict(u) for u in updates],
        "decisions": [decision_to_dict(d) for d in decisions],
        "previous_differential_snapshot": run.previous_differential_snapshot,
    }


def review_run(acting_user, run_id: int) -> ClinicalInterpretationRun:
    require_clinical_interpretation_use(acting_user)
    run = get_run(acting_user, run_id)
    run.status = RUN_STATUS_REVIEWED
    db.session.commit()
    audit_engine.log(
        action=f"{AUDIT_PREFIX}.run_reviewed",
        user=acting_user,
        target_type="ClinicalInterpretationRun",
        target_id=run.id,
        details={"encounter_id": run.encounter_id},
    )
    return run


def _get_finding(acting_user, finding_id: int) -> InterpretationFinding:
    require_clinical_interpretation_view(acting_user)
    finding = InterpretationFinding.query.get(finding_id)
    if finding is None or finding.is_archived:
        raise NotFoundError(f"No interpretation finding with id {finding_id}")
    return finding


def _record_decision(
    acting_user,
    *,
    finding: InterpretationFinding | None,
    run: ClinicalInterpretationRun | None,
    encounter_id: int,
    patient_id: int,
    finding_title: str,
    original_title: str | None,
    physician_status: str,
    notes: str | None = None,
    modified_fields: dict | None = None,
) -> PhysicianInterpretationDecision:
    decision = PhysicianInterpretationDecision(
        run_id=run.id if run else (finding.run_id if finding else None),
        finding_id=finding.id if finding else None,
        encounter_id=encounter_id,
        patient_id=patient_id,
        finding_title=finding_title,
        original_finding_title=original_title,
        physician_status=physician_status,
        physician_notes=notes,
        modified_fields=modified_fields or {},
        department_id=getattr(acting_user, "department_id", 1),
        created_by_id=acting_user.id,
    )
    db.session.add(decision)
    return decision


def accept_finding(
    acting_user, finding_id: int, *, notes: str | None = None
) -> PhysicianInterpretationDecision:
    require_clinical_interpretation_use(acting_user)
    finding = _get_finding(acting_user, finding_id)
    decision = _record_decision(
        acting_user,
        finding=finding,
        run=finding.run,
        encounter_id=finding.encounter_id,
        patient_id=finding.patient_id,
        finding_title=finding.finding_title,
        original_title=finding.finding_title,
        physician_status=DECISION_ACCEPTED,
        notes=notes,
    )
    db.session.commit()
    _audit_decision(acting_user, "accepted", finding, decision)
    return decision


def reject_finding(
    acting_user, finding_id: int, *, notes: str | None = None
) -> PhysicianInterpretationDecision:
    require_clinical_interpretation_use(acting_user)
    finding = _get_finding(acting_user, finding_id)
    decision = _record_decision(
        acting_user,
        finding=finding,
        run=finding.run,
        encounter_id=finding.encounter_id,
        patient_id=finding.patient_id,
        finding_title=finding.finding_title,
        original_title=finding.finding_title,
        physician_status=DECISION_REJECTED,
        notes=notes,
    )
    db.session.commit()
    _audit_decision(acting_user, "rejected", finding, decision)
    return decision


def modify_finding(
    acting_user,
    finding_id: int,
    *,
    finding_title: str | None = None,
    explanation: str | None = None,
    notes: str | None = None,
) -> PhysicianInterpretationDecision:
    require_clinical_interpretation_use(acting_user)
    finding = _get_finding(acting_user, finding_id)
    modified_fields: dict[str, Any] = {}
    title = finding_title or finding.finding_title
    if finding_title:
        modified_fields["finding_title"] = finding_title
    if explanation:
        modified_fields["explanation"] = explanation

    decision = _record_decision(
        acting_user,
        finding=finding,
        run=finding.run,
        encounter_id=finding.encounter_id,
        patient_id=finding.patient_id,
        finding_title=title,
        original_title=finding.finding_title,
        physician_status=DECISION_MODIFIED,
        notes=notes,
        modified_fields=modified_fields,
    )
    db.session.commit()
    _audit_decision(acting_user, "modified", finding, decision)
    return decision


def add_manual_interpretation(
    acting_user,
    encounter_id: int,
    *,
    finding_title: str,
    explanation: str | None = None,
    notes: str | None = None,
) -> PhysicianInterpretationDecision:
    require_clinical_interpretation_use(acting_user)
    encounter = ClinicalEncounter.query.get(encounter_id)
    if encounter is None or encounter.is_archived:
        raise NotFoundError(f"No encounter with id {encounter_id}")

    run = get_latest_run_for_encounter(acting_user, encounter_id)
    decision = _record_decision(
        acting_user,
        finding=None,
        run=run,
        encounter_id=encounter.id,
        patient_id=encounter.patient_id,
        finding_title=finding_title,
        original_title=None,
        physician_status=DECISION_MANUAL,
        notes=notes or explanation,
        modified_fields={"explanation": explanation} if explanation else {},
    )
    db.session.commit()
    audit_engine.log(
        action=f"{AUDIT_PREFIX}.physician_manual",
        user=acting_user,
        target_type="PhysicianInterpretationDecision",
        target_id=decision.id,
        details={"encounter_id": encounter_id, "finding_title": finding_title},
    )
    return decision


def _audit_decision(acting_user, action: str, finding: InterpretationFinding, decision) -> None:
    audit_engine.log(
        action=f"{AUDIT_PREFIX}.physician_{action}",
        user=acting_user,
        target_type="PhysicianInterpretationDecision",
        target_id=decision.id,
        details={
            "finding_id": finding.id,
            "finding_title": decision.finding_title,
            "encounter_id": finding.encounter_id,
            "knowledge_references": finding.knowledge_references,
            "ai_session_uuid": finding.ai_session_uuid,
        },
    )


def run_to_dict(run: ClinicalInterpretationRun) -> dict[str, Any]:
    return {
        "id": run.id,
        "encounter_id": run.encounter_id,
        "patient_id": run.patient_id,
        "assessment_run_id": run.assessment_run_id,
        "ai_session_uuid": run.ai_session_uuid,
        "provider_key": run.provider_key,
        "model_name": run.model_name,
        "status": run.status,
        "clinical_data_sources": run.clinical_data_sources,
        "knowledge_sources": run.knowledge_sources,
        "version": run.version,
        "created_at": run.created_at.isoformat() if run.created_at else None,
    }


def finding_to_dict(finding: InterpretationFinding) -> dict[str, Any]:
    return {
        "id": finding.id,
        "run_id": finding.run_id,
        "finding_title": finding.finding_title,
        "source_type": finding.source_type,
        "source_data": finding.source_data,
        "explanation": finding.explanation,
        "significance": finding.significance,
        "differential_impact": finding.differential_impact,
        "related_diagnosis": finding.related_diagnosis,
        "supporting_diagnoses": finding.supporting_diagnoses,
        "contradicting_diagnoses": finding.contradicting_diagnoses,
        "missing_information": finding.missing_information,
        "knowledge_references": finding.knowledge_references,
        "confidence_indicator": finding.confidence_indicator,
        "ai_session_uuid": finding.ai_session_uuid,
        "status": finding.status,
        "version": finding.version,
    }


def update_to_dict(record: DifferentialUpdateRecord) -> dict[str, Any]:
    return {
        "id": record.id,
        "run_id": record.run_id,
        "diagnosis_name": record.diagnosis_name,
        "previous_confidence": record.previous_confidence,
        "previous_category": record.previous_category,
        "update_direction": record.update_direction,
        "reasoning": record.reasoning,
        "related_finding_title": record.related_finding_title,
        "version": record.version,
    }


def decision_to_dict(decision: PhysicianInterpretationDecision) -> dict[str, Any]:
    return {
        "id": decision.id,
        "run_id": decision.run_id,
        "finding_id": decision.finding_id,
        "finding_title": decision.finding_title,
        "original_finding_title": decision.original_finding_title,
        "physician_status": decision.physician_status,
        "physician_notes": decision.physician_notes,
        "modified_fields": decision.modified_fields,
        "created_at": decision.created_at.isoformat() if decision.created_at else None,
    }
