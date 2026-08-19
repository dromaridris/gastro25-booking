"""Differential diagnostic update comparison engine."""

from __future__ import annotations

from typing import Any

from app.modules.clinical_interpretation.constants import (
    UPDATE_LESS_LIKELY,
    UPDATE_MORE_LIKELY,
    UPDATE_NEW_CONSIDERATION,
    UPDATE_UNCHANGED,
)


class DiagnosticUpdateEngine:
    """
    Compares previous differential assessment with new clinical information.

    Preserves original differential history via snapshot; outputs suggested updates only.
    Does NOT modify physician diagnosis or confirm any diagnosis automatically.
    """

    def generate(
        self,
        *,
        previous_differential: list[dict[str, Any]],
        interpretation_findings: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        if not previous_differential:
            return self._new_considerations_from_findings(interpretation_findings)

        updates: list[dict[str, Any]] = []
        seen: set[str] = set()

        for dx in previous_differential:
            name = dx.get("diagnosis_name")
            if not name or name in seen:
                continue
            seen.add(name)

            direction, reasoning, related = self._evaluate_diagnosis(name, dx, interpretation_findings)
            updates.append(
                {
                    "diagnosis_name": name,
                    "previous_confidence": dx.get("confidence_indicator"),
                    "previous_category": dx.get("category"),
                    "update_direction": direction,
                    "reasoning": reasoning,
                    "related_finding_title": related,
                    "version": 1,
                }
            )

        for finding in interpretation_findings:
            for name in finding.get("supporting_diagnoses") or []:
                if name in seen:
                    continue
                seen.add(name)
                updates.append(
                    {
                        "diagnosis_name": name,
                        "previous_confidence": None,
                        "previous_category": None,
                        "update_direction": UPDATE_NEW_CONSIDERATION,
                        "reasoning": (
                            f"New consideration based on {finding.get('finding_title')}: "
                            f"{finding.get('significance', '')}"
                        ),
                        "related_finding_title": finding.get("finding_title"),
                        "version": 1,
                    }
                )

        return updates

    @staticmethod
    def _evaluate_diagnosis(
        name: str,
        dx: dict[str, Any],
        findings: list[dict[str, Any]],
    ) -> tuple[str, str, str | None]:
        supporting_hits: list[str] = []
        contradicting_hits: list[str] = []
        related_title: str | None = None

        for finding in findings:
            title = finding.get("finding_title") or ""
            if name in (finding.get("supporting_diagnoses") or []):
                supporting_hits.append(title)
                related_title = related_title or title
            if name in (finding.get("contradicting_diagnoses") or []):
                contradicting_hits.append(title)
                related_title = related_title or title

        if supporting_hits and not contradicting_hits:
            return (
                UPDATE_MORE_LIKELY,
                f"New data ({', '.join(supporting_hits)}) supports this diagnosis in the current differential.",
                related_title,
            )
        if contradicting_hits and not supporting_hits:
            return (
                UPDATE_LESS_LIKELY,
                f"New data ({', '.join(contradicting_hits)}) weighs against this diagnosis.",
                related_title,
            )
        if supporting_hits and contradicting_hits:
            return (
                UPDATE_UNCHANGED,
                "Mixed supporting and contradicting new data — differential weight unchanged pending review.",
                related_title,
            )

        missing = dx.get("missing_information") or []
        if missing and findings:
            return (
                UPDATE_UNCHANGED,
                "No direct impact from new results; prior missing information may still apply.",
                None,
            )
        return (
            UPDATE_UNCHANGED,
            "No significant change suggested from newly available clinical data.",
            None,
        )

    @staticmethod
    def _new_considerations_from_findings(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
        updates: list[dict[str, Any]] = []
        seen: set[str] = set()
        for finding in findings:
            for name in finding.get("supporting_diagnoses") or []:
                if name in seen:
                    continue
                seen.add(name)
                updates.append(
                    {
                        "diagnosis_name": name,
                        "previous_confidence": None,
                        "previous_category": None,
                        "update_direction": UPDATE_NEW_CONSIDERATION,
                        "reasoning": f"Suggested from {finding.get('finding_title')}: {finding.get('significance', '')}",
                        "related_finding_title": finding.get("finding_title"),
                        "version": 1,
                    }
                )
        return updates
