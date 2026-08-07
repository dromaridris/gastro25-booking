"""Configurable study exports and immutable snapshots — Sprint 6C."""

from __future__ import annotations

import csv
import io
import json
from datetime import date, datetime
from decimal import Decimal
from io import BytesIO

from app.core.exceptions import ValidationError
from app.engines import audit_engine
from app.extensions import db
from app.modules.research import variable_framework
from app.modules.research.catalogue_seed import REGISTRY_CONTEXT
from app.modules.research.models import ResearchVariableDefinition
from app.modules.research.study_constants import EXPORT_FORMAT_CSV, EXPORT_FORMAT_XLSX
from app.modules.research.study_models import ResearchCase, ResearchExportSnapshot, ResearchStudy


def _serialize(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    return value


def _json_safe_row(row: dict) -> dict:
    return {k: _serialize(v) for k, v in row.items()}


def _filter_cases(study: ResearchStudy, filters: dict | None) -> list[ResearchCase]:
    query = ResearchCase.query.filter_by(study_id=study.id, is_archived=False)
    filters = filters or {}
    if filters.get("case_status"):
        query = query.filter(ResearchCase.case_status == filters["case_status"])
    if filters.get("date_from"):
        query = query.filter(ResearchCase.enrolled_at >= filters["date_from"])
    if filters.get("date_to"):
        query = query.filter(ResearchCase.enrolled_at <= filters["date_to"])
    if filters.get("patient_id"):
        query = query.filter(ResearchCase.patient_id == filters["patient_id"])
    return query.order_by(ResearchCase.enrolled_at.desc()).all()


def _variables_for_export(study: ResearchStudy, variable_codes: list[str] | None) -> list[ResearchVariableDefinition]:
    query = ResearchVariableDefinition.query.filter_by(
        registry_code=study.registry_code,
        is_archived=False,
        is_active=True,
    )
    if variable_codes:
        query = query.filter(ResearchVariableDefinition.code.in_(variable_codes))
    return query.order_by(ResearchVariableDefinition.sort_order).all()


def build_study_dataset(
    study: ResearchStudy,
    *,
    variable_codes: list[str] | None = None,
    filters: dict | None = None,
) -> tuple[list[str], list[dict]]:
    cases = _filter_cases(study, filters)
    variables = _variables_for_export(study, variable_codes)
    context = REGISTRY_CONTEXT.get(study.registry_code, {})

    columns = [
        "study_code",
        "case_id",
        "patient_id",
        "mrn",
        "encounter_id",
        "procedure_id",
        "case_status",
        "enrolled_at",
        "completeness_pct",
    ] + [v.code for v in variables]

    rows: list[dict] = []
    for case in cases:
        patient = case.patient
        row = {
            "study_code": study.study_code,
            "case_id": case.id,
            "patient_id": patient.id,
            "mrn": patient.mrn,
            "encounter_id": case.encounter_id,
            "procedure_id": case.procedure_id,
            "case_status": case.case_status,
            "enrolled_at": _serialize(case.enrolled_at),
            "completeness_pct": case.completeness_pct,
        }
        for var in variables:
            row[var.code] = variable_framework.resolve_variable_value(
                patient,
                var,
                enrollment_id=case.registry_enrollment_id,
                registry_context=context,
            )
        rows.append(row)
    return columns, rows


def export_csv(columns: list[str], rows: list[dict]) -> str:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=columns, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow({k: _serialize(row.get(k)) for k in columns})
    return buf.getvalue()


def export_xlsx(columns: list[str], rows: list[dict]) -> bytes:
    try:
        from openpyxl import Workbook
    except ImportError as exc:
        raise ValidationError("Excel export requires openpyxl.") from exc
    wb = Workbook()
    ws = wb.active
    ws.title = "Export"
    ws.append(columns)
    for row in rows:
        ws.append([_serialize(row.get(c)) for c in columns])
    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


def create_snapshot(
    acting_user,
    study: ResearchStudy,
    *,
    snapshot_name: str,
    export_format: str = EXPORT_FORMAT_CSV,
    variable_codes: list[str] | None = None,
    filters: dict | None = None,
) -> ResearchExportSnapshot:
    columns, rows = build_study_dataset(study, variable_codes=variable_codes, filters=filters)
    snapshot = ResearchExportSnapshot(
        study_id=study.id,
        snapshot_name=snapshot_name,
        export_format=export_format,
        filters_json=json.dumps(filters or {}),
        variable_codes_json=json.dumps(variable_codes or []),
        row_count=len(rows),
        data_json=json.dumps({"columns": columns, "rows": [_json_safe_row(r) for r in rows]}),
        exported_by_id=acting_user.id,
        department_id=study.department_id,
        created_by_id=acting_user.id,
        is_frozen=True,
    )
    db.session.add(snapshot)
    db.session.commit()
    audit_engine.log(
        "research.snapshot_created",
        user=acting_user,
        target_type="research_export_snapshot",
        target_id=snapshot.id,
        details={"study_code": study.study_code, "row_count": len(rows)},
    )
    return snapshot


def load_snapshot_data(snapshot: ResearchExportSnapshot) -> tuple[list[str], list[dict]]:
    payload = json.loads(snapshot.data_json)
    return payload.get("columns", []), payload.get("rows", [])
