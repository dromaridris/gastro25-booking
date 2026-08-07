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
from gi_platform.narrative.terminology import (
    clean_chief_complaint,
    is_alarm_phrase,
    normalize_duration_phrase,
)

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


_DURATION_UNIT_SUFFIXES = (
    'minutes', 'minute', 'hours', 'hour', 'days', 'day',
    'weeks', 'week', 'months', 'month', 'years', 'year',
)


def _duration_for_prose(raw: str) -> str | None:
    """Normalise a timeline token to a lowercase duration unit, or None."""
    t = (raw or '').strip()
    if not t:
        return None
    if t.lower().startswith('present for '):
        t = t[len('present for '):].strip()
    elif t.lower().startswith('for '):
        t = t[len('for '):].strip()
    return normalize_duration_phrase(t)


def _duration_clause(dur: str) -> str:
    """Prefer natural clinical English for common unit answers."""
    d = (dur or '').strip().lower()
    # Catalogue answers are bare units — "several …' duration" reads better
    # than "present for months" when woven into the opening clause.
    if d in ('months', 'month'):
        return "several months' duration"
    if d in ('years', 'year'):
        return "several years' duration"
    if d in ('weeks', 'week'):
        return "several weeks' duration"
    if d in ('days', 'day'):
        return "several days' duration"
    if d in ('hours', 'hour', 'a few hours'):
        return "a few hours' duration"
    if d in ('minutes', 'minute'):
        return "minutes' duration"
    return f"{d} duration"


def _opening_sentence(
    complaint: str,
    associated: list[str],
    *,
    sub_symptom: bool = False,
    duration: str | None = None,
) -> str:
    cc = clean_chief_complaint(complaint)
    dur = _duration_for_prose(duration) if duration else None
    if sub_symptom:
        # Used for the 2nd+ symptom in a multi-symptom encounter, where the
        # overall intro sentence already named every symptom — repeating
        # "The patient presented with X" for each one reads as robotic
        # word-salad rather than prose, so use a lighter connective instead.
        if associated and dur:
            merged = _oxford_join(associated[:5])
            return (
                f"Regarding {cc}, this had been present for {dur} "
                f"and was associated with {merged}."
            )
        if associated:
            merged = _oxford_join(associated[:5])
            return f"Regarding {cc}, this was associated with {merged}."
        if dur:
            return f"Regarding {cc}, this had been present for {dur}."
        return f"Regarding {cc},"
    if associated:
        merged = _oxford_join(associated[:5])
        if dur:
            return (
                f"The patient presented with {cc} of {_duration_clause(dur)}, "
                f"associated with {merged}."
            )
        templates = [
            lambda: f"The patient presented with {cc} associated with {merged}.",
            lambda: f"The patient presented with {cc}, accompanied by {merged}.",
            lambda: f"He presented with {cc} together with {merged}.",
        ]
        return _pick('open|' + cc + merged, templates)()
    if dur:
        return f"The patient presented with {cc} of {_duration_clause(dur)}."
    templates = [
        lambda: f"The patient presented with {cc}.",
        lambda: f"The illness began with {cc}.",
        lambda: f"The presenting complaint was {cc}.",
    ]
    return _pick('open|' + cc, templates)()


def _progression_sentence(timeline: list[str], *, duration_consumed: bool = False) -> str:
    if not timeline:
        return ''
    onset_char = [
        t for t in timeline
        if t.lower().startswith('of ') and t.lower().endswith('onset')
    ]
    duration_tokens = [t for t in timeline if t not in onset_char]
    # If opening already wove duration in, skip repeating it.
    if duration_consumed:
        duration_tokens = [t for t in duration_tokens if not _duration_for_prose(t)]
        if not duration_tokens and not onset_char:
            return ''
        if not duration_tokens and onset_char:
            onset_word = onset_char[0][len('of '):-len(' onset')]
            return f"The illness was {onset_word} in onset."

    if onset_char and duration_tokens:
        dur_sentence = _progression_sentence(duration_tokens)
        onset_word = onset_char[0][len('of '):-len(' onset')]
        if dur_sentence:
            return f"{dur_sentence[:-1]}, {onset_word} in onset."
        return f"The illness was {onset_word} in onset."
    if onset_char and not duration_tokens:
        onset_word = onset_char[0][len('of '):-len(' onset')]
        return f"The illness was {onset_word} in onset."

    # Prefer a single normalised duration when that is all we have.
    if len(duration_tokens) == 1:
        dur = _duration_for_prose(duration_tokens[0])
        if dur:
            options = [
                f"Symptoms had been present for {dur}.",
                f"The illness had been present for {dur}.",
                f"This had been evolving over {dur}.",
            ]
            return _pick('prog|' + dur, options)

    merged = _oxford_join(timeline if not duration_consumed else duration_tokens)
    merged_l = merged.lower()
    if merged_l.startswith('present for '):
        dur = merged[len('present for '):].strip().lower()
        options = [
            f"Symptoms had been present for {dur}.",
            f"The illness had been evolving over {dur}.",
            f"Symptoms progressed over {dur}.",
        ]
        return _pick('prog|' + dur, options)

    # Bare / Title-case units: Months, Years, "3 weeks", etc.
    bare = _duration_for_prose(merged)
    if bare or re.match(r'^\d', merged) or merged_l.endswith(_DURATION_UNIT_SUFFIXES):
        unit = bare or merged.lower()
        options = [
            f"Symptoms had been present for {unit}.",
            f"The illness had been present for {unit}.",
        ]
        return _pick('prog|' + unit, options)

    # Last resort — still avoid "Symptoms had been Months".
    options = [
        f"The course was notable for {merged_l}.",
        f"The timeline included {merged_l}.",
    ]
    return _pick('prog|' + merged_l, options)


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


def render_hpi_paragraph(doc: SemanticDocument, *, sub_symptom: bool = False) -> str:
    """
    Clinical order:
    1. Primary complaint (+ tightly linked associated symptoms in opening)
    2. Progression / timeline
    3. Remaining associated symptoms & pain (not alarm)
    4. Pertinent negatives (also in separate section)
    5. Risk factors
    6. Alarm features (never mixed with ordinary symptoms)

    ``sub_symptom=True`` is used when this paragraph is one of several
    symptom-specific paragraphs stitched together for a multi-complaint
    encounter — it swaps the usual "The patient presented with..." opener
    for a lighter "Regarding the X, ..." connective so the combined note
    doesn't repeat the same opening phrase for every symptom.
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

    timeline = list(g.get(GROUP_TIMELINE, []))
    # Weave a single clear duration into the opening when possible so we
    # avoid the robotic "…dysphagia. Symptoms had been Months." pattern.
    opening_duration = None
    for token in timeline:
        opening_duration = _duration_for_prose(token)
        if opening_duration:
            break

    parts = [_opening_sentence(
        cc, opening_assoc, sub_symptom=sub_symptom, duration=opening_duration,
    )]

    prog = _progression_sentence(timeline, duration_consumed=bool(opening_duration))
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

    text = _paragraph(*parts)
    # Fix dangling connective when sub-symptom had no duration/associated.
    text = re.sub(r',\s*$', '.', text.strip())
    text = re.sub(r'\s+', ' ', text)
    return text



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
