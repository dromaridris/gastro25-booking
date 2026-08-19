"""Investigation services — Sprint 4A-LAB."""

from datetime import date, datetime, time, timezone
from decimal import Decimal, InvalidOperation

from app.core.base_model import utcnow
from app.core.exceptions import NotFoundError, ValidationError
from app.engines import audit_engine, permission_engine
from app.extensions import db
from app.modules.encounters.models import ClinicalEncounter
from app.modules.investigations.catalogue_seed import seed_investigation_catalogue_if_empty
from app.modules.investigations.models import (
    ORDER_KIND_IMAGING,
    ORDER_KIND_LABORATORY,
    ORDER_STATUS_AVAILABLE,
    ORDER_STATUS_CANCELLED,
    ORDER_STATUS_COLLECTED,
    ORDER_STATUS_REQUESTED,
    ORDER_STATUS_REVIEWED,
    RESULT_STATUS_AVAILABLE,
    RESULT_STATUS_DRAFT,
    RESULT_STATUS_REVIEWED,
    TERMINAL_ORDER_STATUSES,
    ImagingStudy,
    InvestigationCatalogueItem,
    InvestigationOrder,
    InvestigationOrderItem,
    InvestigationPanel,
    LabResultSet,
    LabResultValue,
    compute_abnormal_flag,
)
from app.modules.patients.models import Patient


def ensure_catalogue_seeded() -> None:
    seed_investigation_catalogue_if_empty()


def _require(acting_user, code: str, target_id=None):
    permission_engine.require(
        acting_user, code, audit_context={"target_type": "Investigation", "target_id": target_id}
    )


def _parse_decimal(value: str | None) -> Decimal | None:
    if value is None or str(value).strip() == "":
        return None
    try:
        return Decimal(str(value).strip())
    except InvalidOperation as exc:
        raise ValidationError(f"Invalid numeric value: {value}") from exc


def get_order(acting_user, order_id: int) -> InvestigationOrder:
    _require(acting_user, "investigation:view", order_id)
    order = InvestigationOrder.query.get(order_id)
    if order is None or order.is_archived:
        raise NotFoundError(f"No investigation order with id {order_id}")
    return order


def get_lab_result_set(acting_user, result_set_id: int) -> LabResultSet:
    _require(acting_user, "investigation:view", result_set_id)
    result_set = LabResultSet.query.get(result_set_id)
    if result_set is None or result_set.is_archived:
        raise NotFoundError(f"No lab result set with id {result_set_id}")
    return result_set


def get_imaging_study(acting_user, study_id: int) -> ImagingStudy:
    _require(acting_user, "investigation:view", study_id)
    study = ImagingStudy.query.get(study_id)
    if study is None or study.is_archived:
        raise NotFoundError(f"No imaging study with id {study_id}")
    return study


def list_panels(acting_user):
    _require(acting_user, "investigation:view")
    ensure_catalogue_seeded()
    return InvestigationPanel.query.filter_by(is_archived=False).order_by(InvestigationPanel.name).all()


def list_lab_catalogue(acting_user):
    _require(acting_user, "investigation:view")
    ensure_catalogue_seeded()
    return (
        InvestigationCatalogueItem.query.filter_by(item_type="lab_test", is_archived=False)
        .order_by(InvestigationCatalogueItem.sort_order, InvestigationCatalogueItem.name)
        .all()
    )


def list_imaging_catalogue(acting_user):
    _require(acting_user, "investigation:view")
    ensure_catalogue_seeded()
    return (
        InvestigationCatalogueItem.query.filter_by(item_type="imaging_modality", is_archived=False)
        .order_by(InvestigationCatalogueItem.sort_order, InvestigationCatalogueItem.name)
        .all()
    )


def create_lab_order(
    acting_user,
    encounter: ClinicalEncounter,
    panel_id: int = None,
    catalogue_item_ids: list[int] = None,
    clinical_indication: str = None,
    priority: str = "routine",
) -> InvestigationOrder:
    _require(acting_user, "investigation:request")
    ensure_catalogue_seeded()

    if panel_id is None and not catalogue_item_ids:
        raise ValidationError("Select a panel or at least one laboratory test.")

    order = InvestigationOrder(
        encounter_id=encounter.id,
        patient_id=encounter.patient_id,
        order_kind=ORDER_KIND_LABORATORY,
        status=ORDER_STATUS_REQUESTED,
        panel_id=panel_id,
        clinical_indication=(clinical_indication or "").strip() or None,
        priority=priority or "routine",
        ordered_by_id=getattr(acting_user, "id", None),
        department_id=encounter.department_id,
        created_by_id=getattr(acting_user, "id", None),
    )
    db.session.add(order)
    db.session.flush()

    item_ids = set(catalogue_item_ids or [])
    if panel_id:
        panel = InvestigationPanel.query.get(panel_id)
        if panel is None or panel.is_archived:
            raise ValidationError("Invalid panel selected.")
        for member in panel.members:
            item_ids.add(member.catalogue_item_id)

    for cid in item_ids:
        db.session.add(InvestigationOrderItem(order_id=order.id, catalogue_item_id=cid, department_id=encounter.department_id))

    db.session.commit()
    audit_engine.log(
        action="investigation.order_created",
        user=acting_user,
        target_type="InvestigationOrder",
        target_id=order.id,
        details={"order_kind": ORDER_KIND_LABORATORY, "panel_id": panel_id},
    )
    return order


def create_imaging_order(
    acting_user,
    encounter: ClinicalEncounter,
    catalogue_item_id: int,
    clinical_indication: str = None,
    priority: str = "routine",
) -> InvestigationOrder:
    _require(acting_user, "investigation:request")
    ensure_catalogue_seeded()

    item = InvestigationCatalogueItem.query.get(catalogue_item_id)
    if item is None or item.is_archived or item.item_type != "imaging_modality":
        raise ValidationError("Invalid imaging modality selected.")

    order = InvestigationOrder(
        encounter_id=encounter.id,
        patient_id=encounter.patient_id,
        order_kind=ORDER_KIND_IMAGING,
        status=ORDER_STATUS_REQUESTED,
        clinical_indication=(clinical_indication or "").strip() or None,
        priority=priority or "routine",
        ordered_by_id=getattr(acting_user, "id", None),
        department_id=encounter.department_id,
        created_by_id=getattr(acting_user, "id", None),
    )
    db.session.add(order)
    db.session.flush()
    db.session.add(
        InvestigationOrderItem(
            order_id=order.id, catalogue_item_id=item.id, department_id=encounter.department_id
        )
    )
    db.session.commit()
    audit_engine.log(
        action="investigation.order_created",
        user=acting_user,
        target_type="InvestigationOrder",
        target_id=order.id,
        details={"order_kind": ORDER_KIND_IMAGING, "catalogue_item_id": catalogue_item_id},
    )
    return order


def transition_order_status(acting_user, order: InvestigationOrder, new_status: str) -> InvestigationOrder:
    if new_status == ORDER_STATUS_COLLECTED:
        _require(acting_user, "investigation:request", order.id)
    elif new_status in (ORDER_STATUS_AVAILABLE, ORDER_STATUS_REVIEWED):
        if new_status == ORDER_STATUS_REVIEWED:
            _require(acting_user, "investigation:review", order.id)
        else:
            _require(acting_user, "investigation:result_enter", order.id)
    elif new_status == ORDER_STATUS_CANCELLED:
        _require(acting_user, "investigation:request", order.id)
    else:
        raise ValidationError(f"Invalid status: {new_status}")

    if order.status in TERMINAL_ORDER_STATUSES:
        raise ValidationError("Order is in a terminal status.")

    allowed = {
        ORDER_STATUS_REQUESTED: {ORDER_STATUS_COLLECTED, ORDER_STATUS_CANCELLED},
        ORDER_STATUS_COLLECTED: {ORDER_STATUS_AVAILABLE, ORDER_STATUS_CANCELLED},
        ORDER_STATUS_AVAILABLE: {ORDER_STATUS_REVIEWED},
    }
    if new_status not in allowed.get(order.status, set()):
        raise ValidationError(f"Cannot transition from {order.status} to {new_status}.")

    before = order.status
    order.status = new_status
    if new_status == ORDER_STATUS_COLLECTED and order.collected_at is None:
        order.collected_at = utcnow()
    if new_status == ORDER_STATUS_REVIEWED:
        order.reviewed_at = utcnow()
        order.reviewed_by_id = getattr(acting_user, "id", None)
    db.session.commit()

    audit_engine.log(
        action="investigation.order_status_changed",
        user=acting_user,
        target_type="InvestigationOrder",
        target_id=order.id,
        details={"before": before, "after": new_status},
    )
    return order


def create_lab_result_set(
    acting_user,
    encounter: ClinicalEncounter,
    order_id: int = None,
    collected_at: datetime = None,
    resulted_at: datetime = None,
) -> LabResultSet:
    _require(acting_user, "investigation:result_enter")
    result_set = LabResultSet(
        encounter_id=encounter.id,
        patient_id=encounter.patient_id,
        order_id=order_id,
        status=RESULT_STATUS_DRAFT,
        collected_at=collected_at or utcnow(),
        resulted_at=resulted_at,
        department_id=encounter.department_id,
        created_by_id=getattr(acting_user, "id", None),
    )
    db.session.add(result_set)
    db.session.commit()
    audit_engine.log(
        action="investigation.lab_result_set_created",
        user=acting_user,
        target_type="LabResultSet",
        target_id=result_set.id,
        details={"order_id": order_id},
    )
    return result_set


def save_lab_values(acting_user, result_set: LabResultSet, values: dict[int, str]) -> LabResultSet:
    _require(acting_user, "investigation:result_enter", result_set.id)
    if result_set.status == RESULT_STATUS_REVIEWED:
        raise ValidationError("Reviewed result sets cannot be edited.")

    for catalogue_item_id, raw_value in values.items():
        if raw_value is None or str(raw_value).strip() == "":
            continue
        item = InvestigationCatalogueItem.query.get(catalogue_item_id)
        if item is None:
            continue
        numeric = _parse_decimal(raw_value)
        flag = compute_abnormal_flag(numeric, item.reference_range_low, item.reference_range_high)
        existing = LabResultValue.query.filter_by(
            result_set_id=result_set.id, catalogue_item_id=catalogue_item_id
        ).first()
        if existing is None:
            existing = LabResultValue(
                result_set_id=result_set.id,
                catalogue_item_id=catalogue_item_id,
                test_code=item.code,
                department_id=result_set.department_id,
            )
            db.session.add(existing)
        existing.numeric_value = numeric
        existing.text_value = None if numeric is not None else str(raw_value).strip()
        existing.unit = item.default_unit
        existing.reference_low = item.reference_range_low
        existing.reference_high = item.reference_range_high
        existing.reference_text = item.reference_range_text
        existing.abnormal_flag = flag

    db.session.commit()
    audit_engine.log(
        action="investigation.lab_values_updated",
        user=acting_user,
        target_type="LabResultSet",
        target_id=result_set.id,
        details={"value_count": len([v for v in values.values() if v and str(v).strip()])},
    )
    return result_set


def mark_lab_result_available(acting_user, result_set: LabResultSet) -> LabResultSet:
    _require(acting_user, "investigation:result_enter", result_set.id)
    if not result_set.values:
        raise ValidationError("Enter at least one laboratory value before marking available.")
    result_set.status = RESULT_STATUS_AVAILABLE
    result_set.resulted_at = utcnow()
    db.session.commit()

    if result_set.order_id:
        order = InvestigationOrder.query.get(result_set.order_id)
        if order and order.status == ORDER_STATUS_COLLECTED:
            transition_order_status(acting_user, order, ORDER_STATUS_AVAILABLE)

    audit_engine.log(
        action="investigation.lab_result_set_available",
        user=acting_user,
        target_type="LabResultSet",
        target_id=result_set.id,
        details={},
    )
    return result_set


def review_lab_result_set(acting_user, result_set: LabResultSet) -> LabResultSet:
    _require(acting_user, "investigation:review", result_set.id)
    result_set.status = RESULT_STATUS_REVIEWED
    result_set.reviewed_at = utcnow()
    result_set.reviewed_by_id = getattr(acting_user, "id", None)
    db.session.commit()

    if result_set.order_id:
        order = InvestigationOrder.query.get(result_set.order_id)
        if order and order.status == ORDER_STATUS_AVAILABLE:
            transition_order_status(acting_user, order, ORDER_STATUS_REVIEWED)

    audit_engine.log(
        action="investigation.lab_result_set_reviewed",
        user=acting_user,
        target_type="LabResultSet",
        target_id=result_set.id,
        details={},
    )
    from app.modules.workforce.portfolio_events import on_lab_reviewed

    on_lab_reviewed(result_set, acting_user)
    return result_set


def create_imaging_study(
    acting_user,
    encounter: ClinicalEncounter,
    catalogue_item_id: int,
    study_date: date,
    body_region: str = None,
    findings_summary: str = None,
    impression: str = None,
    order_id: int = None,
) -> ImagingStudy:
    _require(acting_user, "investigation:result_enter")
    item = InvestigationCatalogueItem.query.get(catalogue_item_id)
    if item is None or item.is_archived:
        raise ValidationError("Invalid imaging modality.")

    study = ImagingStudy(
        encounter_id=encounter.id,
        patient_id=encounter.patient_id,
        order_id=order_id,
        catalogue_item_id=item.id,
        study_date=study_date,
        body_region=(body_region or "").strip() or None,
        findings_summary=(findings_summary or "").strip() or None,
        impression=(impression or "").strip() or None,
        status=RESULT_STATUS_DRAFT,
        department_id=encounter.department_id,
        created_by_id=getattr(acting_user, "id", None),
    )
    db.session.add(study)
    db.session.commit()
    audit_engine.log(
        action="investigation.imaging_created",
        user=acting_user,
        target_type="ImagingStudy",
        target_id=study.id,
        details={"catalogue_item_id": catalogue_item_id},
    )
    return study


def update_imaging_study(
    acting_user,
    study: ImagingStudy,
    study_date: date = None,
    body_region: str = None,
    findings_summary: str = None,
    impression: str = None,
) -> ImagingStudy:
    _require(acting_user, "investigation:result_enter", study.id)
    if study.status == RESULT_STATUS_REVIEWED:
        raise ValidationError("Reviewed imaging studies cannot be edited.")
    if study_date is not None:
        study.study_date = study_date
    if body_region is not None:
        study.body_region = body_region.strip() or None
    if findings_summary is not None:
        study.findings_summary = findings_summary.strip() or None
    if impression is not None:
        study.impression = impression.strip() or None
    db.session.commit()
    return study


def mark_imaging_available(acting_user, study: ImagingStudy) -> ImagingStudy:
    _require(acting_user, "investigation:result_enter", study.id)
    study.status = RESULT_STATUS_AVAILABLE
    db.session.commit()

    if study.order_id:
        order = InvestigationOrder.query.get(study.order_id)
        if order and order.status not in TERMINAL_ORDER_STATUSES:
            if order.status == ORDER_STATUS_REQUESTED:
                transition_order_status(acting_user, order, ORDER_STATUS_COLLECTED)
                order = InvestigationOrder.query.get(study.order_id)
            if order.status == ORDER_STATUS_COLLECTED:
                transition_order_status(acting_user, order, ORDER_STATUS_AVAILABLE)

    audit_engine.log(
        action="investigation.imaging_available",
        user=acting_user,
        target_type="ImagingStudy",
        target_id=study.id,
        details={},
    )
    return study


def review_imaging_study(acting_user, study: ImagingStudy) -> ImagingStudy:
    _require(acting_user, "investigation:review", study.id)
    study.status = RESULT_STATUS_REVIEWED
    study.reviewed_at = utcnow()
    study.reviewed_by_id = getattr(acting_user, "id", None)
    db.session.commit()
    if study.order_id:
        order = InvestigationOrder.query.get(study.order_id)
        if order and order.status == ORDER_STATUS_AVAILABLE:
            transition_order_status(acting_user, order, ORDER_STATUS_REVIEWED)
    audit_engine.log(
        action="investigation.imaging_reviewed",
        user=acting_user,
        target_type="ImagingStudy",
        target_id=study.id,
        details={},
    )
    from app.modules.workforce.portfolio_events import on_imaging_reviewed

    on_imaging_reviewed(study, acting_user)
    return study


def attach_imaging_file(acting_user, study: ImagingStudy, storage_key: str, content_type: str, file_name: str):
    _require(acting_user, "investigation:result_enter", study.id)
    study.storage_key = storage_key
    study.content_type = content_type
    study.file_name = file_name
    db.session.commit()
    audit_engine.log(
        action="investigation.imaging_file_uploaded",
        user=acting_user,
        target_type="ImagingStudy",
        target_id=study.id,
        details={"file_name": file_name},
    )


def patient_timeline(acting_user, patient_id: int) -> list[dict]:
    _require(acting_user, "investigation:view")
    patient = Patient.query.get(patient_id)
    if patient is None:
        raise NotFoundError(f"No patient with id {patient_id}")

    events: list[dict] = []

    for order in InvestigationOrder.query.filter_by(patient_id=patient_id, is_archived=False).all():
        label = order.panel.name if order.panel else order.order_kind.replace("_", " ").title()
        events.append(
            {
                "kind": "order",
                "timestamp": order.ordered_at,
                "label": f"Order: {label}",
                "status": order.status,
                "id": order.id,
                "url_key": "investigations.view_order",
            }
        )

    for result_set in LabResultSet.query.filter_by(patient_id=patient_id, is_archived=False).all():
        summary_parts = []
        for val in result_set.values[:4]:
            display = val.numeric_value if val.numeric_value is not None else val.text_value
            summary_parts.append(f"{val.test_code}: {display}")
        events.append(
            {
                "kind": "lab",
                "timestamp": result_set.resulted_at or result_set.collected_at or result_set.created_at,
                "label": "Laboratory results",
                "status": result_set.status,
                "summary": "; ".join(summary_parts) if summary_parts else "—",
                "id": result_set.id,
                "url_key": "investigations.view_lab_result",
            }
        )

    for study in ImagingStudy.query.filter_by(patient_id=patient_id, is_archived=False).all():
        mod = study.catalogue_item.name if study.catalogue_item else "Imaging"
        events.append(
            {
                "kind": "imaging",
                "timestamp": datetime.combine(study.study_date, time.min, tzinfo=timezone.utc),
                "label": mod,
                "status": study.status,
                "summary": (study.impression or study.findings_summary or "—")[:120],
                "id": study.id,
                "url_key": "investigations.view_imaging",
            }
        )

    events.sort(key=lambda e: e["timestamp"] or utcnow(), reverse=True)
    return events
