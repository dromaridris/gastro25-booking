"""Migrate clinical history catalogue bundles into Knowledge Library (one-time bootstrap)."""

from __future__ import annotations

import json

from app.core.base_model import utcnow
from app.extensions import db
from app.modules.clinical_history.catalogue_gi_bundles import ALL_INTELLIGENCE_BUNDLES
from app.modules.clinical_history.catalogue_seed import (
    BASE_DIAGNOSES,
    CHIEF_COMPLAINTS,
    COMMON_AND_DIARRHEA_QUESTIONS,
    SHARED_MANAGEMENT,
)
from app.modules.clinical_history.models import (
    ANSWER_TYPE_BOOLEAN,
    ANSWER_TYPE_CHOICE,
    ANSWER_TYPE_TEXT,
    ChiefComplaintDefinition,
)
from app.modules.decision_support.constants import (
    RULE_KIND_INVESTIGATION_ADVANCED,
    RULE_KIND_INVESTIGATION_BASELINE,
    RULE_KIND_PRIOR,
    RULE_KIND_QUESTION,
    RULE_KIND_WEIGHT,
)
from app.modules.knowledge_library.constants import (
    OBJECT_TYPE_CDS_RULE,
    OBJECT_TYPE_COMPLAINT,
    OBJECT_TYPE_DISEASE,
    OBJECT_TYPE_HISTORY_QUESTION,
    OBJECT_TYPE_INVESTIGATION,
    OBJECT_TYPE_MANAGEMENT,
    STATUS_PUBLISHED,
)
from app.modules.knowledge_library.kl_catalog_loader import reset_kl_catalog_index
from app.modules.knowledge_library.models import KnowledgeObjectRecord

_TYPE_MAP = {"boolean": ANSWER_TYPE_BOOLEAN, "choice": ANSWER_TYPE_CHOICE, "text": ANSWER_TYPE_TEXT}


def _add(**kwargs):
    attrs = kwargs.pop("attributes", None)
    rec = KnowledgeObjectRecord(
        published_at=utcnow(),
        department_id=1,
        status=STATUS_PUBLISHED,
        version_label="1.0.0",
        version_sequence=1,
        **kwargs,
    )
    if attrs is not None:
        rec.attributes_json = json.dumps(attrs, ensure_ascii=False)
    db.session.add(rec)
    return rec


def _exists(stable_id: str) -> bool:
    return KnowledgeObjectRecord.query.filter_by(stable_id=stable_id, version_sequence=1).first() is not None


def migrate_catalogue_to_knowledge_library_if_empty() -> int:
    """Seed KL from Python catalogue bundles when registry is empty."""
    if KnowledgeObjectRecord.query.filter_by(object_type=OBJECT_TYPE_COMPLAINT).first() is not None:
        return 0

    count = 0
    for code, name, category, sort_order, kl_key in CHIEF_COMPLAINTS:
        sid = kl_key or f"kl.complaint.{code.replace('hist.', '')}"
        if not _exists(sid):
            _add(
                stable_id=sid,
                object_type=OBJECT_TYPE_COMPLAINT,
                title=name,
                topic_key=kl_key,
                attributes={
                    "complaint_code": code,
                    "category": category,
                    "sort_order": sort_order,
                },
            )
            count += 1

    for dx_code, dx_name, dx_cat, kl_key in BASE_DIAGNOSES:
        sid = kl_key or f"kl.disease.{dx_code.replace('dx.', '')}"
        if not _exists(sid):
            _add(
                stable_id=sid,
                object_type=OBJECT_TYPE_DISEASE,
                title=dx_name,
                topic_key=kl_key,
                attributes={"diagnosis_code": dx_code, "category": dx_cat},
            )
            count += 1

    for code, prompt, section, atype, choices, is_excl, help_text in COMMON_AND_DIARRHEA_QUESTIONS:
        sid = f"kl.question.{code.replace('.', '_')}"
        if not _exists(sid):
            _add(
                stable_id=sid,
                object_type=OBJECT_TYPE_HISTORY_QUESTION,
                title=prompt,
                attributes={
                    "question_code": code,
                    "prompt": prompt,
                    "section": section,
                    "answer_type": atype,
                    "choices": choices,
                    "is_exclusion_question": is_excl,
                    "help_text": help_text,
                },
            )
            count += 1

    for bundle in ALL_INTELLIGENCE_BUNDLES:
        count += _migrate_bundle(bundle)

    for row in SHARED_MANAGEMENT:
        dx_code = row[0]
        sid = row[6] or f"kl.management.{dx_code.replace('dx.', '')}"
        if not _exists(sid):
            _add(
                stable_id=sid,
                object_type=OBJECT_TYPE_MANAGEMENT,
                title=f"Management — {dx_code}",
                topic_key=row[6],
                summary=row[1],
                body=row[2],
                attributes={
                    "diagnosis_code": dx_code,
                    "scores_text": row[3],
                    "red_flags_text": row[4],
                    "follow_up_text": row[5],
                },
            )
            count += 1

    db.session.commit()
    reset_kl_catalog_index()
    return count


def _migrate_bundle(bundle: dict) -> int:
    count = 0
    complaint_code = bundle["complaint_code"]

    for dx_code, dx_name, dx_cat, kl_key in bundle.get("diagnoses") or []:
        sid = kl_key or f"kl.disease.{dx_code.replace('dx.', '')}"
        if not _exists(sid):
            _add(
                stable_id=sid,
                object_type=OBJECT_TYPE_DISEASE,
                title=dx_name,
                topic_key=kl_key,
                attributes={"diagnosis_code": dx_code, "category": dx_cat},
            )
            count += 1

    for row in bundle.get("questions") or []:
        code, prompt, section, atype, choices, is_excl, help_text, _purpose = row
        sid = f"kl.question.{code.replace('.', '_')}"
        if not _exists(sid):
            _add(
                stable_id=sid,
                object_type=OBJECT_TYPE_HISTORY_QUESTION,
                title=prompt,
                attributes={
                    "question_code": code,
                    "prompt": prompt,
                    "section": section,
                    "answer_type": _TYPE_MAP.get(atype, atype),
                    "choices": choices,
                    "is_exclusion_question": is_excl,
                    "help_text": help_text,
                    "complaint_code": complaint_code,
                },
            )
            count += 1

    for complaint, dx, prior in bundle.get("priors") or []:
        sid = f"kl.cds.prior.{complaint}.{dx}".replace(".", "_")
        if not _exists(sid):
            _add(
                stable_id=sid,
                object_type=OBJECT_TYPE_CDS_RULE,
                title=f"Prior {dx}",
                attributes={
                    "rule_kind": RULE_KIND_PRIOR,
                    "complaint_code": complaint,
                    "diagnosis_code": dx,
                    "prior_weight": prior,
                },
            )
            count += 1

    for complaint, qcode, match, dx, delta in bundle.get("weight_rules") or []:
        sid = f"kl.cds.weight.{complaint}.{qcode}.{match}.{dx}".replace(".", "_")[:99]
        if not _exists(sid):
            _add(
                stable_id=sid,
                object_type=OBJECT_TYPE_CDS_RULE,
                title=f"Weight {qcode}→{dx}",
                attributes={
                    "rule_kind": RULE_KIND_WEIGHT,
                    "complaint_code": complaint,
                    "question_code": qcode,
                    "answer_match": match,
                    "diagnosis_code": dx,
                    "weight_delta": delta,
                },
            )
            count += 1

    for rule in bundle.get("rules") or []:
        (
            qcode,
            sort_order,
            purpose,
            priority,
            parent_q,
            parent_a,
            activation_json,
            targets_json,
            rationale,
        ) = rule
        sid = f"kl.cds.qrule.{complaint_code}.{qcode}".replace(".", "_")
        attrs = {
            "rule_kind": RULE_KIND_QUESTION,
            "complaint_code": complaint_code,
            "question_code": qcode,
            "sort_order": sort_order,
            "question_purpose": purpose,
            "differential_priority": priority,
            "parent_question_code": parent_q,
            "parent_answer_required": parent_a,
            "target_diagnosis_codes_json": targets_json,
            "clinical_rationale": rationale,
        }
        if activation_json:
            try:
                attrs["activation_json"] = json.loads(activation_json) if isinstance(activation_json, str) else activation_json
            except json.JSONDecodeError:
                attrs["activation_json"] = activation_json
        if not _exists(sid):
            _add(
                stable_id=sid,
                object_type=OBJECT_TYPE_CDS_RULE,
                title=f"Question rule {qcode}",
                attributes=attrs,
            )
            count += 1

    for idx, row in enumerate(bundle.get("baseline_investigations") or []):
        complaint, inv_code, reason = row
        sid = f"kl.cds.inv.base.{complaint}.{inv_code}".replace(".", "_")
        if not _exists(sid):
            _add(
                stable_id=sid,
                object_type=OBJECT_TYPE_CDS_RULE,
                title=f"Baseline {inv_code}",
                attributes={
                    "rule_kind": RULE_KIND_INVESTIGATION_BASELINE,
                    "complaint_code": complaint,
                    "investigation_code": inv_code,
                    "reason": reason,
                    "sort_order": (idx + 1) * 10,
                },
            )
            count += 1
        inv_sid = f"kl.investigation.{inv_code.replace('.', '_')}"
        if not _exists(inv_sid):
            _add(
                stable_id=inv_sid,
                object_type=OBJECT_TYPE_INVESTIGATION,
                title=inv_code,
                attributes={"investigation_code": inv_code},
            )
            count += 1

    for idx, row in enumerate(bundle.get("advanced_investigations") or []):
        dx, inv_code, reason = row
        sid = f"kl.cds.inv.adv.{dx}.{inv_code}".replace(".", "_")[:99]
        if not _exists(sid):
            _add(
                stable_id=sid,
                object_type=OBJECT_TYPE_CDS_RULE,
                title=f"Advanced {inv_code} for {dx}",
                attributes={
                    "rule_kind": RULE_KIND_INVESTIGATION_ADVANCED,
                    "complaint_code": complaint_code,
                    "diagnosis_code": dx,
                    "investigation_code": inv_code,
                    "reason": reason,
                    "sort_order": (idx + 1) * 10,
                },
            )
            count += 1

    for row in bundle.get("management") or []:
        dx_code = row[0]
        sid = row[6] or f"kl.management.{dx_code.replace('dx.', '')}"
        if not _exists(sid):
            _add(
                stable_id=sid,
                object_type=OBJECT_TYPE_MANAGEMENT,
                title=f"Management — {dx_code}",
                topic_key=row[6],
                summary=row[1],
                body=row[2],
                attributes={
                    "diagnosis_code": dx_code,
                    "scores_text": row[3],
                    "red_flags_text": row[4],
                    "follow_up_text": row[5],
                },
            )
            count += 1

    return count


def kl_catalogue_is_seeded() -> bool:
    return KnowledgeObjectRecord.query.filter_by(object_type=OBJECT_TYPE_COMPLAINT).first() is not None
