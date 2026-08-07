"""Discriminating question planner — maximize hypothesis exclusion (information gain).

Uses CKP ClinicalReasoningEngine.plan_questions when a linked session exists;
otherwise heuristic from CDS adaptive history + diagnosis-rule weight effects.
Structured widgets only — never default to free-text when a structured type exists.

Each planned question is annotated with a one-line rule-in / rule-out coaching note
against the active differential (why this question was asked now).
"""

from __future__ import annotations

import re
from typing import Any

from gi_platform.unified_encounter.seeds import ONSET_TIMING_CHOICES, YES_NO_UNKNOWN

STRUCTURED_TYPES = frozenset({
    'boolean', 'choice', 'select', 'multiple_choice', 'multi_choice',
    'numeric', 'number', 'date', 'scale', 'duration',
})

# Topic keywords in prompt/code → disease-name fragments to rule in / out when present
# in the active differential. Matched case-insensitively against dx labels.
_WHY_TOPICS: list[dict[str, Any]] = [
    {
        'keys': ('family history of ibd', 'family history.*ibd', 'fh.*ibd', 'ibd family'),
        'rule_in': ('inflammatory bowel', 'crohn', 'ulcerative colitis', 'ibd'),
        'rule_out': ('haemorrhoid', 'hemorrhoid', 'anal fissure', 'fissure'),
        'line': 'Yes raises IBD; No makes hereditary IBD less likely and leaves benign anorectal causes more plausible.',
    },
    {
        'keys': ('nocturnal diarrhea', 'nocturnal diarrhoea', 'night.*diarrh', 'wakes.*diarrh'),
        'rule_in': ('inflammatory bowel', 'crohn', 'ulcerative colitis', 'ibd', 'colitis'),
        'rule_out': ('haemorrhoid', 'hemorrhoid', 'anal fissure', 'irritable', 'functional'),
        'line': 'Nocturnal diarrhoea is organic — rules IBD/colitis in and functional/benign anorectal sources down.',
    },
    {
        'keys': ('fever',),
        'rule_in': ('inflammatory bowel', 'ibd', 'diverticul', 'infection', 'colitis', 'abscess'),
        'rule_out': ('haemorrhoid', 'hemorrhoid', 'anal fissure'),
        'line': 'Fever supports inflammatory/infectious bleed sources (IBD, diverticulitis) over simple haemorrhoids/fissure.',
    },
    {
        'keys': ('weight loss', 'unintentional weight', 'cachexia'),
        'rule_in': ('colorectal cancer', 'cancer', 'malignan', 'inflammatory bowel', 'ibd'),
        'rule_out': ('haemorrhoid', 'hemorrhoid', 'anal fissure'),
        'line': 'Weight loss rules malignancy/IBD up and simple anorectal bleeding down.',
    },
    {
        'keys': ('visible blood', 'blood in stool', 'rectal bleeding', 'hematochezia', 'haematochezia', 'bright red'),
        'rule_in': ('diverticular', 'colorectal cancer', 'inflammatory bowel', 'haemorrhoid', 'hemorrhoid', 'fissure'),
        'rule_out': ('ascites', 'portal hypertension', 'bowel obstruction'),
        'line': 'Confirms overt rectal bleeding and keeps LGIB sources active vs non-bleed differentials.',
    },
    {
        'keys': ('smoking',),
        'rule_in': ('colorectal cancer', 'cancer', 'crohn', 'diverticular'),
        'rule_out': (),
        'line': 'Smoking raises colorectal cancer / Crohn risk among competing bleed causes.',
    },
    {
        'keys': ('abdominal.*surgery', 'prior surgery', 'previous.*surgery', 'gi surgery', 'surgical history'),
        'rule_in': ('obstruction', 'adhesion', 'diverticular'),
        'rule_out': (),
        'line': 'Prior surgery raises obstruction/adhesion risk and reframes post-operative bleed sources.',
    },
    {
        'keys': ('drug allerg', 'allerg'),
        'rule_in': (),
        'rule_out': (),
        'line': 'Safety for therapy — not a diagnostic separator; does not re-rank the differential.',
    },
    {
        'keys': ('nsaid', 'aspirin', 'anticoagul', 'antiplatelet', 'warfarin', 'doac'),
        'rule_in': ('peptic ulcer', 'diverticular bleed', 'angiodysplasia'),
        'rule_out': (),
        'line': 'Antithrombotic/NSAID exposure raises ulcer and diverticular bleed likelihood.',
    },
    {
        'keys': ('melena', 'black stool', 'tarry'),
        'rule_in': ('peptic ulcer', 'variceal', 'upper gi', 'ugib'),
        'rule_out': ('haemorrhoid', 'hemorrhoid', 'anal fissure'),
        'line': 'Melena points proximal (UGIB); lowers isolated anorectal sources.',
    },
    {
        'keys': ('hemodynamic', 'haemodynamic', 'presyncope', 'syncope', 'orthostatic', 'dizziness', 'collapse'),
        'rule_in': ('massive', 'variceal', 'diverticular bleed', 'ulcer'),
        'rule_out': ('haemorrhoid', 'hemorrhoid', 'anal fissure'),
        'line': 'Instability marks high-acuity bleed — rules simple haemorrhoid/fissure down.',
    },
    {
        'keys': ('liver', 'cirrhosis', 'portal', 'varices', 'jaundice', 'ascites'),
        'rule_in': ('variceal', 'portal hypertension', 'ascites', 'cirrhosis'),
        'rule_out': ('diverticular', 'haemorrhoid', 'hemorrhoid', 'anal fissure'),
        'line': 'Liver/portal features raise variceal / portal-hypertension sources.',
    },
    {
        'keys': ('change in bowel', 'bowel habit', 'constipation', 'narrow stool'),
        'rule_in': ('colorectal cancer', 'cancer', 'obstruction'),
        'rule_out': ('haemorrhoid', 'hemorrhoid', 'anal fissure'),
        'line': 'Habit change with bleeding raises colorectal cancer / obstruction over benign anorectal disease.',
    },
    {
        'keys': ('tenesmus', 'urgency', 'mucus'),
        'rule_in': ('inflammatory bowel', 'ibd', 'colitis', 'proctitis', 'cancer'),
        'rule_out': ('diverticular bleed',),
        'line': 'Tenesmus/urgency/mucus favour colitis/IBD (or distal tumour) over diverticular arterial bleed.',
    },
    {
        'keys': ('pain.*defecation', 'pain on passing', 'anal pain', 'tearing'),
        'rule_in': ('anal fissure', 'fissure', 'haemorrhoid', 'hemorrhoid'),
        'rule_out': ('diverticular', 'colorectal cancer'),
        'line': 'Pain with defecation favours fissure/haemorrhoid over proximal colonic arterial bleed.',
    },
    {
        'keys': ('abdominal pain', 'left lower', 'llq', 'right lower', 'rlq'),
        'rule_in': ('diverticular', 'inflammatory bowel', 'ibd', 'obstruction', 'colitis'),
        'rule_out': ('haemorrhoid', 'hemorrhoid', 'anal fissure'),
        'line': 'Significant abdominal pain with bleeding favours colonic inflammatory/diverticular disease over anorectal sources.',
    },
]


def _norm(s: str) -> str:
    return re.sub(r'\s+', ' ', (s or '').lower()).strip()


def _dx_names(differential: list[dict] | None) -> list[str]:
    names: list[str] = []
    for d in differential or []:
        n = (d.get('name') or d.get('label') or '').strip()
        if n and n not in names:
            names.append(n)
    return names


def _match_names(names: list[str], fragments: tuple[str, ...] | list[str]) -> list[str]:
    if not fragments:
        return []
    hit: list[str] = []
    for n in names:
        nl = n.lower()
        if any(f.lower() in nl for f in fragments if f):
            hit.append(n)
    return hit


def _topic_for_question(q: dict) -> dict[str, Any] | None:
    blob = _norm(f"{q.get('prompt', '')} {q.get('code', '')} {q.get('help_text', '')}")
    for topic in _WHY_TOPICS:
        for key in topic['keys']:
            if re.search(key, blob, re.I):
                return topic
    return None


def _why_from_cds_weights(
    db,
    q: dict,
    differential: list[dict] | None,
) -> tuple[list[str], list[str]]:
    """Return (rule_in_names, rule_out_names) from CDS weight rules when available."""
    complaint = (q.get('complaint_code') or '').strip()
    qcode = (q.get('code') or '').strip()
    if not complaint or not qcode:
        return [], []
    try:
        from gi_platform.decision_support.knowledge_accessor import CdsKnowledgeAccessor
        accessor = CdsKnowledgeAccessor(db)
        rules = [
            r for r in accessor.weight_rules(complaint)
            if r.attributes.get('question_code') == qcode
        ]
    except Exception:
        return [], []
    if not rules:
        return [], []

    dx_lookup = {_norm(n): n for n in _dx_names(differential)}
    rule_in: list[str] = []
    rule_out: list[str] = []
    for rule in rules:
        dx_code = rule.attributes.get('diagnosis_code') or ''
        delta = float(rule.attributes.get('weight_delta') or 0)
        name = None
        try:
            dx_obj = accessor.disease(dx_code)
            name = dx_obj.title if dx_obj else None
        except Exception:
            name = None
        name = name or dx_code
        # Prefer active-differential label if it fuzzy-matches
        matched = _match_names(list(dx_lookup.values()), (name, dx_code.replace('_', ' ').replace('.', ' ')))
        label = matched[0] if matched else name
        if not label:
            continue
        if delta > 0 and label not in rule_in:
            rule_in.append(label)
        elif delta < 0 and label not in rule_out:
            rule_out.append(label)
    # Prefer names that are actually on the active differential
    active = set(_dx_names(differential))
    if active:
        rule_in = [n for n in rule_in if n in active] or rule_in[:3]
        rule_out = [n for n in rule_out if n in active] or rule_out[:3]
    return rule_in[:4], rule_out[:4]


def build_why_line(q: dict, differential: list[dict] | None = None, db=None) -> dict[str, Any]:
    """
    One-line clinician coaching: which active diagnoses this question rules in/out.
    Returns keys: why_line, rule_in, rule_out.
    """
    names = _dx_names(differential)
    rule_in: list[str] = []
    rule_out: list[str] = []
    base_line = ''

    if db is not None:
        rule_in, rule_out = _why_from_cds_weights(db, q, differential)

    topic = _topic_for_question(q)
    if topic:
        if not rule_in:
            rule_in = _match_names(names, topic.get('rule_in') or ())
        if not rule_out:
            rule_out = _match_names(names, topic.get('rule_out') or ())
        base_line = topic.get('line') or ''

    # Red-flag questions without a topic still need a clear purpose.
    if q.get('is_exclusion') and not base_line and not rule_in and not rule_out:
        alarm_targets = _match_names(
            names,
            ('cancer', 'malignan', 'inflammatory bowel', 'ibd', 'variceal', 'massive', 'obstruction'),
        )
        rule_in = rule_in or alarm_targets
        base_line = 'Red-flag screen — a positive answer elevates must-not-miss diagnoses on the list.'

    parts: list[str] = []
    if rule_in:
        parts.append('Rule in: ' + ', '.join(rule_in[:3]))
    if rule_out:
        parts.append('Rule out / down: ' + ', '.join(rule_out[:3]))
    if parts:
        why = ' · '.join(parts)
        if base_line and base_line not in why:
            why = f'{why}. {base_line}'
    elif base_line:
        why = base_line
    elif names:
        top = ', '.join(names[:4])
        why = f'Separates leading hypotheses: {top}.'
    else:
        why = (q.get('help_text') or '').strip() or 'Asked to discriminate among active differential hypotheses.'

    # Keep one readable line for the bedside UI.
    why = re.sub(r'\s+', ' ', why).strip()
    if len(why) > 220:
        why = why[:217].rstrip() + '…'

    return {
        'why_line': why,
        'rule_in': rule_in,
        'rule_out': rule_out,
    }


def annotate_questions_with_why(
    qs: list[dict],
    differential: list[dict] | None = None,
    db=None,
) -> list[dict]:
    for q in qs:
        coaching = build_why_line(q, differential, db=db)
        q['why_line'] = coaching['why_line']
        q['rule_in'] = coaching['rule_in']
        q['rule_out'] = coaching['rule_out']
        # Keep expandable help_text aligned with the visible line.
        if coaching['why_line']:
            existing = (q.get('help_text') or '').strip()
            if not existing or existing.startswith('Chosen for') or existing.startswith('Selected to'):
                q['help_text'] = coaching['why_line']
            elif coaching['why_line'] not in existing:
                q['help_text'] = f"{coaching['why_line']} {existing}".strip()
    return qs


def _force_structured(q: dict) -> dict | None:
    """Ensure question is structured; drop bare free-text analyzable prompts."""
    atype = (q.get('answer_type') or 'text').lower()
    choices = list(q.get('choices') or [])
    allow_other = bool(q.get('allow_other')) or ('Other' in choices)

    if atype in ('select', 'single_choice'):
        atype = 'choice'
    if atype in ('multiple_choice', 'multiselect', 'multi-select'):
        atype = 'multi_choice'
    if atype in ('number', 'scale'):
        atype = 'numeric'
    if atype == 'duration':
        atype = 'choice'
        choices = choices or list(ONSET_TIMING_CHOICES)

    if atype in STRUCTURED_TYPES and atype != 'text':
        if atype in ('choice', 'multi_choice', 'boolean') and not choices:
            choices = list(YES_NO_UNKNOWN)
            atype = 'boolean' if atype == 'boolean' else atype
        q['answer_type'] = 'boolean' if atype == 'boolean' else atype
        q['choices'] = choices
        q['allow_other'] = allow_other
        return q

    if choices:
        q['answer_type'] = 'multi_choice' if atype == 'multi_choice' else 'choice'
        q['choices'] = choices
        q['allow_other'] = allow_other or ('Other' in choices)
        return q

    # Convert free-text analyzable prompts into yes/no when possible.
    prompt = (q.get('prompt') or '').lower().strip()
    if prompt.startswith(('is ', 'are ', 'do ', 'does ', 'did ', 'have ', 'has ', 'any ', 'was ', 'were ')):
        q['answer_type'] = 'boolean'
        q['choices'] = list(YES_NO_UNKNOWN)
        q['allow_other'] = False
        return q
    # Never pass free-text into discriminating batch.
    return None


def plan_from_ckp(db, ckp_session_id: int | None, answered: set[str], limit: int = 4) -> list[dict]:
    if not ckp_session_id:
        return []
    try:
        from clinical_knowledge_platform.workflow.controller import EncounterController
        ctrl = EncounterController(db, ckp_session_id)
        ctrl.engine.plan_questions(ctrl.ebs)
        ctrl.persist()
        action = ctrl.ebs.get('suggested_next_action') or {}
        qs = action.get('questions') or []
        out = []
        for item in qs:
            code = item.get('code') or ''
            if not code or code in answered:
                continue
            row = {
                'code': code,
                'prompt': item.get('prompt') or item.get('label') or code,
                'answer_type': item.get('answer_type') or 'boolean',
                'choices': item.get('choices') or list(YES_NO_UNKNOWN),
                'help_text': (
                    f"Selected to discriminate hypotheses"
                    f"{(' in section ' + action.get('section')) if action.get('section') else ''}."
                ),
                'phase': 'discriminating',
                'source': 'ckp',
            }
            forced = _force_structured(row)
            if forced:
                out.append(forced)
            if len(out) >= limit:
                break
        return out
    except Exception:
        return []


def plan_from_adaptive(db, session_id: int, symptoms: list[dict], answered: set[str], limit: int = 4) -> list[dict]:
    """Use adaptive history engine discrimination scoring across session symptoms."""
    from gi_platform.catalogue_runtime import get_next_questions, normalize_question_view

    out: list[dict] = []
    seen: set[str] = set(answered)
    for sym in symptoms:
        code = sym.get('complaint_code')
        if not code:
            continue
        try:
            qs = get_next_questions(
                db, code, session_id, batch_size=limit * 2,
                symptom_id=sym.get('id'),
                skip_codes=seen,
            )
        except Exception:
            qs = []
        for q in qs:
            q = normalize_question_view(q)
            if q.code in seen:
                continue
            row = {
                'code': q.code,
                'prompt': q.prompt,
                'answer_type': q.answer_type,
                'choices': q.choices,
                'help_text': q.help_text or (
                    'Chosen for diagnostic discrimination among active differential hypotheses.'
                ),
                'symptom_id': sym.get('id'),
                'symptom_name': sym.get('symptom_name'),
                'complaint_code': code,
                'phase': 'discriminating',
                'source': 'adaptive_cds',
                'is_exclusion': bool(q.is_exclusion),
                'allow_other': bool(getattr(q, 'allow_other', False)) or (
                    'Other' in (q.choices or [])
                ),
            }
            forced = _force_structured(row)
            if not forced:
                continue
            seen.add(q.code)
            out.append(forced)
            if len(out) >= limit:
                return out
    return out


def plan_discriminating_questions(
    db,
    *,
    session_id: int,
    symptoms: list[dict],
    answered_codes: set[str],
    ckp_session_id: int | None = None,
    differential: list[dict] | None = None,
    limit: int = 4,
) -> list[dict]:
    """Prefer CKP planner; fall back to adaptive CDS discrimination."""
    qs = plan_from_ckp(db, ckp_session_id, answered_codes, limit=limit)
    if len(qs) < limit:
        more = plan_from_adaptive(
            db, session_id, symptoms,
            answered_codes | {q['code'] for q in qs},
            limit=limit,
        )
        seen = {q['code'] for q in qs}
        for q in more:
            if q['code'] not in seen:
                qs.append(q)
                seen.add(q['code'])
            if len(qs) >= limit:
                break

    # One-line rule-in / rule-out coaching against the active differential.
    return annotate_questions_with_why(qs[:limit], differential, db=db)
