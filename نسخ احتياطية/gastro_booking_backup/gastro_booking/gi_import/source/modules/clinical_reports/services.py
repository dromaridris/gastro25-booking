"""
Service layer — Structured Clinical Reports (Sprint 3C).

Uses frozen Sprint 3A for Report lifecycle and ReportSection persistence.
Adds structured payload, workflow, narrative generation, validation, and QI.
"""

import copy
from datetime import datetime, timezone

from app.core.exceptions import NotFoundError, ValidationError
from app.engines import audit_engine
from app.extensions import db
from app.modules.clinical_reports.fields.payload import StructuredPayload
from app.modules.clinical_reports.models import (
    ClinicalReportDocument,
    ClinicalReportMetric,
    ClinicalReportTimelineEvent,
    ClinicalReportWorkflowLog,
    WF_CONTEXT,
    WF_REVIEW,
)
from app.modules.clinical_reports.platform import metrics as metrics_engine
from app.modules.clinical_reports.platform import narrative_engine
from app.modules.clinical_reports.platform import validation_engine
from app.modules.clinical_reports.platform import workflow_engine
from app.modules.clinical_reports.platform.registry import (
    STRUCTURED_TEMPLATE_KEYS,
    TEMPLATE_LABELS,
    load_bundle,
    resolve_structured_template_key,
)
from app.modules.clinical_reports.platform.narrative_polish import apply_vocabulary_narrative_polish
from app.modules.clinical_reports.platform.timeline_helpers import procedure_date_for_report
from app.modules.clinical_reports.vocabulary import seed_vocabulary_if_empty
from app.modules.reports import services as report_services
from app.modules.reports.models import Report, SECTION_IMPRESSION, STATUS_DRAFT


def _utcnow():
    return datetime.now(timezone.utc)


_MANDATORY_FIELDS_PREFIX = "Cannot leave current phase — required fields missing: "


def _humanize_mandatory_field_error(template_key: str, error: ValidationError) -> str:
    """Map stable field IDs in workflow errors to FSD display labels."""
    message = str(error)
    if _MANDATORY_FIELDS_PREFIX not in message:
        return message

    bundle = load_bundle(template_key)
    if bundle.field_schema is None:
        return message

    ids_part = message.split(_MANDATORY_FIELDS_PREFIX, 1)[1]
    field_ids = [field_id.strip() for field_id in ids_part.split(",") if field_id.strip()]
    labels = []
    for field_id in field_ids:
        field_def = bundle.field_schema.field_by_id(field_id)
        labels.append(field_def.label if field_def else field_id)
    return _MANDATORY_FIELDS_PREFIX + ", ".join(labels)


def get_template_key_for_report(report: Report) -> str | None:
    procedure = report.procedure
    if procedure is None or procedure.procedure_type is None:
        return None
    return resolve_structured_template_key(procedure.procedure_type)


def require_structured_template(report: Report) -> str:
    template_key = get_template_key_for_report(report)
    if template_key is None:
        keys = ", ".join(f"'{k}'" for k in STRUCTURED_TEMPLATE_KEYS)
        raise ValidationError(
            f"This procedure type has no structured clinical report template "
            f"(report_template_key must be one of: {keys})."
        )
    return template_key


def list_structured_reports(acting_user):
    reports = report_services.list_reports(acting_user)
    return [r for r in reports if get_template_key_for_report(r) is not None]


def get_document_for_report(report: Report) -> ClinicalReportDocument | None:
    return ClinicalReportDocument.query.filter_by(report_id=report.id, is_archived=False).first()


def _ensure_document(acting_user, report: Report, template_key: str) -> ClinicalReportDocument:
    doc = get_document_for_report(report)
    if doc is not None:
        return doc

    bundle = load_bundle(template_key)
    doc = ClinicalReportDocument(
        report_id=report.id,
        template_key=template_key,
        workflow_state=WF_CONTEXT,
        payload_json="{}",
        department_id=report.department_id,
        created_by_id=getattr(acting_user, "id", None),
    )
    doc.set_payload(copy.deepcopy(bundle.default_payload))
    db.session.add(doc)
    db.session.flush()

    audit_engine.log(
        action="clinical_report.document_created",
        user=acting_user,
        target_type="ClinicalReportDocument",
        target_id=doc.id,
        details={"report_id": report.id, "template_key": template_key},
    )
    db.session.commit()
    return doc


def open_report_for_session(acting_user, procedure_session_id: int) -> tuple[Report, ClinicalReportDocument]:
    seed_vocabulary_if_empty()
    report = report_services.get_or_create_report(acting_user, procedure_session_id)
    template_key = require_structured_template(report)
    document = _ensure_document(acting_user, report, template_key)
    regenerate_narrative(acting_user, report, document)
    return report, document


def get_report_bundle(acting_user, report_id: int) -> tuple[Report, ClinicalReportDocument, str]:
    report = report_services.get_report(acting_user, report_id)
    template_key = require_structured_template(report)
    document = get_document_for_report(report)
    if document is None:
        document = _ensure_document(acting_user, report, template_key)
    return report, document, template_key


def _structured_payload(document: ClinicalReportDocument) -> StructuredPayload:
    return StructuredPayload(document.get_payload(), template_key=document.template_key)


def _persist_payload(document: ClinicalReportDocument, sp: StructuredPayload) -> None:
    document.set_payload(sp.data)


def _ensure_payload_normalized(document: ClinicalReportDocument) -> StructuredPayload:
    raw = document.get_payload()
    sp = StructuredPayload(raw, template_key=document.template_key)
    if raw != sp.data:
        document.set_payload(sp.data)
        db.session.commit()
    return sp


def _valid_phase_keys(template_key: str) -> set[str]:
    bundle = load_bundle(template_key)
    if bundle.field_schema is not None:
        return {s.id for s in bundle.field_schema.sections}
    raise ValidationError(f"No field schema available for template '{template_key}'.")


def update_phase_payload(
    acting_user,
    report: Report,
    document: ClinicalReportDocument,
    phase_key: str,
    phase_data: dict,
) -> ClinicalReportDocument:
    if not report.is_editable:
        raise ValidationError("Report is not editable.")

    if phase_key not in _valid_phase_keys(document.template_key):
        raise ValidationError(f"Unknown phase key: {phase_key}")

    sp = _ensure_payload_normalized(document)
    sp.update_legacy_phase(phase_key, phase_data)
    _persist_payload(document, sp)
    report.last_modified_by_id = getattr(acting_user, "id", None)
    db.session.commit()

    audit_engine.log(
        action="clinical_report.phase_updated",
        user=acting_user,
        target_type="ClinicalReportDocument",
        target_id=document.id,
        details={"phase_key": phase_key, "report_id": report.id},
    )
    _refresh_metrics(document)
    regenerate_narrative(acting_user, report, document)
    return document


def transition_workflow(
    acting_user,
    report: Report,
    document: ClinicalReportDocument,
    to_state: str,
) -> ClinicalReportDocument:
    if not report.is_editable:
        raise ValidationError("Report is not editable.")

    sp = _ensure_payload_normalized(document)
    try:
        workflow_engine.validate_transition(
            document.template_key, document.workflow_state, to_state, sp.data
        )
    except ValidationError as error:
        raise ValidationError(
            _humanize_mandatory_field_error(document.template_key, error)
        ) from error

    from_state = document.workflow_state
    document.workflow_state = to_state
    db.session.add(
        ClinicalReportWorkflowLog(
            document_id=document.id,
            from_state=from_state,
            to_state=to_state,
            user_id=getattr(acting_user, "id", None),
            department_id=document.department_id,
            created_by_id=getattr(acting_user, "id", None),
        )
    )
    db.session.commit()

    audit_engine.log(
        action="clinical_report.workflow_transition",
        user=acting_user,
        target_type="ClinicalReportDocument",
        target_id=document.id,
        details={"from_state": from_state, "to_state": to_state},
    )
    return document


def apply_quick_fill(
    acting_user,
    report: Report,
    document: ClinicalReportDocument,
    profile_key: str,
) -> ClinicalReportDocument:
    if not report.is_editable:
        raise ValidationError("Report is not editable.")

    bundle = load_bundle(document.template_key)
    profile = bundle.quick_fill_profiles.get(profile_key)
    if profile is None:
        raise ValidationError(f"Unknown quick-fill profile: {profile_key}")

    sp = _ensure_payload_normalized(document)
    for field_id, value in profile["values"].items():
        sp.set_field(field_id, value)
    document.last_quick_fill_profile = profile_key
    _persist_payload(document, sp)
    report.last_modified_by_id = getattr(acting_user, "id", None)
    db.session.commit()

    audit_engine.log(
        action="clinical_report.quick_fill_applied",
        user=acting_user,
        target_type="ClinicalReportDocument",
        target_id=document.id,
        details={"profile_key": profile_key},
    )
    _refresh_metrics(document)
    regenerate_narrative(acting_user, report, document)
    return document


def regenerate_narrative(
    acting_user, report: Report, document: ClinicalReportDocument
) -> None:
    if report.status != STATUS_DRAFT:
        return

    sp = _structured_payload(document)
    sections = narrative_engine.generate_narrative(document.template_key, sp.data)
    sections = apply_vocabulary_narrative_polish(sections)
    for section_key, content in sections.items():
        if section_key == SECTION_IMPRESSION and document.impression_edited_manually:
            continue
        report_services.update_section(acting_user, report, section_key, content)


def reset_document_after_unlock(document: ClinicalReportDocument) -> ClinicalReportDocument:
    """Return workflow to review and clear stale validation acknowledgments."""
    document.workflow_state = WF_REVIEW
    sp = _structured_payload(document)
    sp.set_validation_acknowledgments([])
    _persist_payload(document, sp)
    db.session.commit()
    return document


def mark_impression_manual(acting_user, report: Report, document: ClinicalReportDocument) -> None:
    document.impression_edited_manually = True
    report.last_modified_by_id = getattr(acting_user, "id", None)
    db.session.commit()


def evaluate_report_validation(document: ClinicalReportDocument) -> list:
    sp = _structured_payload(document)
    return validation_engine.evaluate_validation(
        document.template_key, sp.data, sp.validation_acknowledgments()
    )


def acknowledge_validation(
    acting_user, report: Report, document: ClinicalReportDocument, rule_ids: list[str]
) -> ClinicalReportDocument:
    sp = _structured_payload(document)
    existing = set(sp.validation_acknowledgments())
    existing.update(rule_ids)
    sp.set_validation_acknowledgments(sorted(existing))
    _persist_payload(document, sp)
    report.last_modified_by_id = getattr(acting_user, "id", None)
    db.session.commit()
    return document


def finalize_report(acting_user, report: Report, document: ClinicalReportDocument) -> Report:
    findings = evaluate_report_validation(document)
    if validation_engine.has_blocking_errors(findings):
        messages = [f.message for f in validation_engine.blocking_findings(findings)]
        raise ValidationError("Cannot finalize: " + "; ".join(messages))

    regenerate_narrative(acting_user, report, document)
    _refresh_metrics(document)
    return report_services.finalize_report(acting_user, report)


def _refresh_metrics(document: ClinicalReportDocument) -> None:
    sp = _structured_payload(document)
    computed = metrics_engine.compute_metrics(document.template_key, sp.data)
    for metric_key, value in computed.items():
        row = ClinicalReportMetric.query.filter_by(
            document_id=document.id, metric_key=metric_key
        ).first()
        if row is None:
            row = ClinicalReportMetric(
                document_id=document.id,
                metric_key=metric_key,
                department_id=document.department_id,
            )
            db.session.add(row)
        row.metric_value = value
        row.is_computed = True
    db.session.commit()


def get_metrics(document: ClinicalReportDocument) -> dict[str, str]:
    rows = ClinicalReportMetric.query.filter_by(document_id=document.id).all()
    return {r.metric_key: r.metric_value for r in rows}


def list_timeline_events(document: ClinicalReportDocument):
    return (
        ClinicalReportTimelineEvent.query.filter_by(document_id=document.id, is_archived=False)
        .order_by(ClinicalReportTimelineEvent.sequence_order.asc())
        .all()
    )


def upsert_timeline_event(
    acting_user,
    document: ClinicalReportDocument,
    event_key: str,
    occurred_at=None,
    sequence_order: int = 0,
) -> ClinicalReportTimelineEvent:
    event = ClinicalReportTimelineEvent.query.filter_by(
        document_id=document.id, event_key=event_key, is_archived=False
    ).first()
    if event is None:
        event = ClinicalReportTimelineEvent(
            document_id=document.id,
            event_key=event_key,
            department_id=document.department_id,
            created_by_id=getattr(acting_user, "id", None),
        )
        db.session.add(event)
    event.occurred_at = occurred_at
    event.sequence_order = sequence_order
    db.session.commit()
    return event


def save_timeline_events(
    acting_user,
    report: Report,
    document: ClinicalReportDocument,
    event_times: dict[str, str | None],
) -> None:
    """Persist timeline event timestamps from form submission."""
    from datetime import datetime

    event_date = procedure_date_for_report(report)
    for sequence_order, (event_key, occurred_at_raw) in enumerate(event_times.items()):
        occurred_at = None
        if occurred_at_raw:
            try:
                parsed_time = datetime.strptime(occurred_at_raw.strip(), "%H:%M").time()
                occurred_at = datetime.combine(event_date, parsed_time)
            except ValueError:
                continue
        upsert_timeline_event(
            acting_user,
            document,
            event_key,
            occurred_at=occurred_at,
            sequence_order=sequence_order,
        )


def workflow_context(report: Report, document: ClinicalReportDocument, template_key: str) -> dict:
    from app.modules.clinical_reports.image_config import max_images_for_template
    from app.modules.clinical_reports.image_services import list_report_images
    from app.modules.clinical_reports.platform.template_schema import qi_labels_from_schema

    bundle = load_bundle(template_key)
    sp = _ensure_payload_normalized(document)
    findings = evaluate_report_validation(document)
    timeline_defs = []
    if bundle.field_schema is not None:
        timeline_defs = [
            {"key": ev.key, "label": ev.label} for ev in bundle.field_schema.components.timeline
        ]
    qi_labels = qi_labels_from_schema(template_key)
    events = list_timeline_events(document)
    timeline_by_key = {ev.event_key: ev for ev in events}
    timeline_labels = {item["key"]: item["label"] for item in timeline_defs}
    blocking_findings = validation_engine.blocking_findings(findings)
    has_timeline_times = any(
        timeline_by_key.get(item["key"]) and timeline_by_key[item["key"]].occurred_at
        for item in timeline_defs
    )
    report_images = list_report_images(document)
    return {
        "template_key": template_key,
        "template_label": bundle.label or TEMPLATE_LABELS.get(template_key, template_key),
        "workflow_state": document.workflow_state,
        "workflow_states": bundle.workflow_states,
        "next_states": workflow_engine.allowed_next_states(bundle, document.workflow_state),
        "payload": sp.legacy_dict(),
        "payload_v2": sp.data,
        "field_schema": bundle.field_schema,
        "validation_findings": findings,
        "blocking_validation_findings": blocking_findings,
        "has_blocking_validation": bool(blocking_findings),
        "metrics": get_metrics(document),
        "timeline_events": events,
        "timeline_by_key": timeline_by_key,
        "timeline_labels": timeline_labels,
        "quick_fill_profiles": bundle.quick_fill_profiles,
        "timeline_event_defs": bundle.timeline_event_defs,
        "timeline_defs": timeline_defs,
        "has_timeline_times": has_timeline_times,
        "qi_labels": qi_labels,
        "report_images": report_images,
        "max_report_images": max_images_for_template(template_key),
        "report_image_count": len(report_images),
    }
