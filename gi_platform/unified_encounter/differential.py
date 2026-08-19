"""Differential enrichment — never empty after characterization (knowledge-driven)."""

from __future__ import annotations

from typing import Any

from gi_platform.unified_encounter.seeds import DIAGNOSIS_PRIOR_SEEDS


def _seed_priors_into_db(db) -> None:
    """Idempotent insert of diagnosis priors into gi_diagnosis_rule."""
    try:
        has = db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='gi_diagnosis_rule'"
        ).fetchone()
    except Exception:
        return
    if not has:
        return
    from gi_platform.clinical_assessment.catalogue_seed import seed_diagnosis_rules_if_empty
    seed_diagnosis_rules_if_empty(db)

    for block in DIAGNOSIS_PRIOR_SEEDS:
        complaint = block['complaint_code']
        for name, category, conf in block['items']:
            exists = db.execute(
                """
                SELECT id FROM gi_diagnosis_rule
                WHERE complaint_code = ? AND diagnosis_name = ?
                """,
                (complaint, name),
            ).fetchone()
            if exists:
                continue
            try:
                db.execute(
                    """
                    INSERT INTO gi_diagnosis_rule (
                        complaint_code, diagnosis_name, category, base_priority, base_confidence,
                        inclusion_reason, supporting_patterns_json, missing_patterns_json,
                        contradicting_patterns_json, specialty_code
                    ) VALUES (?, ?, ?, ?, ?, ?, '[]', '[]', '[]', 'general')
                    """,
                    (
                        complaint, name, category,
                        {'must_not_miss': 5, 'most_likely': 10, 'important_alternative': 15}.get(category, 12),
                        conf,
                        f'Knowledge prior for {complaint} after characterization.',
                    ),
                )
            except Exception:
                pass
    try:
        db.commit()
    except Exception:
        pass


def priors_for_complaint(db, complaint_code: str) -> list[dict]:
    out: list[dict] = []
    try:
        rows = db.execute(
            """
            SELECT diagnosis_name, category, base_confidence, inclusion_reason
            FROM gi_diagnosis_rule
            WHERE complaint_code = ?
            ORDER BY base_priority, id
            """,
            (complaint_code,),
        ).fetchall()
    except Exception:
        rows = []
    for r in rows:
        out.append({
            'name': r['diagnosis_name'],
            'score': float(r['base_confidence'] or 0.4),
            'category': r['category'] or '',
            'rationale': r['inclusion_reason'] or '',
            'from_symptoms': [],
            'source': 'diagnosis_rule',
        })
    if out:
        return out
    # In-memory seed fallback
    for block in DIAGNOSIS_PRIOR_SEEDS:
        if block['complaint_code'] != complaint_code:
            continue
        for name, category, conf in block['items']:
            out.append({
                'name': name,
                'score': float(conf),
                'category': category,
                'rationale': 'Seeded knowledge prior',
                'from_symptoms': [],
                'source': 'seed',
            })
    return out


def try_ckp_differential(db, ckp_session_id: int | None) -> list[dict]:
    if not ckp_session_id:
        return []
    try:
        from clinical_knowledge_platform.workflow.controller import EncounterController
        ctrl = EncounterController(db, ckp_session_id)
        ctrl.engine.rank_differential(ctrl.ebs)
        ctrl.persist()
        diff = ctrl.ebs.get('differential') or []
        out = []
        for item in diff:
            out.append({
                'name': item.get('label') or item.get('code') or 'Hypothesis',
                'score': float(item.get('score') or 0.4),
                'category': item.get('confidence') or item.get('status') or '',
                'confidence': item.get('confidence') or '',
                'from_symptoms': [],
                'source': 'ckp',
                'code': item.get('code'),
            })
        return out
    except Exception:
        return []


def build_enriched_differential(
    db,
    session_id: int,
    *,
    ckp_session_id: int | None = None,
) -> dict[str, Any]:
    """Combined CDS differential + CKP + knowledge priors — never empty if complaints set."""
    from gi_platform import symptom_service

    _seed_priors_into_db(db)
    base = symptom_service.compute_combined_differential(db, session_id)
    merged: dict[str, dict] = {}
    for dx in base.get('diagnoses') or []:
        name = dx.get('name') or ''
        if not name:
            continue
        key = name.lower()
        merged[key] = {
            'name': name,
            'score': float(dx.get('score') or 0.4),
            'category': dx.get('category') or '',
            'from_symptoms': list(dx.get('from_symptoms') or []),
            'source': 'cds',
            'confidence': dx.get('confidence') or '',
        }

    for dx in try_ckp_differential(db, ckp_session_id):
        key = (dx['name'] or '').lower()
        if not key:
            continue
        if key not in merged or float(dx['score']) > merged[key]['score']:
            merged[key] = dx

    symptoms = symptom_service.list_session_symptoms(db, session_id)
    for sym in symptoms:
        for prior in priors_for_complaint(db, sym['complaint_code']):
            key = prior['name'].lower()
            if key not in merged:
                prior = dict(prior)
                prior['from_symptoms'] = [sym.get('symptom_name') or sym['complaint_code']]
                merged[key] = prior
            else:
                if sym.get('symptom_name') and sym['symptom_name'] not in merged[key].get('from_symptoms', []):
                    merged[key].setdefault('from_symptoms', []).append(sym['symptom_name'])
                # Boost slightly when CDS already has it
                merged[key]['score'] = max(merged[key]['score'], prior['score'])

    diagnoses = sorted(merged.values(), key=lambda d: -float(d.get('score') or 0))
    # Confidence labels for UI
    for d in diagnoses:
        score = float(d.get('score') or 0)
        if not d.get('confidence'):
            if score >= 0.75:
                d['confidence'] = 'high'
            elif score >= 0.5:
                d['confidence'] = 'moderate'
            else:
                d['confidence'] = 'low'

    return {
        'diagnoses': diagnoses,
        'symptoms': symptoms,
        'red_flags': base.get('red_flags') or [],
        'investigations': base.get('investigations') or [],
    }
