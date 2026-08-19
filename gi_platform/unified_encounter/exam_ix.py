"""Examination and investigation checklists for the unified encounter."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from gi_platform.unified_encounter.seeds import DEFAULT_EXAM_SYSTEMS

_CK_ROOT = Path(__file__).resolve().parents[2] / 'clinical_knowledge'

# Template sections are merged into a small set of clinical groups so the same
# sign is never offered twice under different headings.
_SYSTEM_ALIASES = {
    'general': 'general',
    'general_jaundice': 'general',
    'hydration': 'general',
    'nutrition': 'general',
    'hemodynamic': 'general',
    'haemodynamic': 'general',
    'lymph_and_skin': 'general',
    'lymph_thyroid': 'general',
    'nodes_and_other': 'general',
    'abdomen': 'abdomen',
    'abdominal': 'abdomen',
    'abdomen_inspection': 'abdomen',
    'abdomen_palpation': 'abdomen',
    'abdomen_percussion': 'abdomen',
    'abdomen_percussion_fluid': 'abdomen',
    'abdomen_auscultation': 'abdomen',
    'cardiorespiratory': 'cardiorespiratory',
    'cardiovascular': 'cardiorespiratory',
    'respiratory': 'cardiorespiratory',
    'chest': 'cardiorespiratory',
    'chest_wall': 'cardiorespiratory',
    'chest_if_needed': 'cardiorespiratory',
    'neuro': 'neuro',
    'neurological': 'neuro',
    'extremities_neuro': 'neuro',
    'rectal': 'rectal',
    'perianal': 'rectal',
}

# Different wordings of the same clinical concept — first one wins, the rest
# are dropped from the checklist entirely.
_CONCEPT_SYNONYMS = {
    'distress': 'distress',
    'general distress': 'distress',
    'distress / toxic appearance': 'distress',
    'general distress / toxic appearance': 'distress',
    'looks well / comfortable': 'wellbeing',
    'vital signs': 'vital_signs',
    'vital signs (hr, bp, rr, spo2, temperature)': 'vital_signs',
    'pulse rate, rhythm, character': 'vital_signs',
    'blood pressure (both arms if dissection suspected)': 'vital_signs',
    'spo2 on room air': 'vital_signs',
    'fever / hypothermia': 'fever',
    'fever': 'fever',
    'fever (measured)': 'fever',
    'tachycardia': 'tachycardia',
    'tachypnea': 'tachypnea',
    'hypotension / shock': 'hypotension',
    'hypotension': 'hypotension',
    'postural pulse/bp change': 'postural_change',
    'postural vitals': 'postural_change',
    'postural blood pressure': 'postural_change',
    'capillary refill': 'capillary_refill',
    'level of consciousness': 'alert_oriented',
    'mental status / gcs': 'alert_oriented',
    'pallor': 'pallor',
    'pallor / colour': 'pallor',
    'hydration': 'hydration',
    'hydration status': 'hydration',
    'hydration / mucous membranes': 'hydration',
    'skin turgor': 'hydration',
    'skin turgor / mucous membranes': 'hydration',
    'dehydration': 'hydration',
    'jaundice / icterus': 'jaundice',
    'jaundice': 'jaundice',
    'jaundice (observed)': 'jaundice',
    'skin/mucosal jaundice': 'jaundice',
    'jaundice / pallor': 'jaundice',
    'scleral icterus': 'jaundice',
    'icteric sclera': 'jaundice',
    'lymphadenopathy': 'lymphadenopathy',
    'lymphadenopathy (cervical, axillary, inguinal)': 'lymphadenopathy',
    'cervical lymphadenopathy': 'lymphadenopathy',
    'cervical / axillary / inguinal nodes': 'lymphadenopathy',
    'cervical / supraclavicular / axillary / inguinal nodes': 'lymphadenopathy',
    'neck mass': 'neck_mass',
    'thyroid / neck mass': 'neck_mass',
    'thyroid examination': 'neck_mass',
    'soft, non-tender': 'abdo_soft',
    'tenderness — localized': 'abdo_tenderness_local',
    'localized tenderness': 'abdo_tenderness_local',
    'tenderness by quadrant': 'abdo_tenderness_local',
    'light then deep palpation by quadrant': 'abdo_tenderness_local',
    'epigastric tenderness': 'abdo_tenderness_local',
    'epigastric tenderness (reflux/pud-type pain)': 'abdo_tenderness_local',
    'tenderness — generalized': 'abdo_tenderness_general',
    'tenderness / peritonism': 'abdo_tenderness_general',
    'peritonism': 'abdo_tenderness_general',
    'peritoneal signs': 'abdo_tenderness_general',
    'guarding / rigidity': 'abdo_guarding',
    'guarding / rigidity / rebound': 'abdo_guarding',
    'tenderness / guarding': 'abdo_guarding',
    'abdominal guarding': 'abdo_guarding',
    'guarding': 'abdo_guarding',
    'rigidity': 'abdo_guarding',
    'abdominal rigidity': 'abdo_guarding',
    'rebound tenderness': 'abdo_rebound',
    'distension / ascites': 'ascites',
    'distension': 'ascites',
    'contour / distension': 'ascites',
    'contour / symmetry of distention': 'ascites',
    'distension / shifting dullness': 'ascites',
    'ascites': 'ascites',
    'ascites / shifting dullness': 'ascites',
    'shifting dullness if ascites suspected': 'ascites',
    'shifting dullness / fluid wave if ascites suspected': 'ascites',
    'flank fullness': 'ascites',
    'organomegaly (liver / spleen)': 'organomegaly',
    'organomegaly': 'organomegaly',
    'organomegaly / masses': 'organomegaly',
    'hepatomegaly': 'organomegaly',
    'splenomegaly': 'organomegaly',
    'splenomegaly (portal hypertension)': 'organomegaly',
    'hepatosplenomegaly': 'organomegaly',
    'liver span': 'organomegaly',
    'liver / spleen span': 'organomegaly',
    'liver span / edge / consistency': 'organomegaly',
    'mass palpable': 'abdo_mass',
    'masses': 'abdo_mass',
    'masses (alarm feature)': 'abdo_mass',
    'abdominal mass': 'abdo_mass',
    'palpable abdominal mass': 'abdo_mass',
    'epigastric mass / tenderness': 'abdo_mass',
    'dull mass vs resonant gas': 'abdo_mass',
    'palpable faecal loading': 'faecal_loading',
    'bowel sounds absent / tinkling': 'bowel_sounds',
    'bowel sounds': 'bowel_sounds',
    'bowel sounds (present / absent / hyperactive)': 'bowel_sounds',
    'bowel sounds (tinkling vs absent)': 'bowel_sounds',
    'hernial orifices abnormal': 'hernia',
    'hernial orifices': 'hernia',
    'hernias': 'hernia',
    'hernia': 'hernia',
    'visible peristalsis': 'visible_peristalsis',
    'visible peristalsis (obstruction)': 'visible_peristalsis',
    'scars / stomas': 'scars',
    'surgical scars': 'scars',
    'tympany vs dullness': 'percussion_note',
    'percussion note': 'percussion_note',
    'murphy sign': 'murphy',
    'murphy sign if ruq pain': 'murphy',
    'palpable gallbladder (courvoisier)': 'courvoisier',
    'bruits if indicated': 'bruits',
    'stigmata of chronic liver disease if relevant': 'clcd_stigmata',
    'caput medusae': 'clcd_stigmata',
    'spider naevi': 'clcd_stigmata',
    'palmar erythema': 'clcd_stigmata',
    'heart sounds normal': 'heart_sounds',
    'heart sounds / murmurs': 'heart_sounds',
    'heart sounds / murmurs / rubs': 'heart_sounds',
    'heart sounds / new murmur (endocarditis screen)': 'heart_sounds',
    'murmur': 'murmur',
    'cardiac murmur': 'murmur',
    'crackles / reduced air entry': 'crackles',
    'crackles': 'crackles',
    'reduced air entry': 'crackles',
    'respiratory distress / crackles / focal findings': 'crackles',
    'breath sounds': 'breath_sounds',
    'breath sounds / added sounds': 'breath_sounds',
    'wheeze': 'wheeze',
    'peripheral oedema': 'peripheral_oedema',
    'peripheral oedema (cardiac vs hepatic cause)': 'peripheral_oedema',
    'peripheral edema': 'peripheral_oedema',
    'pitting oedema': 'peripheral_oedema',
    'jvp': 'jvp',
    'raised jvp': 'jvp',
    'peripheral pulses': 'peripheral_pulses',
    'chest wall movement / symmetry': 'chest_wall_movement',
    'work of breathing / accessory muscle use': 'work_of_breathing',
    'respiratory distress / crackles / focal findings when hemoptysis possible': 'crackles',
    'reproducible chest wall tenderness': 'chest_wall_tenderness',
    'chest wall tenderness (differential)': 'chest_wall_tenderness',
    'signs of pneumothorax or effusion': 'pneumothorax_effusion',
    'aspiration signs (chest exam)': 'aspiration_signs',
    'alert / oriented': 'alert_oriented',
    'confusion / encephalopathy signs': 'encephalopathy',
    'asterixis': 'asterixis',
    'asterixis / mental status if liver disease suspected': 'asterixis',
    'focal deficit': 'focal_deficit',
    'cranial nerve screen relevant to swallowing (ix, x, xii)': 'cranial_nerves',
    'not performed': 'pr_not_performed',
    'pr exam when indicated (document separately if performed)': 'pr_not_performed',
    'digital rectal exam when indicated': 'pr_not_performed',
    'digital rectal exam if indicated': 'pr_not_performed',
    'digital rectal exam — tone, mass, impacted stool': 'pr_not_performed',
    'normal pr': 'pr_normal',
    'melena on glove': 'stool_on_glove',
    'stool colour': 'stool_on_glove',
    'stool appearance on glove': 'stool_on_glove',
    'stool colour/consistency on glove': 'stool_on_glove',
    'abnormal stool colour': 'stool_on_glove',
    'abnormal stool colour on dre': 'stool_on_glove',
    'fresh blood': 'fresh_blood_pr',
    'mass / lesion': 'rectal_mass',
    'rectal mass': 'rectal_mass',
    'rectal mass on dre': 'rectal_mass',
    'perianal source (haemorrhoids/fissure)': 'perianal_source',
    'perianal inspection (fissure/haemorrhoids)': 'perianal_source',
    'perianal inspection (fissure/fistula/skin tags)': 'perianal_source',
    'perianal findings': 'perianal_source',
    'external inspection': 'perianal_source',
    'oral cavity / oropharynx inspection': 'oropharynx',
    'oropharyngeal inspection': 'oropharynx',
    'oropharyngeal lesion': 'oropharynx',
    'oral thrush': 'oral_thrush',
    'dental erosion': 'dental_erosion',
    'rash / petechiae': 'rash',
    'bruising / petechiae': 'rash',
    'excoriations (pruritus)': 'excoriations',
    'skin/hair changes': 'skin_changes',
    'muscle wasting / temporal wasting': 'muscle_wasting',
    'signs of malnutrition / muscle wasting': 'muscle_wasting',
    'bmi if available': 'bmi',
    'costovertebral angle tenderness': 'cva_tenderness',
    'wound / line / catheter sites': 'line_sites',
    'joints for septic arthritis': 'joints',
    'ears/throat/sinuses': 'ent',
}


_QUALIFIER_SUFFIXES = (
    ' if relevant', ' if indicated', ' when indicated', ' if available',
    ' if ruq pain', ' when hemoptysis possible', ' if liver disease suspected',
    ' if ascites suspected', ' if dissection suspected',
)


def _strip_qualifiers(text: str) -> str:
    """Drop trailing conditional wording that does not change the concept."""
    clean = ' '.join(str(text or '').strip().rstrip('.').split())
    lowered = clean.lower()
    for suffix in _QUALIFIER_SUFFIXES:
        if lowered.endswith(suffix):
            return clean[: len(clean) - len(suffix)].rstrip(' ,;')
    return clean


def _concept_key(label: str) -> str:
    """Canonical concept id for a checklist label, so synonyms collapse to one."""
    norm = ' '.join(str(label or '').strip().lower().split())
    if norm in _CONCEPT_SYNONYMS:
        return _CONCEPT_SYNONYMS[norm]
    trimmed = _strip_qualifiers(norm).lower()
    return _CONCEPT_SYNONYMS.get(trimmed, trimmed or norm)


def _sign_labels() -> dict[str, str]:
    """Human labels for SG_* codes from the clinical knowledge dictionary."""
    cached = getattr(_sign_labels, '_cache', None)
    if cached is not None:
        return cached
    labels: dict[str, str] = {}
    try:
        data = json.loads((_CK_ROOT / 'dictionary' / 'signs.json').read_text(encoding='utf-8'))
        for entry in data if isinstance(data, list) else []:
            code = entry.get('code')
            label = entry.get('label')
            if code and label:
                labels[code] = label
    except Exception:
        labels = {}
    _sign_labels._cache = labels
    return labels


def _load_exam_template_for_complaint(complaint_code: str) -> list[dict] | None:
    """Map hist.* / CC_* to clinical_knowledge exam templates when present."""
    slug = (complaint_code or '').replace('hist.', '').replace('CC_', '').replace('cp.', '')
    slug = slug.replace('distension', 'distention')
    aliases = {
        'loose_stools': 'diarrhea',
        'upper_gi_bleeding': 'hematemesis',
        'lower_gi_bleeding': 'hematochezia',
        'ascites': 'abdominal_distention',
        'abdominal_distension': 'abdominal_distention',
    }
    slug = aliases.get(slug, slug)
    path = _CK_ROOT / 'templates' / 'exam' / f'{slug}.json'
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return None
    sign_labels = _sign_labels()
    systems = []
    for sec in data.get('systems') or []:
        items = list(sec.get('checklist') or [])
        # Also surface dictionary finding labels as checkable items
        for fid in sec.get('finding_ids') or []:
            label = sign_labels.get(fid) or fid.replace('SG_', '').replace('_', ' ').capitalize()
            if label not in items:
                items.append(label)
        if items:
            raw_key = sec.get('key') or sec.get('title', 'exam')
            systems.append({
                'key': _SYSTEM_ALIASES.get(raw_key, raw_key),
                'title': sec.get('title') or raw_key,
                'items': items,
            })
    return systems or None


def build_exam_checklist(symptoms: list[dict] | None = None) -> list[dict]:
    """
    Merge default systems with complaint-specific exam templates.

    Template sections collapse into the default clinical groups, and any sign
    already offered elsewhere is dropped so nothing is asked twice.
    """
    by_key: dict[str, dict] = {}
    for s in DEFAULT_EXAM_SYSTEMS:
        by_key[s['key']] = {'key': s['key'], 'title': s['title'], 'items': list(s['items'])}

    # Concepts already offered anywhere in the checklist.
    used_concepts: set[str] = set()
    for group in by_key.values():
        for item in group['items']:
            used_concepts.add(_concept_key(item))

    for sym in symptoms or []:
        for sec in _load_exam_template_for_complaint(sym.get('complaint_code') or '') or []:
            key = sec['key']
            group = by_key.get(key)
            if group is None:
                group = {'key': key, 'title': sec['title'], 'items': []}
                by_key[key] = group
            for item in sec['items']:
                concept = _concept_key(item)
                if concept in used_concepts:
                    continue
                group['items'].append(item)
                used_concepts.add(concept)

    ordered = []
    seen_keys = set()
    for s in DEFAULT_EXAM_SYSTEMS:
        ordered.append(by_key[s['key']])
        seen_keys.add(s['key'])
    for key, group in by_key.items():
        if key not in seen_keys and group['items']:
            ordered.append(group)
    return ordered


def build_investigation_checklist(
    db,
    session_id: int,
    *,
    differential: dict | None = None,
) -> list[dict]:
    """Suggested investigations as checklist rows (not one button per test)."""
    from gi_platform.investigation_catalog import ORDER_TYPES

    suggestions: list[dict] = []
    seen: set[str] = set()

    # Existing CDS suggestions table
    try:
        rows = db.execute(
            "SELECT name, rationale, priority FROM gi_investigation_suggestion WHERE session_id = ? ORDER BY id",
            (session_id,),
        ).fetchall()
        for r in rows:
            name = r['name']
            if name and name.lower() not in seen:
                seen.add(name.lower())
                suggestions.append({
                    'name': name,
                    'rationale': r['rationale'] or '',
                    'priority': r['priority'] or 'routine',
                    'source': 'cds',
                })
    except Exception:
        pass

    for inv in (differential or {}).get('investigations') or []:
        name = inv.get('name') or ''
        if name and name.lower() not in seen:
            seen.add(name.lower())
            suggestions.append({
                'name': name,
                'rationale': inv.get('rationale') or '',
                'priority': inv.get('priority') or 'routine',
                'source': 'differential',
            })

    # Heuristic knowledge priors from active diagnoses (non-GI-hardcoded: keyword → catalogue)
    dx_blob = ' '.join(
        (d.get('name') or '') for d in (differential or {}).get('diagnoses') or []
    ).lower()
    heuristics = [
        (('bleed', 'hematemesis', 'melena', 'ulcer', 'varice'), [
            ('CBC', 'Baseline hemoglobin', 'urgent'),
            ('Coagulation profile', 'Bleeding risk / cirrhosis', 'urgent'),
            ('Urea / electrolytes', 'Resuscitation baseline', 'urgent'),
            ('Upper GI endoscopy', 'Diagnostic and therapeutic', 'urgent'),
        ]),
        (('jaundice', 'biliary', 'cholang'), [
            ('LFTs', 'Cholestatic vs hepatocellular pattern', 'urgent'),
            ('Abdominal ultrasound', 'Biliary obstruction screen', 'urgent'),
            ('INR', 'Liver synthetic function', 'urgent'),
        ]),
        (('pancreatitis',), [
            ('Serum lipase / amylase', 'Confirm pancreatitis', 'urgent'),
            ('CBC + CRP', 'Severity markers', 'urgent'),
        ]),
        (('diarrhea', 'colitis', 'ibd'), [
            ('Stool culture / C. difficile', 'Infectious work-up', 'routine'),
            ('CBC + CRP', 'Inflammatory activity', 'routine'),
        ]),
        (('ascites', 'cirrhosis'), [
            ('Diagnostic paracentesis', 'SBP exclusion', 'urgent'),
            ('Ascitic fluid SAAG / culture', 'Portal vs other ascites', 'urgent'),
        ]),
    ]
    for keys, tests in heuristics:
        if any(k in dx_blob for k in keys):
            for name, rationale, priority in tests:
                if name.lower() not in seen:
                    seen.add(name.lower())
                    suggestions.append({
                        'name': name,
                        'rationale': rationale,
                        'priority': priority,
                        'source': 'knowledge_heuristic',
                    })

    # Always offer a compact catalogue strip for ordering
    catalogue = []
    for order_type, label, items in ORDER_TYPES:
        for code, name in items[:8]:
            catalogue.append({'order_type': order_type, 'code': code, 'name': name, 'group': label})

    return {
        'suggested': suggestions,
        'catalogue': catalogue,
    }


_NORMAL_EXAM_PROSE = {
    'general': 'The patient appeared well and comfortable, with no abnormal general signs identified.',
    'abdomen': (
        'The abdomen was soft and non-tender, with no guarding, palpable mass, '
        'organomegaly or clinically evident ascites.'
    ),
    'abdomen_inspection': 'Inspection of the abdomen was unremarkable.',
    'abdomen_auscultation': 'Bowel sounds were present and normal.',
    'abdomen_percussion': 'Abdominal percussion was unremarkable.',
    'abdomen_palpation': (
        'The abdomen was soft and non-tender on palpation, with no guarding, '
        'rebound tenderness, palpable mass or organomegaly.'
    ),
    'cardiorespiratory': (
        'Heart sounds were normal and the chest was clear to auscultation, '
        'with no peripheral oedema.'
    ),
    'neuro': 'The patient was alert and oriented, with no focal neurological deficit.',
    'rectal': 'Rectal and perianal examination was unremarkable.',
    'hemodynamic': 'The patient was haemodynamically stable, with no postural change.',
    'chest_if_needed': 'Respiratory examination was unremarkable.',
    'nodes_and_other': 'No clinically significant lymphadenopathy was identified.',
}

_PRESENT_EXAM_PROSE = {
    'looks well / comfortable': 'The patient appeared well and comfortable.',
    'distress / toxic appearance': 'The patient appeared distressed and clinically unwell.',
    'general distress / toxic appearance': 'The patient appeared distressed and clinically unwell.',
    'fever / hypothermia': 'An abnormal temperature was documented.',
    'tachycardia': 'Tachycardia was present.',
    'hypotension / shock': 'Hypotension with features of circulatory compromise was present.',
    'hypotension': 'Hypotension was present.',
    'pallor': 'Pallor was noted.',
    'pallor / colour': 'Pallor was noted.',
    'jaundice / icterus': 'Jaundice was present.',
    'icteric sclera': 'Scleral icterus was present.',
    'lymphadenopathy': 'Lymphadenopathy was present.',
    'dehydration': 'Clinical features of dehydration were present.',
    'soft, non-tender': 'The abdomen was soft and non-tender.',
    'tenderness — localized': 'Localized abdominal tenderness was present.',
    'localized tenderness': 'Localized abdominal tenderness was present.',
    'tenderness — generalized': 'Generalized abdominal tenderness was present.',
    'guarding / rigidity': 'Guarding or rigidity was elicited.',
    'guarding / rigidity / rebound': 'Guarding, rigidity or rebound tenderness was elicited.',
    'rebound tenderness': 'Rebound tenderness was present.',
    'distension / ascites': 'Abdominal distension with clinically evident ascites was present.',
    'organomegaly (liver / spleen)': 'Hepatomegaly or splenomegaly was present.',
    'organomegaly / masses': 'Organomegaly or a palpable abdominal mass was present.',
    'mass palpable': 'A palpable abdominal mass was identified.',
    'bowel sounds absent / tinkling': 'Bowel sounds were abnormal (absent or tinkling).',
    'hernial orifices abnormal': 'An abnormality of the hernial orifices was identified.',
    'heart sounds normal': 'Heart sounds were normal.',
    'murmur': 'A cardiac murmur was heard.',
    'crackles / reduced air entry': 'Crackles or reduced air entry were present.',
    'wheeze': 'Wheeze was present.',
    'peripheral oedema': 'Peripheral oedema was present.',
    'alert / oriented': 'The patient was alert and oriented.',
    'confusion / encephalopathy signs': 'Confusion or clinical features of encephalopathy were present.',
    'focal deficit': 'A focal neurological deficit was identified.',
    'asterixis': 'Asterixis was present.',
    'not performed': 'Rectal examination was not performed.',
    'melena on glove': 'Melena was present on the examining glove.',
    'fresh blood': 'Fresh blood was present on rectal examination.',
    'mass / lesion': 'A rectal mass or lesion was identified.',
    'normal pr': 'Rectal examination was normal.',
    'postural pulse/bp change': 'A postural pulse or blood-pressure change was demonstrated.',
    'capillary refill': 'Capillary refill was prolonged.',
    'level of consciousness': 'The level of consciousness was abnormal.',
    'stigmata of chronic liver disease if relevant': 'Stigmata of chronic liver disease were present.',
    'perianal source (haemorrhoids/fissure)': 'A perianal bleeding source was identified.',
    'masses': 'A mass was identified on examination.',
}

_ABSENT_EXAM_PROSE = {
    'distress / toxic appearance': 'The patient was not distressed or toxic in appearance.',
    'general distress / toxic appearance': 'The patient was not distressed or toxic in appearance.',
    'fever / hypothermia': 'The patient was afebrile.',
    'tachycardia': 'There was no tachycardia.',
    'hypotension / shock': 'There was no hypotension or clinical shock.',
    'hypotension': 'There was no hypotension.',
    'pallor': 'There was no pallor.',
    'pallor / colour': 'There was no pallor.',
    'jaundice / icterus': 'There was no jaundice.',
    'lymphadenopathy': 'There was no palpable lymphadenopathy.',
    'dehydration': 'There were no clinical features of dehydration.',
    'tenderness — localized': 'There was no localized abdominal tenderness.',
    'localized tenderness': 'There was no localized abdominal tenderness.',
    'tenderness — generalized': 'There was no generalized abdominal tenderness.',
    'guarding / rigidity': 'There was no guarding or rigidity.',
    'guarding / rigidity / rebound': 'There was no guarding, rigidity or rebound tenderness.',
    'rebound tenderness': 'There was no rebound tenderness.',
    'distension / ascites': 'There was no abdominal distension or clinically evident ascites.',
    'organomegaly (liver / spleen)': 'There was no palpable hepatosplenomegaly.',
    'organomegaly / masses': 'There was no palpable organomegaly or abdominal mass.',
    'mass palpable': 'No abdominal mass was palpable.',
    'hernial orifices abnormal': 'No abnormality of the hernial orifices was identified.',
    'murmur': 'No cardiac murmur was heard.',
    'crackles / reduced air entry': 'There were no crackles or focal reduction in air entry.',
    'wheeze': 'There was no wheeze.',
    'peripheral oedema': 'There was no peripheral oedema.',
    'confusion / encephalopathy signs': 'There was no confusion or clinical encephalopathy.',
    'focal deficit': 'No focal neurological deficit was identified.',
    'asterixis': 'There was no asterixis.',
    'melena on glove': 'There was no melena on the examining glove.',
    'fresh blood': 'There was no fresh blood on rectal examination.',
    'mass / lesion': 'No rectal mass or lesion was identified.',
    'postural pulse/bp change': 'There was no significant postural pulse or blood-pressure change.',
    'capillary refill': 'Capillary refill was not prolonged.',
    'stigmata of chronic liver disease if relevant': 'No stigmata of chronic liver disease were identified.',
    'perianal source (haemorrhoids/fissure)': 'No haemorrhoid or anal fissure was identified.',
    'respiratory distress / crackles / focal findings when hemoptysis possible': (
        'There was no respiratory distress, crackles or focal chest finding.'
    ),
}


def _clean_finding_label(item: str) -> str:
    clean = _strip_qualifiers(item)
    return clean.replace(' — ', ' ').replace(' / ', ' or ')


def _sentence_for_finding(item: str, polarity: str) -> str:
    """Translate one explicit checklist choice into natural clinical prose."""
    key = ' '.join(str(item).strip().lower().split())
    phrases = _PRESENT_EXAM_PROSE if polarity == 'present' else _ABSENT_EXAM_PROSE
    if key in phrases:
        return phrases[key]

    clean = _clean_finding_label(item)
    if polarity == 'present':
        return f'{clean} was noted.'
    return f'No {clean[:1].lower() + clean[1:]} was identified.'


def _system_normal_prose(system_key: str, title: str) -> str:
    if system_key in _NORMAL_EXAM_PROSE:
        return _NORMAL_EXAM_PROSE[system_key]
    if system_key.startswith('abdomen_'):
        return f'{title} was unremarkable.'
    return f'Examination of the {title.lower()} was unremarkable.'


def _ensure_sentence(text: str) -> str:
    text = ' '.join((text or '').strip().split())
    if not text:
        return ''
    return text if text[-1] in '.!?' else text + '.'


def _wrap_body(sentences: list[str], *, indent: str = '  ', width: int = 92) -> str:
    """Indented, soft-wrapped paragraph so each system block reads as a block."""
    text = ' '.join(s.strip() for s in sentences if s and s.strip())
    if not text:
        return ''
    lines: list[str] = []
    current = indent
    for word in text.split():
        candidate = word if current.strip() == '' else f'{current} {word}'
        if len(candidate) > width and current.strip():
            lines.append(current)
            current = f'{indent}{word}'
        else:
            current = candidate if current.strip() else f'{indent}{word}'
    if current.strip():
        lines.append(current)
    return '\n'.join(lines)


def format_exam_text(
    findings: dict[str, dict],
    other: str = '',
    *,
    normal_systems: list[str] | set[str] | None = None,
    system_titles: dict[str, str] | None = None,
) -> str:
    """
    Generate a professional, deterministic examination narrative.

    Only explicitly selected findings are rendered. Marking a whole system as
    normal authorizes a standard normal-system sentence. Systems left untouched
    are simply omitted. No diagnosis or unrecorded finding is introduced.
    """
    normal_set = {str(k) for k in (normal_systems or []) if k}
    titles = dict(system_titles or {})

    ordered_keys: list[str] = []
    seen: set[str] = set()
    for system in DEFAULT_EXAM_SYSTEMS:
        key = system['key']
        ordered_keys.append(key)
        seen.add(key)
        titles.setdefault(key, system['title'])
    for key in list((findings or {}).keys()) + list(normal_set):
        if key and key not in seen:
            ordered_keys.append(key)
            seen.add(key)

    blocks: list[str] = []
    for system_key in ordered_keys:
        title = titles.get(system_key) or system_key.replace('_', ' ').title()
        if system_key in normal_set:
            body = _wrap_body([_system_normal_prose(system_key, title)])
        else:
            items = (findings or {}).get(system_key) or {}
            body = _wrap_body([
                _sentence_for_finding(item, polarity)
                for item, polarity in items.items()
                if polarity in ('present', 'absent') and not str(item).startswith('_')
            ])
        if body:
            blocks.append(f'{title}\n{body}')

    other_sentence = _ensure_sentence(other)
    if other_sentence:
        blocks.append('Additional findings\n' + _wrap_body([other_sentence]))

    return '\n\n'.join(blocks)
