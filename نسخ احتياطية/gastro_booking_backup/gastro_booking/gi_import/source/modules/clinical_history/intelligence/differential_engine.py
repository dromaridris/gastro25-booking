"""Differential diagnosis engine — priors + answer-driven weights, continuously updated."""

from __future__ import annotations

from app.modules.clinical_history.intelligence.catalog_provider import get_catalog_provider

CONSIDERATION_STRONG = "strong_consideration"
CONSIDERATION_MODERATE = "consider"
CONSIDERATION_LOW = "less_likely"


def _normalize(value: str) -> str:
    return (value or "").strip().lower()


def compute_differential(
    complaint_code: str,
    session_id: int,
    answer_map: dict[str, str] | None = None,
) -> dict[str, float]:
    """
    Internal ranked weights — NOT shown as percentages to clinicians.
    Starts from complaint-specific priors, then applies answer weight rules.
    """
    provider = get_catalog_provider()

    weights: dict[str, float] = {}
    for prior in provider.differential_priors(complaint_code):
        weights[prior.diagnosis_code] = prior.prior_weight

    # Ensure all diagnoses referenced in weight rules exist in map
    for rule in provider.weight_rules_for_complaint(complaint_code):
        weights.setdefault(rule.diagnosis_code, 0.0)

    if answer_map is None:
        from app.modules.clinical_history.intelligence.branching_engine import answer_map as build_map

        answer_map = build_map(session_id)

    for rule in provider.weight_rules_for_complaint(complaint_code):
        ans = answer_map.get(rule.question_code)
        if ans is None:
            continue
        if _normalize(rule.answer_match) == ans:
            weights[rule.diagnosis_code] = weights.get(rule.diagnosis_code, 0.0) + rule.weight_delta

    return weights


def _weight_to_consideration(weight: float, max_weight: float) -> str:
    if weight <= 0:
        return CONSIDERATION_LOW
    if max_weight <= 0:
        return CONSIDERATION_LOW
    ratio = weight / max_weight
    if ratio >= 0.75:
        return CONSIDERATION_STRONG
    if ratio >= 0.4:
        return CONSIDERATION_MODERATE
    return CONSIDERATION_LOW


def differential_for_display(complaint_code: str, session_id: int) -> list[dict]:
    raw = compute_differential(complaint_code, session_id)
    if not raw:
        return []

    max_w = max(raw.values()) if raw else 0
    provider = get_catalog_provider()

    items = []
    for code, weight in sorted(raw.items(), key=lambda x: x[1], reverse=True):
        if weight <= 0 and max_w > 0:
            continue
        dx = provider.diagnosis(code)
        items.append({
            "diagnosis_code": code,
            "name": dx.name if dx else code,
            "consideration_level": _weight_to_consideration(weight, max_w),
            "internal_weight": round(weight, 2),
        })
    return items[:12]


def top_diagnoses(complaint_code: str, session_id: int, limit: int = 5) -> list[str]:
    raw = compute_differential(complaint_code, session_id)
    ranked = sorted(((k, v) for k, v in raw.items() if v > 0), key=lambda x: x[1], reverse=True)
    return [code for code, _ in ranked[:limit]]
