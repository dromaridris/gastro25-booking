"""Stage 1 — structured answers → semantic clinical groups (disease-agnostic)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from gi_platform.narrative.terminology import (
    clean_chief_complaint,
    extract_clinical_phrase,
    is_alarm_phrase,
    phrase_from_fact,
)

# Semantic buckets used by Stage 2 prose engine.
GROUP_CHIEF_COMPLAINT = 'chief_complaint'
GROUP_TIMELINE = 'timeline'
GROUP_HPI = 'history_of_present_illness'
GROUP_PAIN = 'pain_characteristics'
GROUP_ASSOCIATED = 'associated_symptoms'
GROUP_PERTINENT_NEGATIVES = 'pertinent_negatives'
GROUP_RISK = 'risk_factors'
GROUP_ALARM = 'alarm_features'
GROUP_PMH = 'past_medical_history'
GROUP_SURGICAL = 'surgical_history'
GROUP_DRUGS = 'drug_history'
GROUP_ALLERGY = 'allergy_history'
GROUP_FAMILY = 'family_history'
GROUP_SOCIAL = 'social_history'
GROUP_TRAVEL = 'travel_history'
GROUP_EXPOSURE = 'exposure_history'
GROUP_FUNCTIONAL = 'functional_impact'
GROUP_PREV_INVESTIGATION = 'previous_investigations'
GROUP_PREV_TREATMENT = 'previous_treatments'

ALL_GROUPS = (
    GROUP_CHIEF_COMPLAINT, GROUP_TIMELINE, GROUP_HPI, GROUP_PAIN, GROUP_ASSOCIATED,
    GROUP_PERTINENT_NEGATIVES, GROUP_RISK, GROUP_ALARM, GROUP_PMH, GROUP_SURGICAL,
    GROUP_DRUGS, GROUP_ALLERGY, GROUP_FAMILY, GROUP_SOCIAL, GROUP_TRAVEL, GROUP_EXPOSURE,
    GROUP_FUNCTIONAL, GROUP_PREV_INVESTIGATION, GROUP_PREV_TREATMENT,
)

# Raw questionnaire section → default semantic group.
SECTION_DEFAULT: dict[str, str] = {
    'presenting': GROUP_ASSOCIATED,
    'alarm': GROUP_ALARM,
    'exclusion': GROUP_PERTINENT_NEGATIVES,
    'risk_factor': GROUP_RISK,
    'risk': GROUP_RISK,
    'supports': GROUP_ASSOCIATED,
    'contextual': GROUP_HPI,
    'pmh': GROUP_PMH,
    'surgical': GROUP_SURGICAL,
    'drugs': GROUP_DRUGS,
    'allergy': GROUP_ALLERGY,
    'family': GROUP_FAMILY,
    'social': GROUP_SOCIAL,
}

# Keyword routing within prompts / question codes (longest match wins via iteration order).
_KEYWORD_ROUTES: tuple[tuple[str, str], ...] = (
    (r'\b(onset|duration|how long|when did|started|began|progress|chronicity|acute)\b', GROUP_TIMELINE),
    (r'\b(pain|ache|tender|r\.?u\.?q|l\.?u\.?q|epigastric|retrosternal|colic|odynophagia|radiat)\b', GROUP_PAIN),
    (r'\b(travel|recent trip|abroad|endemic)\b', GROUP_TRAVEL),
    (r'\b(exposure|contact|raw food|shellfish|water source)\b', GROUP_EXPOSURE),
    (r'\b(endoscopy|colonoscopy|egd|imaging|ultrasound|ct |mri|previous investigation|prior scope)\b', GROUP_PREV_INVESTIGATION),
    (r'\b(treatment|therapy|ppi|antibiotic|steroid|transfusion|prior treatment)\b', GROUP_PREV_TREATMENT),
    (r'\b(weight loss|fever|rigors|syncope|bleed|hematemesis|melena|anaemia|jaundice|vomit)\b', GROUP_ASSOCIATED),
    (r'\b(nocturnal|wake|sleep|work|daily activit|function)\b', GROUP_FUNCTIONAL),
    (r'\b(alcohol|smok|nsaid|aspirin|anticoag|drug use|medication)\b', GROUP_RISK),
    (r'\b(family|first.?degree|relative)\b', GROUP_FAMILY),
    (r'\b(allerg)\b', GROUP_ALLERGY),
)

# "No" answers on these topics are clinically relevant pertinent negatives.
_NEGATIVE_RELEVANT = re.compile(
    r'\b(alcohol|hepatotoxic|medication|drug|rash|arthralgia|confusion|'
    r'encephalopathy|travel|iv drug|intravenous|endoscopy|bleed|fever|'
    r'weight loss|vomit|jaundice)\b',
    re.I,
)


@dataclass
class ClinicalFact:
    code: str
    prompt: str
    value: str
    answer_type: str
    section: str
    symptom_name: str = ''
    duration_category: str = ''


@dataclass
class SemanticDocument:
    chief_complaint: str = ''
    groups: dict[str, list[str]] = field(default_factory=dict)

    def add(self, group: str, phrase: str) -> None:
        phrase = (phrase or '').strip()
        if not phrase:
            return
        bucket = self.groups.setdefault(group, [])
        key = phrase.lower()
        if key not in {p.lower() for p in bucket}:
            bucket.append(phrase)


def _classify_group(fact: ClinicalFact) -> str:
    blob = f"{fact.code} {fact.prompt}".lower()
    for pattern, group in _KEYWORD_ROUTES:
        if re.search(pattern, blob, re.I):
            return group
    if fact.section == 'exclusion':
        return GROUP_PERTINENT_NEGATIVES
    if fact.section == 'alarm':
        return GROUP_ALARM
    return SECTION_DEFAULT.get(fact.section, GROUP_HPI)


def _negative_phrase(prompt: str) -> str:
    p = extract_clinical_phrase(prompt, prefer_parenthetical=False)
    return p.lower() if p else prompt.rstrip('?').strip().lower()


def build_multi_symptom_hpi(
    *,
    symptoms: list[dict],
    facts_by_symptom: dict[int | None, list[ClinicalFact]],
    shared_facts: list[ClinicalFact],
) -> str:
    """Build professional HPI with per-symptom paragraphs and combined assessment line."""
    from gi_platform.narrative.prose import render_hpi_paragraph, _paragraph, _oxford_join
    from gi_platform.symptom_service import duration_label

    paragraphs: list[str] = []
    for sym in symptoms:
        sid = sym.get('id')
        sym_facts = list(facts_by_symptom.get(sid, []))
        onset = (sym.get('onset_text') or '').strip()
        dur = duration_label(sym.get('duration_category') or '')
        cc = sym.get('symptom_name') or sym.get('complaint_code') or 'symptom'
        if onset and not any('onset' in f.code.lower() or 'when did' in f.prompt.lower() for f in sym_facts):
            sym_facts.insert(0, ClinicalFact(
                code='sym.onset', prompt='Symptom onset', value=onset,
                answer_type='text', section='presenting', symptom_name=cc, duration_category=dur,
            ))
        doc = build_semantic_document(chief_complaint=cc, facts=sym_facts)
        para = render_hpi_paragraph(doc)
        if dur and para and dur not in para.lower():
            para = para.replace(
                f"presented with {clean_chief_complaint(cc)}.",
                f"presented with {clean_chief_complaint(cc)} ({dur} course).",
                1,
            )
        if para:
            paragraphs.append(para)

    if shared_facts:
        shared_doc = build_semantic_document(chief_complaint='collateral history', facts=shared_facts)
        shared_para = render_hpi_paragraph(shared_doc)
        if shared_para:
            paragraphs.append(shared_para)

    if len(paragraphs) > 1:
        intro = f"The patient presented with {_oxford_join([s.get('symptom_name', '') for s in symptoms])}."
        body = ' '.join(paragraphs)
        return _paragraph(intro, body)
    return _paragraph(*paragraphs)


def build_semantic_document(*, chief_complaint: str, facts: list[ClinicalFact]) -> SemanticDocument:
    doc = SemanticDocument(chief_complaint=chief_complaint.strip())
    doc.add(GROUP_CHIEF_COMPLAINT, clean_chief_complaint(chief_complaint))

    for fact in facts:
        val = (fact.value or '').strip()
        if not val:
            continue
        group = _classify_group(fact)
        is_no = val.lower() in ('no', 'false', '0', 'none', 'denied')

        if is_no:
            blob = f"{fact.code} {fact.prompt}"
            if (
                fact.section in ('exclusion', 'alarm')
                or group in (GROUP_PERTINENT_NEGATIVES, GROUP_ALARM)
                or _NEGATIVE_RELEVANT.search(blob)
            ):
                doc.add(GROUP_PERTINENT_NEGATIVES, _negative_phrase(fact.prompt))
            continue

        if fact.section == 'exclusion' and val.lower() in ('yes', 'true'):
            doc.add(GROUP_ALARM, phrase_from_fact(fact.prompt, val, fact.answer_type, code=fact.code) or _negative_phrase(fact.prompt))
            continue

        phrase = phrase_from_fact(fact.prompt, val, fact.answer_type, code=fact.code)
        if phrase:
            if is_alarm_phrase(phrase) and group not in (GROUP_PERTINENT_NEGATIVES, GROUP_RISK):
                doc.add(GROUP_ALARM, phrase)
            else:
                doc.add(group, phrase)

    return doc
