"""Migrate GI Python catalogue into SQLite knowledge + research tables."""

from __future__ import annotations

import json

from gi_platform import knowledge_service, research_service
from gi_platform.catalogue_loader import load_all_intelligence_bundles, load_research_seed, load_seed_constants

_TYPE_MAP = {'boolean': 'boolean', 'choice': 'choice', 'text': 'text'}


def _slug_exists(db, slug: str) -> bool:
    return db.execute(
        "SELECT 1 FROM gi_knowledge_object WHERE slug = ?", (slug,)
    ).fetchone() is not None


def _insert_object(db, *, slug: str, title: str, object_type: str, summary: str = '',
                   body: dict | None = None, status: str = 'published') -> int | None:
    if _slug_exists(db, slug):
        return None
    return knowledge_service.create_object(
        db, slug=slug, title=title, object_type=object_type,
        summary=summary, body=body or {}, status=status,
    )


def migrate_knowledge_catalogue(db) -> int:
    existing = db.execute(
        "SELECT COUNT(*) AS c FROM gi_knowledge_object WHERE object_type = 'complaint'"
    ).fetchone()['c']
    if existing > 0:
        return 0

    seed = load_seed_constants()
    count = 0

    for code, name, category, sort_order, kl_key in seed.get('CHIEF_COMPLAINTS', []):
        slug = kl_key or f"kl.complaint.{code.replace('hist.', '')}"
        if _insert_object(db, slug=slug, title=name, object_type='complaint', body={
            'complaint_code': code, 'category': category, 'sort_order': sort_order,
        }):
            count += 1

    for dx_code, dx_name, dx_cat, kl_key in seed.get('BASE_DIAGNOSES', []):
        slug = kl_key or f"kl.disease.{dx_code.replace('dx.', '')}"
        if _insert_object(db, slug=slug, title=dx_name, object_type='disease', body={
            'diagnosis_code': dx_code, 'category': dx_cat,
        }):
            count += 1

    for row in seed.get('COMMON_AND_DIARRHEA_QUESTIONS', []):
        code, prompt, section, atype, choices, is_excl, help_text = row[:7]
        slug = f"kl.question.{code.replace('.', '_')}"
        if _insert_object(db, slug=slug, title=prompt, object_type='history_question', body={
            'question_code': code, 'prompt': prompt, 'section': section,
            'answer_type': atype, 'choices': choices,
            'is_exclusion_question': is_excl, 'help_text': help_text,
        }):
            count += 1

    for bundle in load_all_intelligence_bundles():
        count += _migrate_bundle(db, bundle)

    for row in seed.get('SHARED_MANAGEMENT', []):
        dx_code, summary, body_text, scores, red_flags, follow_up, kl_key = row
        slug = kl_key or f"kl.management.{dx_code.replace('dx.', '')}"
        if _insert_object(db, slug=slug, title=f"Management — {dx_code}", object_type='management',
                          summary=summary, body={
                              'diagnosis_code': dx_code, 'body': body_text,
                              'scores_text': scores, 'red_flags_text': red_flags,
                              'follow_up_text': follow_up,
                          }):
            count += 1

    db.execute(
        "INSERT OR REPLACE INTO gi_meta (key, value) VALUES ('catalogue_migrated', ?)",
        (str(count),),
    )
    db.commit()
    return count


def _migrate_bundle(db, bundle: dict) -> int:
    count = 0
    complaint_code = bundle.get('complaint_code', '')

    for dx_code, dx_name, dx_cat, kl_key in bundle.get('diagnoses') or []:
        slug = kl_key or f"kl.disease.{dx_code.replace('dx.', '')}"
        if _insert_object(db, slug=slug, title=dx_name, object_type='disease', body={
            'diagnosis_code': dx_code, 'category': dx_cat, 'complaint_code': complaint_code,
        }):
            count += 1

    for row in bundle.get('questions') or []:
        code, prompt, section, atype, choices, is_excl, help_text = row[:7]
        slug = f"kl.question.{code.replace('.', '_')}"
        if _insert_object(db, slug=slug, title=prompt, object_type='history_question', body={
            'question_code': code, 'prompt': prompt, 'section': section,
            'answer_type': _TYPE_MAP.get(atype, atype), 'choices': choices,
            'is_exclusion_question': is_excl, 'help_text': help_text,
            'complaint_code': complaint_code,
        }):
            count += 1

    for complaint, dx, prior in bundle.get('priors') or []:
        slug = f"kl.cds.prior.{complaint}.{dx}".replace('.', '_')[:120]
        if _insert_object(db, slug=slug, title=f"Prior {dx}", object_type='cds_rule', body={
            'rule_kind': 'prior', 'complaint_code': complaint,
            'diagnosis_code': dx, 'prior_weight': prior,
        }):
            count += 1

    for complaint, qcode, match, dx, delta in bundle.get('weight_rules') or []:
        slug = f"kl.cds.weight.{complaint}.{qcode}.{match}.{dx}".replace('.', '_')[:120]
        if _insert_object(db, slug=slug, title=f"Weight {qcode}→{dx}", object_type='cds_rule', body={
            'rule_kind': 'weight', 'complaint_code': complaint, 'question_code': qcode,
            'answer_match': match, 'diagnosis_code': dx, 'weight_delta': delta,
        }):
            count += 1

    for rule in bundle.get('rules') or []:
        qcode = rule[0]
        slug = f"kl.cds.qrule.{complaint_code}.{qcode}".replace('.', '_')[:120]
        if _insert_object(db, slug=slug, title=f"Question rule {qcode}", object_type='cds_rule', body={
            'rule_kind': 'question', 'complaint_code': complaint_code,
            'question_code': qcode, 'sort_order': rule[1], 'question_purpose': rule[2],
            'differential_priority': rule[3], 'parent_question_code': rule[4],
            'parent_answer_required': rule[5], 'activation_json': rule[6],
            'target_diagnosis_codes_json': rule[7], 'clinical_rationale': rule[8],
        }):
            count += 1

    for row in bundle.get('investigations') or []:
        slug = f"kl.investigation.{complaint_code}.{row[0]}".replace('.', '_')[:120]
        if _insert_object(db, slug=slug, title=row[1], object_type='investigation', body={
            'investigation_code': row[0], 'complaint_code': complaint_code,
            'name': row[1], 'tier': row[2], 'rationale': row[3],
        }):
            count += 1

    for idx, row in enumerate(bundle.get('baseline_investigations') or []):
        complaint, inv_code, reason = row
        slug = f"kl.cds.inv.base.{complaint}.{inv_code}".replace('.', '_')[:120]
        if _insert_object(db, slug=slug, title=f"Baseline {inv_code}", object_type='cds_rule', body={
            'rule_kind': 'investigation_baseline', 'complaint_code': complaint,
            'investigation_code': inv_code, 'reason': reason, 'sort_order': (idx + 1) * 10,
        }):
            count += 1

    for idx, row in enumerate(bundle.get('advanced_investigations') or []):
        dx, inv_code, reason = row
        slug = f"kl.cds.inv.adv.{dx}.{inv_code}".replace('.', '_')[:120]
        if _insert_object(db, slug=slug, title=f"Advanced {inv_code}", object_type='cds_rule', body={
            'rule_kind': 'investigation_advanced', 'complaint_code': complaint_code,
            'diagnosis_code': dx, 'investigation_code': inv_code, 'reason': reason,
            'sort_order': (idx + 1) * 10,
        }):
            count += 1

    for row in bundle.get('management') or []:
        dx_code = row[0]
        slug = row[6] if len(row) > 6 else f"kl.management.{dx_code.replace('dx.', '')}"
        if _insert_object(db, slug=slug, title=f"Management — {dx_code}", object_type='management',
                          summary=row[1], body={
                              'diagnosis_code': dx_code, 'body': row[2],
                              'scores_text': row[3], 'red_flags_text': row[4],
                              'follow_up_text': row[5],
                          }):
            count += 1

    return count


def patch_investigation_rules(db) -> int:
    """Add baseline/advanced investigation CDS rules if missing from earlier migration."""
    existing = db.execute(
        """
        SELECT COUNT(*) AS c FROM gi_knowledge_object
        WHERE object_type = 'cds_rule'
          AND json_extract(body_json, '$.rule_kind') = 'investigation_baseline'
        """
    ).fetchone()['c']
    if existing > 0:
        return 0
    count = 0
    for bundle in load_all_intelligence_bundles():
        complaint_code = bundle.get('complaint_code', '')
        for idx, row in enumerate(bundle.get('baseline_investigations') or []):
            complaint, inv_code, reason = row
            slug = f"kl.cds.inv.base.{complaint}.{inv_code}".replace('.', '_')[:120]
            if _insert_object(db, slug=slug, title=f"Baseline {inv_code}", object_type='cds_rule', body={
                'rule_kind': 'investigation_baseline', 'complaint_code': complaint,
                'investigation_code': inv_code, 'reason': reason, 'sort_order': (idx + 1) * 10,
            }):
                count += 1
        for idx, row in enumerate(bundle.get('advanced_investigations') or []):
            dx, inv_code, reason = row
            slug = f"kl.cds.inv.adv.{dx}.{inv_code}".replace('.', '_')[:120]
            if _insert_object(db, slug=slug, title=f"Advanced {inv_code}", object_type='cds_rule', body={
                'rule_kind': 'investigation_advanced', 'complaint_code': complaint_code,
                'diagnosis_code': dx, 'investigation_code': inv_code, 'reason': reason,
                'sort_order': (idx + 1) * 10,
            }):
                count += 1
    db.commit()
    return count


def migrate_research_catalogue(db) -> int:
    if db.execute("SELECT COUNT(*) AS c FROM gi_research_registry").fetchone()['c'] > 0:
        return 0
    seed = load_research_seed()
    count = 0
    code_to_id: dict[str, int] = {}

    for code, name, description, kl_key, sort_order in seed.get('REGISTRIES', []):
        rid = research_service.create_registry(
            db, code=code, title=name, description=description, status='active',
        )
        code_to_id[code] = rid
        count += 1

    for row in seed.get('VARIABLES', []):
        vcode, registry_code, name, source_type, source_key, value_type, sort_order, desc = row
        rid = code_to_id.get(registry_code)
        if rid:
            research_service.add_variable(
                db, rid, name=name, var_type=value_type, code=vcode,
                source_type=source_type, sort_order=sort_order,
            )
            count += 1

    db.commit()
    return count
