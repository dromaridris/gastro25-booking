"""Modular clinical score registry — disease-based, extensible calculators."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class ScoreResult:
    code: str
    name: str
    group: str
    available: bool
    value: float | int | str | None = None
    interpretation: str = ''
    missing: list[str] = field(default_factory=list)
    inputs: dict[str, Any] = field(default_factory=dict)
    auto: bool = True


def _num(val: Any) -> float | None:
    if val is None or val == '':
        return None
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).strip().replace(',', '')
    m = re.search(r'[-+]?\d*\.?\d+', s)
    if not m:
        return None
    try:
        return float(m.group())
    except ValueError:
        return None


def _ln_floor(v: float, floor: float = 1.0) -> float:
    return math.log(max(v, floor))


def _band_points(value: float, bands: list[tuple[float | None, float | None, int]]) -> int | None:
    for lo, hi, pts in bands:
        if lo is not None and value < lo:
            continue
        if hi is not None and value > hi:
            continue
        return pts
    return None


def _ctx_get(ctx: dict[str, Any], key: str) -> Any:
    if key in ctx:
        return ctx[key]
    lab = ctx.get('labs') or {}
    if key in lab:
        return lab[key]
    short = key.split('.')[-1] if '.' in key else key
    return lab.get(short) or lab.get(f'lab.{short}')


# --- Liver scores ---

def calc_meld(ctx: dict) -> ScoreResult:
    bili = _num(_ctx_get(ctx, 'total_bilirubin'))
    inr = _num(_ctx_get(ctx, 'inr'))
    creat = _num(_ctx_get(ctx, 'creatinine'))
    missing = [k for k, v in [('total_bilirubin', bili), ('inr', inr), ('creatinine', creat)] if v is None]
    if missing:
        return ScoreResult('meld', 'MELD', 'liver', False, missing=missing)
    bili_mg = bili / 17.1 if bili > 5 else bili
    creat_mg = creat / 88.4 if creat > 20 else creat
    score = 3.78 * _ln_floor(bili_mg) + 11.2 * _ln_floor(inr) + 9.57 * _ln_floor(creat_mg) + 6.43
    score = int(round(min(max(score, 6), 40)))
    if score <= 9:
        interp = 'Low 3-month mortality (~1–2%)'
    elif score <= 19:
        interp = 'Moderate 3-month mortality (~6%)'
    elif score <= 29:
        interp = 'High 3-month mortality (~20%)'
    else:
        interp = 'Very high 3-month mortality (>30%)'
    return ScoreResult('meld', 'MELD', 'liver', True, score, interp,
                       inputs={'bilirubin': bili, 'inr': inr, 'creatinine': creat})


def calc_meld_na(ctx: dict) -> ScoreResult:
    base = calc_meld(ctx)
    if not base.available:
        return ScoreResult('meld_na', 'MELD-Na', 'liver', False, missing=base.missing)
    na = _num(_ctx_get(ctx, 'sodium'))
    if na is None:
        return ScoreResult('meld_na', 'MELD-Na', 'liver', False, missing=['sodium'])
    meld = float(base.value)
    if na >= 137:
        meld_na = meld
    elif na <= 125:
        meld_na = meld + 15
    else:
        meld_na = meld + 15 - (137 - na) * 0.8
    meld_na = int(round(min(max(meld_na, 6), 40)))
    return ScoreResult('meld_na', 'MELD-Na', 'liver', True, meld_na,
                       f'MELD-Na {meld_na} (adjusted for sodium {na})',
                       inputs={'meld': meld, 'sodium': na})


def calc_child_pugh(ctx: dict) -> ScoreResult:
    bili = _num(_ctx_get(ctx, 'total_bilirubin'))
    alb = _num(_ctx_get(ctx, 'albumin'))
    inr = _num(_ctx_get(ctx, 'inr'))
    ascites = str(_ctx_get(ctx, 'ascites') or ctx.get('answers', {}).get('ascites', 'none')).lower()
    enceph = str(_ctx_get(ctx, 'encephalopathy') or ctx.get('answers', {}).get('encephalopathy', 'none')).lower()
    missing = []
    if bili is None:
        missing.append('total_bilirubin')
    if alb is None:
        missing.append('albumin')
    if inr is None:
        missing.append('inr')
    if missing:
        return ScoreResult('child_pugh', 'Child-Pugh', 'liver', False, missing=missing)
    bili_mg = bili / 17.1 if bili > 5 else bili
    alb_gdl = alb / 10 if alb > 10 else alb
    pts = 0
    pts += _band_points(bili_mg, [(None, 2, 1), (2, 3, 2), (3, None, 3)]) or 0
    pts += _band_points(alb_gdl, [(3.5, None, 1), (2.8, 3.5, 2), (None, 2.8, 3)]) or 0
    pts += _band_points(inr, [(None, 1.7, 1), (1.7, 2.3, 2), (2.3, None, 3)]) or 0
    if 'moderate' in ascites or 'severe' in ascites:
        pts += 3
    elif 'mild' in ascites or ascites == 'yes':
        pts += 2
    else:
        pts += 1
    if 'grade 3' in enceph or 'grade 4' in enceph or 'severe' in enceph:
        pts += 3
    elif 'grade 1' in enceph or 'grade 2' in enceph or 'mild' in enceph:
        pts += 2
    else:
        pts += 1
    cls = 'A' if pts <= 6 else ('B' if pts <= 9 else 'C')
    return ScoreResult('child_pugh', 'Child-Pugh', 'liver', True, pts,
                       f'Class {cls} ({pts} points)', inputs={'bilirubin': bili, 'albumin': alb, 'inr': inr})


def calc_albi(ctx: dict) -> ScoreResult:
    bili = _num(_ctx_get(ctx, 'total_bilirubin'))
    alb = _num(_ctx_get(ctx, 'albumin'))
    if bili is None or alb is None:
        return ScoreResult('albi', 'ALBI', 'liver', False, missing=[k for k, v in [('total_bilirubin', bili), ('albumin', alb)] if v is None])
    bili_mg = max(bili / 17.1 if bili > 5 else bili, 0.1)
    alb_gdl = alb / 10 if alb > 10 else alb
    score = math.log10(bili_mg) * 0.66 + alb_gdl * -0.085
    grade = '1' if score <= -2.60 else ('2' if score <= -1.39 else '3')
    return ScoreResult('albi', 'ALBI', 'liver', True, round(score, 2),
                       f'ALBI grade {grade}', inputs={'bilirubin': bili, 'albumin': alb})


def calc_apri(ctx: dict) -> ScoreResult:
    ast = _num(_ctx_get(ctx, 'ast'))
    plt = _num(_ctx_get(ctx, 'platelets'))
    if ast is None or plt is None:
        return ScoreResult('apri', 'APRI', 'liver', False, missing=[k for k, v in [('ast', ast), ('platelets', plt)] if v is None])
    score = ((ast / 40) / plt) * 100
    interp = 'Significant fibrosis likely' if score > 1.5 else ('Advanced fibrosis unlikely' if score < 0.5 else 'Indeterminate')
    return ScoreResult('apri', 'APRI', 'liver', True, round(score, 2), interp)


def calc_fib4(ctx: dict) -> ScoreResult:
    age = _num(ctx.get('age'))
    ast = _num(_ctx_get(ctx, 'ast'))
    alt = _num(_ctx_get(ctx, 'alt'))
    plt = _num(_ctx_get(ctx, 'platelets'))
    missing = [k for k, v in [('age', age), ('ast', ast), ('alt', alt), ('platelets', plt)] if v is None]
    if missing:
        return ScoreResult('fib4', 'FIB-4', 'liver', False, missing=missing)
    score = (age * ast) / (plt * math.sqrt(max(alt, 1)))
    interp = 'Advanced fibrosis likely' if score > 3.25 else ('Advanced fibrosis unlikely' if score < 1.45 else 'Indeterminate')
    return ScoreResult('fib4', 'FIB-4', 'liver', True, round(score, 2), interp)


def calc_maddrey(ctx: dict) -> ScoreResult:
    pt = _num(_ctx_get(ctx, 'pt'))
    bili = _num(_ctx_get(ctx, 'total_bilirubin'))
    if pt is None or bili is None:
        return ScoreResult('maddrey', 'Maddrey DF', 'liver', False, missing=[k for k, v in [('pt', pt), ('total_bilirubin', bili)] if v is None])
    bili_mg = bili / 17.1 if bili > 5 else bili
    control_pt = _num(ctx.get('control_pt')) or 12.0
    score = 4.6 * (pt - control_pt) + bili_mg
    interp = 'Severe alcoholic hepatitis — consider steroids if >32' if score >= 32 else 'Below threshold for steroid benefit'
    return ScoreResult('maddrey', 'Maddrey DF', 'liver', True, round(score, 1), interp)


# --- GI bleeding ---

def calc_glasgow_blatchford(ctx: dict) -> ScoreResult:
    urea = _num(_ctx_get(ctx, 'urea'))
    hb = _num(_ctx_get(ctx, 'hemoglobin'))
    sbp = _num(ctx.get('sbp') or ctx.get('answers', {}).get('sbp'))
    pulse = _num(ctx.get('pulse') or ctx.get('answers', {}).get('pulse'))
    melena = str(ctx.get('answers', {}).get('melena', '')).lower() == 'yes'
    syncope = str(ctx.get('answers', {}).get('syncope', '')).lower() == 'yes'
    liver = str(ctx.get('answers', {}).get('liver_disease', '')).lower() == 'yes'
    heart = str(ctx.get('answers', {}).get('heart_failure', '')).lower() == 'yes'
    if urea is None or hb is None:
        return ScoreResult('gbs', 'Glasgow-Blatchford', 'gi_bleeding', False, missing=['urea', 'hemoglobin'])
    pts = 0
    if urea >= 25:
        pts += 6
    elif urea >= 10:
        pts += 4
    elif urea >= 8:
        pts += 3
    elif urea >= 6.5:
        pts += 2
    male = str(ctx.get('gender', '')).lower() in ('m', 'male')
    if male:
        if hb < 100:
            pts += 6
        elif hb < 120:
            pts += 3
        elif hb < 130:
            pts += 1
    else:
        if hb < 100:
            pts += 6
        elif hb < 120:
            pts += 1
    if sbp and sbp < 90:
        pts += 2
    elif sbp and sbp < 100:
        pts += 1
    elif pulse and pulse >= 100:
        pts += 1
    if melena:
        pts += 1
    if syncope:
        pts += 2
    if liver:
        pts += 2
    if heart:
        pts += 2
    interp = 'Low risk — outpatient management may be appropriate' if pts == 0 else (
        'High risk — admission and intervention likely needed' if pts >= 12 else 'Intermediate risk'
    )
    return ScoreResult('gbs', 'Glasgow-Blatchford', 'gi_bleeding', True, pts, interp)


def calc_rockall_pre(ctx: dict) -> ScoreResult:
    age = _num(ctx.get('age'))
    sbp = _num(ctx.get('sbp'))
    pulse = _num(ctx.get('pulse'))
    comorb = str(ctx.get('answers', {}).get('comorbidity', 'none')).lower()
    if age is None:
        return ScoreResult('rockall_pre', 'Rockall (pre-endoscopy)', 'gi_bleeding', False, missing=['age'])
    pts = 0
    if age > 60:
        pts += 1
    if age > 79:
        pts += 1
    if sbp and sbp < 100:
        pts += 2
    elif pulse and pulse >= 100:
        pts += 1
    if 'heart' in comorb or 'renal' in comorb or 'liver' in comorb:
        pts += 2
    elif comorb not in ('none', ''):
        pts += 1
    return ScoreResult('rockall_pre', 'Rockall (pre-endoscopy)', 'gi_bleeding', True, pts,
                       'Low' if pts <= 2 else ('Intermediate' if pts <= 4 else 'High risk'))


def calc_aims65(ctx: dict) -> ScoreResult:
    alb = _num(_ctx_get(ctx, 'albumin'))
    inr = _num(_ctx_get(ctx, 'inr'))
    mental = str(ctx.get('answers', {}).get('altered_mental_status', '')).lower() == 'yes'
    sbp = _num(ctx.get('sbp'))
    age = _num(ctx.get('age'))
    pts = 0
    if alb is not None and alb < 30:
        pts += 1
    if inr is not None and inr > 1.5:
        pts += 1
    if mental:
        pts += 1
    if sbp is not None and sbp <= 90:
        pts += 1
    if age is not None and age >= 65:
        pts += 1
    if alb is None and inr is None and age is None:
        return ScoreResult('aims65', 'AIMS65', 'gi_bleeding', False, missing=['albumin or inr or age'])
    return ScoreResult('aims65', 'AIMS65', 'gi_bleeding', True, pts,
                       'High in-hospital mortality' if pts >= 2 else 'Lower mortality risk')


# --- Pancreatitis ---

def calc_bisap(ctx: dict) -> ScoreResult:
    bun = _num(_ctx_get(ctx, 'urea'))
    gcs = _num(ctx.get('gcs') or ctx.get('answers', {}).get('gcs'))
    sbp = _num(ctx.get('sbp'))
    age = _num(ctx.get('age'))
    pleural = str(ctx.get('answers', {}).get('pleural_effusion', '')).lower() == 'yes'
    pts = 0
    if bun is not None and bun > 8.9:
        pts += 1
    if gcs is not None and gcs < 15:
        pts += 1
    if sbp is not None and sbp < 90:
        pts += 1
    if age is not None and age > 60:
        pts += 1
    if pleural:
        pts += 1
    if bun is None and age is None:
        return ScoreResult('bisap', 'BISAP', 'pancreatitis', False, missing=['urea or age'])
    return ScoreResult('bisap', 'BISAP', 'pancreatitis', True, pts,
                       'Severe pancreatitis likely' if pts >= 3 else 'Lower severity')


# --- General ---

def calc_qsofa(ctx: dict) -> ScoreResult:
    sbp = _num(ctx.get('sbp'))
    rr = _num(ctx.get('respiratory_rate') or ctx.get('answers', {}).get('respiratory_rate'))
    gcs = _num(ctx.get('gcs') or ctx.get('answers', {}).get('gcs'))
    pts = 0
    if sbp is not None and sbp <= 100:
        pts += 1
    if rr is not None and rr >= 22:
        pts += 1
    if gcs is not None and gcs < 15:
        pts += 1
    if sbp is None and rr is None and gcs is None:
        return ScoreResult('qsofa', 'qSOFA', 'general', False, missing=['sbp, rr, or gcs'])
    return ScoreResult('qsofa', 'qSOFA', 'general', True, pts,
                       'High risk of poor outcome' if pts >= 2 else 'qSOFA < 2')


SCORE_GROUPS: dict[str, str] = {
    'liver': 'Liver & Hepatology',
    'gi_bleeding': 'GI Bleeding',
    'pancreatitis': 'Pancreatitis',
    'ibd': 'Inflammatory Bowel Disease',
    'nutrition': 'Nutrition',
    'general': 'General / Critical Care',
}

# Each entry: calculator, groups, trigger keywords/diagnoses/complaints/lab dependencies
ScoreCalc = Callable[[dict], ScoreResult]

SCORE_REGISTRY: list[dict[str, Any]] = [
    {'code': 'meld', 'group': 'liver', 'calc': calc_meld,
     'labs': {'total_bilirubin', 'inr', 'creatinine'},
     'diagnoses': {'cirrhosis', 'liver_failure', 'ascites', 'jaundice'},
     'complaints': {'jaundice', 'ascites', 'hepatitis', 'cirrhosis'}},
    {'code': 'meld_na', 'group': 'liver', 'calc': calc_meld_na,
     'labs': {'total_bilirubin', 'inr', 'creatinine', 'sodium'},
     'diagnoses': {'cirrhosis', 'liver_failure'}, 'complaints': {'jaundice', 'ascites', 'cirrhosis'}},
    {'code': 'child_pugh', 'group': 'liver', 'calc': calc_child_pugh,
     'labs': {'total_bilirubin', 'albumin', 'inr'},
     'diagnoses': {'cirrhosis', 'liver_failure'}, 'complaints': {'ascites', 'cirrhosis', 'jaundice'}},
    {'code': 'albi', 'group': 'liver', 'calc': calc_albi,
     'labs': {'total_bilirubin', 'albumin'},
     'diagnoses': {'hcc', 'cirrhosis', 'liver_failure'}, 'complaints': {'jaundice', 'cirrhosis'}},
    {'code': 'apri', 'group': 'liver', 'calc': calc_apri,
     'labs': {'ast', 'platelets'}, 'complaints': {'hepatitis', 'jaundice'}},
    {'code': 'fib4', 'group': 'liver', 'calc': calc_fib4,
     'labs': {'ast', 'alt', 'platelets'}, 'complaints': {'hepatitis', 'jaundice'}},
    {'code': 'maddrey', 'group': 'liver', 'calc': calc_maddrey,
     'labs': {'pt', 'total_bilirubin'}, 'diagnoses': {'alcoholic_hepatitis'}, 'complaints': {'jaundice'}},
    {'code': 'gbs', 'group': 'gi_bleeding', 'calc': calc_glasgow_blatchford,
     'labs': {'urea', 'hemoglobin'},
     'complaints': {'upper_gi_bleed', 'melena', 'hematemesis', 'gi_bleed'}},
    {'code': 'rockall_pre', 'group': 'gi_bleeding', 'calc': calc_rockall_pre,
     'complaints': {'upper_gi_bleed', 'melena', 'hematemesis', 'gi_bleed'}},
    {'code': 'aims65', 'group': 'gi_bleeding', 'calc': calc_aims65,
     'labs': {'albumin', 'inr'},
     'complaints': {'upper_gi_bleed', 'gi_bleed', 'lower_gi_bleed'}},
    {'code': 'bisap', 'group': 'pancreatitis', 'calc': calc_bisap,
     'labs': {'urea'},
     'diagnoses': {'acute_pancreatitis'}, 'complaints': {'pancreatitis', 'abdominal_pain'}},
    {'code': 'qsofa', 'group': 'general', 'calc': calc_qsofa, 'complaints': {'sepsis', 'abdominal_pain'}},
]

SCORE_BY_CODE: dict[str, dict] = {s['code']: s for s in SCORE_REGISTRY}


def all_calculators() -> list[ScoreCalc]:
    return [s['calc'] for s in SCORE_REGISTRY]
