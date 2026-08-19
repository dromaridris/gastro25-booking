"""Research Variables Framework — CRUD, versioning, resolution (Sprint 6B)."""

from __future__ import annotations

import json

from app.core.base_model import utcnow
from app.core.exceptions import NotFoundError, PermissionDeniedError, ValidationError
from app.engines import audit_engine, permission_engine
from app.extensions import db
from app.modules.patients.models import Patient
from app.modules.research.catalogue_seed import REGISTRY_CONTEXT
from app.modules.research.constants import (
    LEGACY_VALUE_TYPE_MAP,
    ORIGIN_CLINICAL_REFERENCE,
    ORIGIN_MANUAL_ENTRY,
    SOURCE_TYPE_TO_MODULE,
    VALUE_STATUS_DRAFT,
    VALUE_STATUS_SUBMITTED,
)
from app.modules.research.extractors import extract_variable_value
from app.modules.research.models import (
    DiseaseRegistryDefinition,
    ResearchVariableDefinition,
    ResearchVariableGroup,
    ResearchVariableValue,
    ResearchVariableVersion,
)
from app.modules.research.validation import validate_value_for_variable, validate_variable_definition_payload


def _require(user, permission: str) -> None:
    permission_engine.require(user, permission)


def _require_variable_manage(user) -> None:
    _require(user, "research:variable_manage")


def _require_variable_enter(user) -> None:
    _require(user, "research:variable_enter")


def _require_view(user) -> None:
    _require(user, "research:view")


def _get_registry(registry_code: str) -> DiseaseRegistryDefinition:
    reg = DiseaseRegistryDefinition.query.filter_by(code=registry_code, is_archived=False).first()
    if reg is None:
        raise NotFoundError(f"Registry '{registry_code}' not found.")
    return reg


def _snapshot(variable: ResearchVariableDefinition) -> dict:
    return {
        "code": variable.code,
        "stable_id": variable.stable_id,
        "registry_code": variable.registry_code,
        "group_code": variable.group_code,
        "name": variable.name,
        "description": variable.description,
        "category": variable.category,
        "source_module": variable.source_module,
        "source_type": variable.source_type,
        "source_key": variable.source_key,
        "data_type": variable.data_type,
        "value_origin": variable.value_origin,
        "is_required": variable.is_required,
        "validation_rules_json": variable.validation_rules_json,
        "allowed_values_json": variable.allowed_values_json,
        "attachment_config_json": variable.attachment_config_json,
        "version": variable.version,
        "sort_order": variable.sort_order,
        "is_active": variable.is_active,
    }


def _record_version(variable: ResearchVariableDefinition, acting_user) -> ResearchVariableVersion:
    record = ResearchVariableVersion(
        variable_code=variable.code,
        version=variable.version,
        snapshot_json=json.dumps(_snapshot(variable), ensure_ascii=False),
        published_by_id=acting_user.id,
        department_id=variable.department_id,
        created_by_id=acting_user.id,
    )
    db.session.add(record)
    return record


# ---------------------------------------------------------------------------
# Groups
# ---------------------------------------------------------------------------


def create_group(acting_user, registry_code: str, code: str, name: str, description: str = None, sort_order: int = 0):
    _require_variable_manage(acting_user)
    _get_registry(registry_code)
    code = code.strip()
    existing = ResearchVariableGroup.query.filter_by(registry_code=registry_code, code=code, is_archived=False).first()
    if existing:
        raise ValidationError(f"Group '{code}' already exists in registry '{registry_code}'.")
    group = ResearchVariableGroup(
        code=code,
        registry_code=registry_code,
        name=name.strip(),
        description=description,
        sort_order=sort_order,
        department_id=getattr(acting_user, "department_id", 1) or 1,
        created_by_id=acting_user.id,
    )
    db.session.add(group)
    db.session.commit()
    audit_engine.log(
        "research.variable_group_created",
        user=acting_user,
        target_type="research_variable_group",
        target_id=group.id,
        details={"registry_code": registry_code, "code": code},
    )
    return group


def list_groups(acting_user, registry_code: str) -> list[ResearchVariableGroup]:
    _require_view(acting_user)
    _get_registry(registry_code)
    return (
        ResearchVariableGroup.query.filter_by(registry_code=registry_code, is_archived=False, is_active=True)
        .order_by(ResearchVariableGroup.sort_order)
        .all()
    )


# ---------------------------------------------------------------------------
# Variable definitions
# ---------------------------------------------------------------------------


def create_variable(
    acting_user,
    *,
    registry_code: str,
    code: str,
    stable_id: str,
    name: str,
    source_type: str,
    source_key: str,
    data_type: str = "text",
    value_origin: str = ORIGIN_CLINICAL_REFERENCE,
    source_module: str | None = None,
    group_code: str | None = None,
    category: str | None = None,
    description: str | None = None,
    is_required: bool = False,
    validation_rules: dict | None = None,
    allowed_values: list | None = None,
    attachment_config: dict | None = None,
    sort_order: int = 0,
) -> ResearchVariableDefinition:
    _require_variable_manage(acting_user)
    _get_registry(registry_code)
    validate_variable_definition_payload(
        code=code,
        stable_id=stable_id,
        name=name,
        data_type=data_type,
        source_type=source_type,
        source_key=source_key,
        value_origin=value_origin,
        allowed_values=allowed_values,
    )
    if ResearchVariableDefinition.query.filter_by(code=code.strip(), is_archived=False).first():
        raise ValidationError(f"Variable code '{code}' already exists.")
    if ResearchVariableDefinition.query.filter_by(stable_id=stable_id.strip(), is_archived=False).first():
        raise ValidationError(f"Stable ID '{stable_id}' already exists.")

    resolved_module = source_module or SOURCE_TYPE_TO_MODULE.get(source_type)
    variable = ResearchVariableDefinition(
        code=code.strip(),
        stable_id=stable_id.strip(),
        registry_code=registry_code,
        group_code=group_code,
        name=name.strip(),
        description=description,
        category=category,
        source_module=resolved_module,
        source_type=source_type.strip(),
        source_key=source_key.strip(),
        data_type=data_type,
        value_type=data_type,
        value_origin=value_origin,
        is_required=is_required,
        validation_rules_json=json.dumps(validation_rules or {}),
        allowed_values_json=json.dumps(allowed_values or []),
        attachment_config_json=json.dumps(attachment_config or {}),
        version=1,
        sort_order=sort_order,
        department_id=getattr(acting_user, "department_id", 1) or 1,
        created_by_id=acting_user.id,
        updated_by_id=acting_user.id,
    )
    db.session.add(variable)
    db.session.flush()
    _record_version(variable, acting_user)
    db.session.commit()
    audit_engine.log(
        "research.variable_created",
        user=acting_user,
        target_type="research_variable_definition",
        target_id=variable.id,
        details={"code": variable.code, "registry_code": registry_code},
    )
    return variable


def update_variable(acting_user, variable_code: str, **fields) -> ResearchVariableDefinition:
    _require_variable_manage(acting_user)
    variable = ResearchVariableDefinition.query.filter_by(code=variable_code, is_archived=False).first()
    if variable is None:
        raise NotFoundError("Variable not found.")

    mutable = {
        "name",
        "description",
        "category",
        "group_code",
        "source_module",
        "source_type",
        "source_key",
        "data_type",
        "value_origin",
        "is_required",
        "validation_rules",
        "allowed_values",
        "attachment_config",
        "sort_order",
        "is_active",
    }
    changed = False
    for key, value in fields.items():
        if key not in mutable:
            continue
        changed = True
        if key == "validation_rules":
            variable.validation_rules_json = json.dumps(value or {})
        elif key == "allowed_values":
            variable.allowed_values_json = json.dumps(value or [])
        elif key == "attachment_config":
            variable.attachment_config_json = json.dumps(value or {})
        elif key == "data_type":
            variable.data_type = value
            variable.value_type = value
        else:
            setattr(variable, key, value)

    if not changed:
        return variable

    variable.version += 1
    variable.updated_by_id = acting_user.id
    _record_version(variable, acting_user)
    db.session.commit()
    audit_engine.log(
        "research.variable_updated",
        user=acting_user,
        target_type="research_variable_definition",
        target_id=variable.id,
        details={"code": variable.code, "version": variable.version},
    )
    return variable


def archive_variable(acting_user, variable_code: str) -> ResearchVariableDefinition:
    _require_variable_manage(acting_user)
    variable = ResearchVariableDefinition.query.filter_by(code=variable_code, is_archived=False).first()
    if variable is None:
        raise NotFoundError("Variable not found.")
    variable.archive(acting_user.id, reason="Archived via research variable framework")
    db.session.commit()
    audit_engine.log(
        "research.variable_archived",
        user=acting_user,
        target_type="research_variable_definition",
        target_id=variable.id,
        details={"code": variable.code},
    )
    return variable


def get_variable(acting_user, variable_code: str) -> ResearchVariableDefinition:
    _require_view(acting_user)
    variable = ResearchVariableDefinition.query.filter_by(code=variable_code, is_archived=False).first()
    if variable is None:
        raise NotFoundError("Variable not found.")
    return variable


def list_variables_for_registry(acting_user, registry_code: str) -> list[ResearchVariableDefinition]:
    _require_view(acting_user)
    return (
        ResearchVariableDefinition.query.filter_by(registry_code=registry_code, is_archived=False, is_active=True)
        .order_by(ResearchVariableDefinition.sort_order)
        .all()
    )


def list_variables_for_module(acting_user, source_module: str, registry_code: str | None = None) -> list[ResearchVariableDefinition]:
    _require_view(acting_user)
    query = ResearchVariableDefinition.query.filter_by(source_module=source_module, is_archived=False, is_active=True)
    if registry_code:
        query = query.filter_by(registry_code=registry_code)
    return query.order_by(ResearchVariableDefinition.sort_order).all()


def list_variable_versions(acting_user, variable_code: str) -> list[ResearchVariableVersion]:
    _require_view(acting_user)
    get_variable(acting_user, variable_code)
    return (
        ResearchVariableVersion.query.filter_by(variable_code=variable_code, is_archived=False)
        .order_by(ResearchVariableVersion.version.desc())
        .all()
    )


# ---------------------------------------------------------------------------
# Manual research values (never touch clinical modules)
# ---------------------------------------------------------------------------


def save_manual_value(
    acting_user,
    variable_code: str,
    patient_id: int,
    raw_value,
    *,
    enrollment_id: int,
    status: str = VALUE_STATUS_DRAFT,
) -> ResearchVariableValue:
    _require_variable_enter(acting_user)
    variable = ResearchVariableDefinition.query.filter_by(code=variable_code, is_archived=False).first()
    if variable is None:
        raise NotFoundError("Variable not found.")
    if variable.value_origin != ORIGIN_MANUAL_ENTRY:
        raise ValidationError("This variable is not configured for manual entry.")
    if status not in {VALUE_STATUS_DRAFT, VALUE_STATUS_SUBMITTED}:
        raise ValidationError("Invalid research value status.")

    normalised = validate_value_for_variable(variable, raw_value)
    existing = ResearchVariableValue.query.filter_by(
        variable_code=variable_code,
        patient_id=patient_id,
        enrollment_id=enrollment_id,
        is_archived=False,
    ).first()

    if existing:
        existing.value_text = normalised["value_text"]
        existing.value_numeric = normalised["value_numeric"]
        existing.value_json = normalised["value_json"]
        existing.status = status
        existing.variable_version = variable.version
        existing.entered_at = utcnow()
        existing.entered_by_id = acting_user.id
        db.session.commit()
        audit_engine.log(
            "research.manual_value_updated",
            user=acting_user,
            target_type="research_variable_value",
            target_id=existing.id,
            details={"variable_code": variable_code, "patient_id": patient_id},
        )
        return existing

    row = ResearchVariableValue(
        variable_code=variable_code,
        registry_code=variable.registry_code,
        patient_id=patient_id,
        enrollment_id=enrollment_id,
        variable_version=variable.version,
        value_text=normalised["value_text"],
        value_numeric=normalised["value_numeric"],
        value_json=normalised["value_json"],
        status=status,
        entered_by_id=acting_user.id,
        department_id=getattr(acting_user, "department_id", 1) or 1,
        created_by_id=acting_user.id,
    )
    db.session.add(row)
    db.session.commit()
    audit_engine.log(
        "research.manual_value_created",
        user=acting_user,
        target_type="research_variable_value",
        target_id=row.id,
        details={"variable_code": variable_code, "patient_id": patient_id},
    )
    return row


def get_manual_value(variable_code: str, patient_id: int, enrollment_id: int) -> ResearchVariableValue | None:
    return ResearchVariableValue.query.filter_by(
        variable_code=variable_code,
        patient_id=patient_id,
        enrollment_id=enrollment_id,
        is_archived=False,
    ).first()


# ---------------------------------------------------------------------------
# Resolution — clinical reference via CDR; manual from research tables only
# ---------------------------------------------------------------------------


def resolve_variable_value(
    patient: Patient,
    variable: ResearchVariableDefinition,
    *,
    enrollment_id: int | None = None,
    registry_context: dict | None = None,
):
    if variable.value_origin == ORIGIN_MANUAL_ENTRY:
        if enrollment_id is None:
            return None
        row = get_manual_value(variable.code, patient.id, enrollment_id)
        if row is None:
            return None
        if row.value_json:
            try:
                return json.loads(row.value_json)
            except json.JSONDecodeError:
                return row.value_json
        if row.value_numeric is not None:
            return str(row.value_numeric)
        return row.value_text

    ctx = dict(registry_context or {})
    attachment = variable.attachment_config()
    ctx.update({k: v for k, v in attachment.items() if k not in ctx})
    return extract_variable_value(patient, variable.source_type, variable.source_key, registry_context=ctx)


def backfill_legacy_variable_metadata() -> int:
    """Populate Sprint 6B fields on pre-existing 5A variable rows."""
    updated = 0
    for variable in ResearchVariableDefinition.query.filter_by(is_archived=False).all():
        changed = False
        if not variable.stable_id:
            variable.stable_id = variable.code
            changed = True
        if not variable.data_type or variable.data_type == "text" and variable.value_type:
            variable.data_type = LEGACY_VALUE_TYPE_MAP.get(variable.value_type, variable.value_type)
            changed = True
        if not variable.source_module:
            variable.source_module = SOURCE_TYPE_TO_MODULE.get(variable.source_type)
            changed = True
        if not variable.value_origin:
            variable.value_origin = ORIGIN_CLINICAL_REFERENCE
            changed = True
        if variable.version is None or variable.version < 1:
            variable.version = 1
            changed = True
        if changed:
            updated += 1
    if updated:
        db.session.commit()
    return updated
