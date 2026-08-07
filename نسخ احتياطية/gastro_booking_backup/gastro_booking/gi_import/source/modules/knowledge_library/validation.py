"""Validate Knowledge Library objects before publishing."""

from __future__ import annotations

import json

from app.core.exceptions import ValidationError
from app.modules.decision_support.constants import (
    RULE_KIND_BRANCH_ACTIVATION,
    RULE_KIND_INVESTIGATION_ADVANCED,
    RULE_KIND_INVESTIGATION_BASELINE,
    RULE_KIND_PRIOR,
    RULE_KIND_QUESTION,
    RULE_KIND_RED_FLAG,
    RULE_KIND_WEIGHT,
)
from app.modules.knowledge_library.constants import (
    OBJECT_TYPE_CDS_RULE,
    OBJECT_TYPE_COMPLAINT,
    OBJECT_TYPE_DISEASE,
    OBJECT_TYPE_GUIDELINE,
    OBJECT_TYPE_HISTORY_QUESTION,
    OBJECT_TYPE_INVESTIGATION,
    OBJECT_TYPE_MANAGEMENT,
    OBJECT_TYPE_SCORE,
    STATUS_PUBLISHED,
)
from app.modules.knowledge_library.models import KnowledgeObjectRecord


def _published_codes(object_type: str, attr_key: str) -> set[str]:
    codes: set[str] = set()
    for row in KnowledgeObjectRecord.query.filter_by(object_type=object_type, status=STATUS_PUBLISHED, is_archived=False):
        val = row.attributes.get(attr_key)
        if val:
            codes.add(val)
    return codes


def _question_codes() -> set[str]:
    return _published_codes(OBJECT_TYPE_HISTORY_QUESTION, "question_code")


def _diagnosis_codes(record: KnowledgeObjectRecord | None = None) -> set[str]:
    codes = _published_codes(OBJECT_TYPE_DISEASE, "diagnosis_code")
    if record and record.object_type == OBJECT_TYPE_DISEASE:
        code = record.attributes.get("diagnosis_code")
        if code:
            codes.add(code)
    return codes


def _complaint_codes(record: KnowledgeObjectRecord | None = None) -> set[str]:
    codes = _published_codes(OBJECT_TYPE_COMPLAINT, "complaint_code")
    if record and record.object_type == OBJECT_TYPE_COMPLAINT:
        code = record.attributes.get("complaint_code")
        if code:
            codes.add(code)
    return codes


def _investigation_codes(record: KnowledgeObjectRecord | None = None) -> set[str]:
    codes = _published_codes(OBJECT_TYPE_INVESTIGATION, "investigation_code")
    if record and record.object_type == OBJECT_TYPE_INVESTIGATION:
        code = record.attributes.get("investigation_code")
        if code:
            codes.add(code)
    return codes


def validate_for_publish(record: KnowledgeObjectRecord) -> list[str]:
    errors: list[str] = []
    attrs = record.attributes
    ot = record.object_type

    if not record.title or not record.title.strip():
        errors.append("Title is required.")

    if ot == OBJECT_TYPE_DISEASE:
        if not attrs.get("diagnosis_code"):
            errors.append("Disease requires attributes.diagnosis_code.")

    elif ot == OBJECT_TYPE_COMPLAINT:
        if not attrs.get("complaint_code"):
            errors.append("Complaint requires attributes.complaint_code.")

    elif ot == OBJECT_TYPE_HISTORY_QUESTION:
        if not attrs.get("question_code"):
            errors.append("History question requires attributes.question_code.")
        if not attrs.get("section"):
            errors.append("History question requires attributes.section.")
        if not attrs.get("answer_type"):
            errors.append("History question requires attributes.answer_type.")
        parent = attrs.get("parent_question_code")
        if parent and parent not in _question_codes() and parent != attrs.get("question_code"):
            errors.append(f"parent_question_code '{parent}' not found in published questions.")

    elif ot == OBJECT_TYPE_INVESTIGATION:
        if not attrs.get("investigation_code"):
            errors.append("Investigation requires attributes.investigation_code.")

    elif ot == OBJECT_TYPE_MANAGEMENT:
        dx = attrs.get("diagnosis_code")
        if not dx:
            errors.append("Management requires attributes.diagnosis_code.")
        elif dx not in _diagnosis_codes(record):
            errors.append(f"diagnosis_code '{dx}' not found among published diseases.")

    elif ot == OBJECT_TYPE_GUIDELINE:
        if not record.summary and not record.body:
            errors.append("Guideline requires summary or body.")

    elif ot == OBJECT_TYPE_SCORE:
        calc = attrs.get("calculation") or attrs
        if not calc.get("formula"):
            errors.append("Clinical score requires calculation.formula.")
        for var in calc.get("variables") or []:
            if not var.get("source_type") or not var.get("source_key"):
                errors.append(f"Score variable '{var.get('variable_code', '?')}' missing source_type/source_key.")

    elif ot == OBJECT_TYPE_CDS_RULE:
        errors.extend(_validate_cds_rule(record, attrs))

    return errors


def _validate_cds_rule(record: KnowledgeObjectRecord, attrs: dict) -> list[str]:
    errors: list[str] = []
    kind = attrs.get("rule_kind")
    if not kind:
        return ["CDS rule requires attributes.rule_kind."]

    complaint = attrs.get("complaint_code")
    if kind != RULE_KIND_INVESTIGATION_ADVANCED and not complaint:
        errors.append("CDS rule requires complaint_code (except advanced-only rules).")
    if complaint and complaint not in _complaint_codes(record):
        errors.append(f"complaint_code '{complaint}' not found among published complaints.")

    if kind == RULE_KIND_PRIOR:
        dx = attrs.get("diagnosis_code")
        if not dx:
            errors.append("Prior rule requires diagnosis_code.")
        elif dx not in _diagnosis_codes(record):
            errors.append(f"diagnosis_code '{dx}' not found.")

    elif kind == RULE_KIND_WEIGHT:
        q = attrs.get("question_code")
        dx = attrs.get("diagnosis_code")
        if not q or attrs.get("answer_match") is None or not dx:
            errors.append("Weight rule requires question_code, answer_match, diagnosis_code.")
        elif q not in _question_codes():
            errors.append(f"question_code '{q}' not found.")
        elif dx not in _diagnosis_codes(record):
            errors.append(f"diagnosis_code '{dx}' not found.")

    elif kind == RULE_KIND_QUESTION:
        q = attrs.get("question_code")
        if not q:
            errors.append("Question rule requires question_code.")
        elif q not in _question_codes():
            errors.append(f"question_code '{q}' not found.")
        parent = attrs.get("parent_question_code")
        if parent and parent not in _question_codes():
            errors.append(f"parent_question_code '{parent}' not found.")
        activation = attrs.get("activation_json") or attrs.get("visible_if")
        if activation:
            errors.extend(_validate_branching(activation, q))

    elif kind in (RULE_KIND_INVESTIGATION_BASELINE, RULE_KIND_INVESTIGATION_ADVANCED):
        inv = attrs.get("investigation_code")
        if not inv:
            errors.append("Investigation rule requires investigation_code.")
        elif inv not in _investigation_codes(record):
            errors.append(f"investigation_code '{inv}' not found.")
        if kind == RULE_KIND_INVESTIGATION_ADVANCED:
            dx = attrs.get("diagnosis_code")
            if not dx:
                errors.append("Advanced investigation rule requires diagnosis_code.")
            elif dx not in _diagnosis_codes(record):
                errors.append(f"diagnosis_code '{dx}' not found.")

    elif kind == RULE_KIND_RED_FLAG:
        if not attrs.get("condition"):
            errors.append("Red flag rule requires condition.")
        if not attrs.get("message") and not record.summary:
            errors.append("Red flag requires message or summary.")

    elif kind == RULE_KIND_BRANCH_ACTIVATION:
        if not attrs.get("branch_code") or not attrs.get("condition"):
            errors.append("Branch activation requires branch_code and condition.")
        errors.extend(_validate_branching(attrs.get("condition"), None))

    return errors


def _validate_branching(spec, self_code: str | None) -> list[str]:
    errors: list[str] = []
    if not spec:
        return errors
    if isinstance(spec, list):
        for item in spec:
            errors.extend(_validate_branching(item, self_code))
        return errors
    if not isinstance(spec, dict):
        return errors

    cond_type = spec.get("type", "answer")
    if cond_type == "answer":
        q = spec.get("question_code")
        if q and q not in _question_codes() and q != self_code:
            errors.append(f"Branching references unknown question '{q}'.")
    elif cond_type in ("and", "or"):
        for sub in spec.get("conditions") or []:
            errors.extend(_validate_branching(sub, self_code))
    return errors


def validate_for_publish_or_raise(record: KnowledgeObjectRecord) -> None:
    errors = validate_for_publish(record)
    if errors:
        raise ValidationError("Cannot publish: " + "; ".join(errors))
