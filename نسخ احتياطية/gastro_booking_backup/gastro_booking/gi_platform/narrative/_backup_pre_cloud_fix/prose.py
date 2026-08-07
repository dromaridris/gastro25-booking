"""Stage 2 — consultant HPI narrative with clinical ordering and quality review."""

from __future__ import annotations

import hashlib
import re

from gi_platform.narrative.semantic import (
    GROUP_ALARM,
    GROUP_ALLERGY,
    GROUP_ASSOCIATED,
    GROUP_DRUGS,
    GROUP_FAMILY,
    GROUP_FUNCTIONAL,
    GROUP_HPI,
    GROUP_PAIN,
    GROUP_PERTINENT_NEGATIVES,
    GROUP_PMH,
    GROUP_PREV_INVESTIGATION,
    GROUP_PREV_TREATMENT,
    GROUP_RISK,
    GROUP_SOCIAL,
    GROUP_SURGICAL,
    GROUP_TIMELINE,
    GROUP_TRAVEL,
    GROUP_EXPOSURE,
    SemanticDocument,
)
from gi_platform.narrative.terminology import clean_chief_complaint, is_alarm_phrase

# Quality gate — reject internal / machine-like output.
_FORBIDDEN_IN_HISTORY = re.compile(
    r'(hist\.|dx\.|q\.|kl\.|dominant complaint|working differential|'
    r'json|collateral symptoms comprised)',
    re.I,
)


def _stable_index(key: str, modulo: int) -> int:
    return int(hashlib.md5(key.encode()).hexdigest()[:8], 16) % modulo


def _oxford_join(items: list[str]) -> str:
    items = [i.strip() for i in items if i and i.strip()]
    if not items:
        return ''
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return ', '.join(items[:-1]) + f", and {items[-1]}"


def _pick(key: str, options: list[str]) -> str:
    return options[_stable_index(key, len(options))]


def _partition_alarm(phrases: list[str]) -> tuple[list[str], list[str]]:
    """Separate alarm phrases from ordinary associated symptoms."""
    ordinary, alarm = [], []
    for p in phrases:
        (alarm if is_alarm_phrase(p) else ordinary).append(p)
    return ordinary, alarm


def _opening_sentence(complaint: str, associated: list[str]) -> str:
    cc = clean_chief_complaint(complaint)
    if associated:
        merged = _oxford_join(associated[:5])
        templates = [
            lambda: f"The patient presented with {cc} associated with {merged}.",
            lambda: f"The patient presented with {cc}, accompanied by {merged}.",
            lambda: f"He presented with {cc} together with {merged}.",
        ]
        return _pick('open|' + cc + merged, templates)()
    templates = [
        lambda: f"The patient presented with {cc}.",
        lambda: f"The illness began with {cc}.",
        lambda: f"Symptoms started with {cc}.",
    ]
    return _pick('open|' + cc, templates)()


def _progression_sentence(timeline: list[str]) -> str:
    if not timeline:
        return ''
    onset_char = [t for t in timeline if t.startswith('of ') and t.endswith('onset')]
    duration = [t for t in timeline if t not in onset_char]
    if onset_char and duration:
        dur_sentence = _progression_sentence(duration)
        onset_word = onset_char[0][len('of '):-len(' onset')]
        return f"{dur_sentence[:-1]}, {onset_word} in onset."
    if onset_char and not duration:
        onset_word = onset_char[0][len('of '):-len(' onset')]
        return f"The illness was {onset_word} in onset."
    merged = _oxford_join(timeline)
    if merged.startswith('present for '):
        dur = merged[len('present for '):]
        options = [
            f"Symptoms had been present for {dur}.",
            f"The illness had been evolving over {dur}.",
            f"Symptoms progressed over {dur}.",
        ]
        return _pick('prog|' + dur, options)
    if re.match(r'^\d', merged) or merged.endswith(('days', 'weeks', 'months', 'hours')):
        options = [
            f"Symptoms had been present for {merged}.",
            f"The illness had been present for {merged}.",
        ]
        return _pick('prog|' + merged, options)
    options = [
        f"Symptoms had been {merged}.",
        f"The illness had been {merged}.",
    ]
    return _pick('prog|' + merged, options)


def _associated_sentence(phrases: list[str]) -> str:
    if not phrases:
        return ''
    merged = _oxford_join(phrases)
    options = [
        f"There was associated {merged}.",
        f"Associated features included {merged}.",
        f"The illness was associated with {merged}.",
    ]
    return _pick('assoc|' + merged, options)


def _negatives_sentence(phrases: list[str]) -> str:
    if not phrases:
        return ''
    merged = _oxford_join(phrases[:8])
    options = [
        f"There was no history of {merged}.",
        f"Pertinent negatives included no {merged}.",
        f"Specifically, there was no {merged}.",
    ]
    return _pick('neg|' + merged, options)


def _risk_sentence(phrases: list[str]) -> str:
    if not phrases:
        return ''
    merged = _oxford_join(phrases)
    options = [
        f"Relevant risk factors included {merged}.",
        f"There was a background history of {merged}.",
        f"Risk factors comprised {merged}.",
    ]
    return _pick('risk|' + merged, options)


def _alarm_sentence(phrases: list[str]) -> str:
    if not phrases:
        return ''
    merged = _oxford_join(phrases)
    options = [
        f"Alarm features included {merged}.",
        f"Of particular concern were {merged}.",
        f"Features raising concern included {merged}.",
    ]
    return _pick('alarm|' + merged, options)


def _pain_sentence(phrases: list[str]) -> str:
    if not phrases:
        return ''
    located = [p for p in phrases if p.startswith('located in the')]
    other = [p for p in phrases if not p.startswith('located in the')]
    clauses = []
    if located:
        clauses.append(f"Pain was {_oxford_join(located)}")
    if other:
        merged = _oxford_join(other)
        clauses.append(f"described as {merged}" if clauses else f"Pain was described as {merged}")
    return (', '.join(clauses) + '.') if clauses else ''


def _paragraph(*parts: str) -> str:
    return ' '.join(p.strip() for p in parts if p and p.strip())


def render_hpi_paragraph(doc: SemanticDocument) -> str:
    """
    Clinical order:
    1. Primary complaint (+ tightly linked associated symptoms in opening)
    2. Progression / timeline
    3. Remaining associated symptoms & pain (not alarm)
    4. Pertinent negatives (also in separate section)
    5. Risk factors
    6. Alarm features (never mixed with ordinary symptoms)
    """
    g = doc.groups
    cc = doc.chief_complaint

    raw_associated = (
        g.get(GROUP_ASSOCIATED, [])
        + g.get(GROUP_HPI, [])
        + g.get(GROUP_FUNCTIONAL, [])
    )
    ordinary_assoc, alarm_from_assoc = _partition_alarm(raw_associated)
    alarm_all = list(dict.fromkeys(g.get(GROUP_ALARM, []) + alarm_from_assoc))

    # Opening: chief complaint + up to 3 linked ordinary symptoms
    opening_assoc = ordinary_assoc[:3]
    remainder_assoc = ordinary_assoc[3:]

    parts = [_opening_sentence(cc, opening_assoc)]

    prog = _progression_sentence(g.get(GROUP_TIMELINE, []))
    if prog:
        parts.append(prog)

    pain = _pain_sentence(g.get(GROUP_PAIN, []))
    if pain:
        parts.append(pain)

    if remainder_assoc:
        parts.append(_associated_sentence(remainder_assoc))

    prev_inv = g.get(GROUP_PREV_INVESTIGATION, [])
    if prev_inv:
        parts.append(f"Previous investigations included {_oxford_join(prev_inv)}.")

    prev_tx = g.get(GROUP_PREV_TREATMENT, [])
    if prev_tx:
        parts.append(f"Prior treatments included {_oxford_join(prev_tx)}.")

    travel = g.get(GROUP_TRAVEL, [])
    if travel:
        parts.append(f"Travel history was notable for {_oxford_join(travel)}.")

    exposure = g.get(GROUP_EXPOSURE, [])
    if exposure:
        parts.append(f"Exposure history included {_oxford_join(exposure)}.")

    negatives = g.get(GROUP_PERTINENT_NEGATIVES, [])
    if negatives:
        parts.append(_negatives_sentence(negatives))

    risk = g.get(GROUP_RISK, [])
    if risk:
        parts.append(_risk_sentence(risk))

    if alarm_all:
        parts.append(_alarm_sentence(alarm_all))

    return _paragraph(*parts)


def _render_background(phrases: list[str], *, empty: str, opener: str) -> str:
    if not phrases:
        return empty
    return f"{opener} {_oxford_join(phrases)}."


def render_background_sections(doc: SemanticDocument) -> dict[str, str]:
    g = doc.groups
    return {
        'past_medical_history': _render_background(
            g.get(GROUP_PMH, []), empty='No significant past medical history was recorded.',
            opener='Past medical history included'),
        'surgical_history': _render_background(
            g.get(GROUP_SURGICAL, []), empty='No previous relevant surgery was recorded.',
            opener='Previous surgery included'),
        'drug_history': _render_background(
            g.get(GROUP_DRUGS, []), empty='No regular medications were recorded.',
            opener='Current medications included'),
        'allergy_history': _render_background(
            g.get(GROUP_ALLERGY, []), empty='No known drug allergies were recorded.',
            opener='Allergies included'),
        'family_history': _render_background(
            g.get(GROUP_FAMILY, []), empty='Family history was unremarkable.',
            opener='Family history included'),
        'social_history': _render_background(
            g.get(GROUP_SOCIAL, []), empty='Social history was not elaborated.',
            opener='Social history included'),
    }


def _quality_clean(text: str) -> str:
    t = text
    t = re.sub(r'\bhist\.\S+', '', t, flags=re.I)
    t = re.sub(r'\b(q|dx|kl|proc|lab|img)\.\S+', '', t, flags=re.I)
    t = re.sub(r'\s{2,}', ' ', t)
    return t.strip()


def _quality_review(sections: dict[str, str]) -> dict[str, str]:
    """Final pass — strip internal codes and forbidden machine phrasing."""
    out = {}
    for key, body in sections.items():
        if not body:
            continue
        cleaned = _quality_clean(body)
        if key in ('hpi', 'relevant_negatives') and _FORBIDDEN_IN_HISTORY.search(cleaned):
            cleaned = re.sub(r'dominant complaint', 'presenting complaint', cleaned, flags=re.I)
            cleaned = _quality_clean(cleaned)
        out[key] = cleaned
    return out


def render_from_semantic_document(doc: SemanticDocument) -> dict[str, str]:
    hpi = render_hpi_paragraph(doc)
    sections = {
        'hpi': hpi,
        **render_background_sections(doc),
    }
    return _quality_review(sections)
