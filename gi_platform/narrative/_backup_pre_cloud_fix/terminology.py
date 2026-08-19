"""Strip internal codes and normalise text for consultant-facing prose."""

from __future__ import annotations

import re

# Patterns that must never appear in final narrative.
_INTERNAL_CODE = re.compile(
    r'\b(hist|dx|q|kl|proc|lab|img|reg|rv)\.[a-z0-9_.]+\b',
    re.I,
)
_UNDERSCORE_CODE = re.compile(r'\b[a-z]+_[a-z0-9_]+\b', re.I)

TERM_MAP: dict[str, str] = {
    'itching': 'generalised pruritus',
    'generalized itching': 'generalised pruritus',
    'generalised itching': 'generalised pruritus',
    'black stools': 'melena',
    'black tarry stools': 'melena',
    'black tarry stool': 'melena',
    'vomiting blood': 'haematemesis',
    'blood in vomit': 'haematemesis',
    'yellow eyes': 'jaundice',
    'yellow skin': 'icterus',
    'yellowing of the eyes': 'jaundice',
    'difficulty swallowing': 'dysphagia',
    'painful swallowing': 'odynophagia',
    'heartburn': 'retrosternal burning',
    'blood in stool': 'rectal bleeding',
    'bright red blood per rectum': 'haematochezia',
    'loose stools': 'loose bowel motions',
    'watery diarrhea': 'watery diarrhoea',
    'watery diarrhoea': 'watery diarrhoea',
    'weight loss': 'unintentional weight loss',
    'loss of appetite': 'anorexia',
    'feeling tired': 'fatigue',
    'bloating': 'abdominal bloating',
    'gas': 'excessive flatus',
}

CHOICE_LABELS: dict[str, str] = {
    'hours': 'a few hours',
    '1-3_days': 'one to three days',
    'more_than_3_days': 'more than three days',
    'small': 'a small volume',
    'moderate': 'a moderate volume',
    'large': 'a large volume',
    'massive': 'a massive volume',
    'never': 'never smoked',
    'former': 'an ex-smoker',
    'current': 'a current smoker',
    '1-3': 'one to three times daily',
    '4-6': 'four to six times daily',
    '7+': 'more than seven times daily',
}

# Phrases treated as alarm features if present affirmatively.
_ALARM_KEYWORDS = re.compile(
    r'\b(weight loss|unintentional weight loss|progressive|deteriorat|'
    r'bleed|hematemesis|haematemesis|melena|haematochezia|'
    r'persistent vomit|confusion|encephalopathy|syncope|shock|'
    r'obstructive|cholangitis|peritonitis)\b',
    re.I,
)


def _lower(s: str) -> str:
    return (s or '').strip().lower()


def clean_internal_codes(text: str) -> str:
    """Remove hist.* / q.* / dx.* and similar from display text."""
    if not text:
        return ''
    t = text.strip()
    # Chief complaint codes: hist.upper_gi_bleeding → upper gi bleeding
    t = re.sub(r'^hist\.', '', t, flags=re.I)
    t = re.sub(r'^dx\.', '', t, flags=re.I)
    t = _INTERNAL_CODE.sub('', t)
    t = _UNDERSCORE_CODE.sub(lambda m: m.group(0).replace('_', ' '), t)
    t = re.sub(r'\s{2,}', ' ', t).strip()
    return t


def clean_chief_complaint(text: str) -> str:
    t = clean_internal_codes(text)
    t = t.replace('_', ' ')
    t = normalize_term(t) or t
    return t.lower().strip() or 'the presenting symptoms'


def normalize_term(text: str) -> str:
    t = (text or '').strip()
    if not t:
        return ''
    for src, dst in sorted(TERM_MAP.items(), key=lambda x: -len(x[0])):
        if dst.lower() in t.lower():
            continue
        pattern = r'\b' + re.escape(src) + r'\b'
        if re.search(pattern, t, re.I):
            t = re.sub(pattern, dst, t, flags=re.I)
    return t.strip()


def normalize_choice(value: str) -> str:
    v = (value or '').strip().lower()
    if v in CHOICE_LABELS:
        return CHOICE_LABELS[v]
    alt = v.replace('-', '_')
    if alt in CHOICE_LABELS:
        return CHOICE_LABELS[alt]
    return v.replace('_', ' ').strip()


def is_alarm_phrase(phrase: str) -> bool:
    return bool(_ALARM_KEYWORDS.search(phrase or ''))


def extract_clinical_phrase(prompt: str, *, prefer_parenthetical: bool = True) -> str:
    text = (prompt or '').strip()
    if prefer_parenthetical:
        m = re.search(r'\(([^)]+)\)', text)
        if m:
            inner = m.group(1).strip()
            if inner and len(inner) < 60:
                inner = clean_internal_codes(inner)
                return normalize_term(inner).lower() or inner.lower()
    text = re.sub(r'^(has|have|did|does|is|are|was|were)\s+(the\s+)?patient\s+', '', text, flags=re.I)
    text = re.sub(r'^(any|history of)\s+', '', text, flags=re.I)
    text = text.rstrip('?').strip()
    text = re.split(r'\s*[\—\-–]\s*', text, maxsplit=1)[0].strip()
    text = re.split(r'\s*\(', text, maxsplit=1)[0].strip()
    text = clean_internal_codes(text)
    result = normalize_term(text) or text
    result = result.lower()
    for ac in ('NSAID', 'NSAIDs', 'HIV', 'HBV', 'HCV', 'IBD', 'IBS', 'PPI', 'INR', 'EGD', 'ERCP'):
        result = re.sub(r'\b' + ac.lower() + r'\b', ac, result, flags=re.I)
    return result


_ONSET_PATTERN_VALUES = {'sudden', 'gradual', 'unclear', 'abrupt', 'insidious'}
_DURATION_VALUES = {'hours', 'days', 'weeks', 'months', 'minutes', 'years'}
_QUESTION_LEAD = re.compile(r'^(when|was|is|does|did|how|what|where|has|have|are|were)\b', re.I)


def phrase_from_fact(prompt: str, value: str, answer_type: str, *, code: str = '') -> str | None:
    v = (value or '').strip()
    if not v:
        return None
    stem = extract_clinical_phrase(prompt)
    code_l = (code or '').lower()
    prompt_l = _lower(prompt)
    v_l = v.lower()

    if answer_type == 'boolean' or v_l in ('yes', 'no', 'true', 'false'):
        if v_l in ('no', 'false'):
            return None
        return stem or normalize_term(v)

    if answer_type == 'choice':
        label = normalize_choice(v)

        # Onset character (sudden/gradual) is semantically distinct from onset
        # *timing* (hours/days/...) even though both prompts often contain
        # the word "onset" — disambiguate on the answer value itself.
        if v_l in _ONSET_PATTERN_VALUES:
            return f"of {label} onset"

        if (
            v_l in _DURATION_VALUES
            or '.duration' in code_l
            or 'duration' in prompt_l
            or 'how long' in prompt_l
            or 'when did' in prompt_l
            or ('onset' in prompt_l and 'onset' in code_l)
        ):
            return f"present for {label}"

        if 'frequency' in prompt_l or '.frequency' in code_l:
            return f"bowel frequency of {label}"

        if 'amount' in prompt_l or 'volume' in prompt_l:
            return f"{label} of bleeding"

        if 'severity' in prompt_l or '.severity' in code_l:
            return f"{label} in severity"

        if any(k in prompt_l for k in ('site', 'location', 'located')) or '.site' in code_l or '.location' in code_l:
            return f"located in the {label}"

        if any(k in prompt_l for k in ('character', 'quality')) or '.character' in code_l or '.quality' in code_l:
            return label

        if 'radiat' in prompt_l or '.radiation' in code_l:
            return f"radiating to {label}"

        # Safe fallback: never glue a raw question stem to "(label)" — that
        # produces literal Q&A text instead of prose. Only combine when the
        # stem is a short, non-interrogative noun phrase; otherwise the
        # label alone reads better than a garbled question fragment.
        if stem and len(stem.split()) <= 4 and not _QUESTION_LEAD.match(stem):
            return f"{stem} ({label})"
        return label

    cleaned = clean_internal_codes(v)
    if 'radiat' in prompt_l or '.radiation' in code_l:
        return f"radiation to {cleaned}"
    if '.duration' in code_l or 'how long' in prompt_l or 'duration' in prompt_l or 'when did' in prompt_l:
        return f"present for {cleaned}"
    return normalize_term(cleaned) if len(cleaned) > 2 else cleaned
