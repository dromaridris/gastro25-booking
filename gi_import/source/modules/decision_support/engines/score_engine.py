"""Clinical score engine — auto-calculate when sufficient variables exist."""

from __future__ import annotations

from typing import Any

from app.modules.decision_support.constants import FORMULA_INTEGER_SUM, FORMULA_POINT_SUM
from app.modules.decision_support.context import AssessmentContext, ScoreResult
from app.modules.decision_support.knowledge_accessor import CdsKnowledgeAccessor
from app.modules.decision_support.variable_resolver import resolve_value


def _apply_bands(raw_value: Any, bands: list[dict]) -> tuple[int | float | None, str | None]:
    if raw_value is None:
        return None, None
    try:
        numeric = float(raw_value)
    except (TypeError, ValueError):
        return None, None

    for band in bands:
        min_v = band.get("min")
        max_v = band.get("max")
        if min_v is not None and numeric < float(min_v):
            continue
        if max_v is not None and numeric > float(max_v):
            continue
        return band.get("points", 0), band.get("label")

    return 0, None


def _calculate_point_sum(definition: dict, context: AssessmentContext) -> tuple[int | None, list[str]]:
    total = 0
    missing: list[str] = []
    for var in definition.get("variables", []):
        key = var.get("variable_code") or var.get("name")
        source_type = var.get("source_type")
        source_key = var.get("source_key")
        val = resolve_value(context, source_type, source_key)
        if val is None:
            missing.append(key or source_key)
            continue
        points, _ = _apply_bands(val, var.get("bands", []))
        if points is None:
            missing.append(key or source_key)
            continue
        total += int(points)
    if missing:
        return None, missing
    return total, []


def _calculate_integer_sum(definition: dict, context: AssessmentContext) -> tuple[int | None, list[str]]:
    total = 0
    missing: list[str] = []
    for var in definition.get("variables", []):
        key = var.get("variable_code") or var.get("name")
        source_type = var.get("source_type")
        source_key = var.get("source_key")
        val = resolve_value(context, source_type, source_key)
        if val is None:
            missing.append(key or source_key)
            continue
        try:
            total += int(float(val))
        except (TypeError, ValueError):
            missing.append(key or source_key)
    if missing:
        return None, missing
    return total, []


def _interpret_score(total: int, interpretations: list[dict]) -> str | None:
    for row in interpretations:
        min_v = row.get("min")
        max_v = row.get("max")
        if min_v is not None and total < int(min_v):
            continue
        if max_v is not None and total > int(max_v):
            continue
        return row.get("label")
    return None


def calculate_scores(
    context: AssessmentContext,
    accessor: CdsKnowledgeAccessor,
) -> list[ScoreResult]:
    results: list[ScoreResult] = []
    for score_obj in accessor.score_definitions():
        attrs = score_obj.attributes
        definition = attrs.get("calculation") or attrs
        formula = definition.get("formula", FORMULA_POINT_SUM)
        score_code = attrs.get("score_code") or score_obj.stable_id

        applicable = attrs.get("complaint_codes")
        if applicable and context.complaint_code not in applicable:
            continue

        total: int | None = None
        missing: list[str] = []
        if formula == FORMULA_POINT_SUM:
            total, missing = _calculate_point_sum(definition, context)
        elif formula == FORMULA_INTEGER_SUM:
            total, missing = _calculate_integer_sum(definition, context)

        if total is None:
            results.append(
                ScoreResult(
                    score_stable_id=score_obj.stable_id,
                    score_code=score_code,
                    name=score_obj.title,
                    available=False,
                    missing_variables=missing,
                )
            )
            continue

        interpretation = _interpret_score(total, definition.get("interpretations", []))
        results.append(
            ScoreResult(
                score_stable_id=score_obj.stable_id,
                score_code=score_code,
                name=score_obj.title,
                available=True,
                value=str(total),
                interpretation=interpretation,
            )
        )
    return results
