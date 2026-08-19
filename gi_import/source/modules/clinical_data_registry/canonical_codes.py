"""Canonical Clinical Object Codes and legacy alias mapping."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class CanonicalCodeDefinition:
    code: str
    source_module: str
    source_type: str
    source_keys: tuple[str, ...]
    description: str = ""


# Canonical codes are the platform-wide vocabulary. Legacy source_keys remain
# on owning modules; CDR resolves aliases transparently.
CANONICAL_REGISTRY: dict[str, CanonicalCodeDefinition] = {
    "lab.cbc.hb": CanonicalCodeDefinition(
        "lab.cbc.hb",
        "investigations",
        "lab_result",
        ("lab.hb", "lab.cbc_hb"),
        "Haemoglobin",
    ),
    "lab.lft.alt": CanonicalCodeDefinition(
        "lab.lft.alt",
        "investigations",
        "lab_result",
        ("lab.alt",),
        "Alanine aminotransferase",
    ),
    "lab.lft.ast": CanonicalCodeDefinition(
        "lab.lft.ast",
        "investigations",
        "lab_result",
        ("lab.ast",),
        "Aspartate aminotransferase",
    ),
    "lab.lft.bilirubin_total": CanonicalCodeDefinition(
        "lab.lft.bilirubin_total",
        "investigations",
        "lab_result",
        ("lab.bilirubin_total",),
        "Total bilirubin",
    ),
    "lab.lft.albumin": CanonicalCodeDefinition(
        "lab.lft.albumin",
        "investigations",
        "lab_result",
        ("lab.albumin",),
        "Serum albumin",
    ),
    "lab.coag.inr": CanonicalCodeDefinition(
        "lab.coag.inr",
        "investigations",
        "lab_result",
        ("lab.inr",),
        "International normalised ratio",
    ),
    "lab.inflammatory.crp": CanonicalCodeDefinition(
        "lab.inflammatory.crp",
        "investigations",
        "lab_result",
        ("lab.crp",),
        "C-reactive protein",
    ),
    "lab.inflammatory.calprotectin": CanonicalCodeDefinition(
        "lab.inflammatory.calprotectin",
        "investigations",
        "lab_result",
        ("lab.calprotectin",),
        "Faecal calprotectin",
    ),
    "lab.rft.creatinine": CanonicalCodeDefinition(
        "lab.rft.creatinine",
        "investigations",
        "lab_result",
        ("lab.creatinine",),
        "Creatinine",
    ),
    "patient.sex": CanonicalCodeDefinition(
        "patient.sex",
        "patients",
        "patient_field",
        ("sex",),
        "Patient sex",
    ),
    "patient.mrn": CanonicalCodeDefinition(
        "patient.mrn",
        "patients",
        "patient_field",
        ("mrn",),
        "Medical record number",
    ),
}


def _build_legacy_index() -> dict[tuple[str, str], str]:
    index: dict[tuple[str, str], str] = {}
    for canonical, definition in CANONICAL_REGISTRY.items():
        for key in definition.source_keys:
            index[(definition.source_type, key)] = canonical
    return index


LEGACY_TO_CANONICAL: dict[tuple[str, str], str] = _build_legacy_index()


def canonical_for_legacy(source_type: str, source_key: str) -> str | None:
    return LEGACY_TO_CANONICAL.get((source_type, source_key))


def definition_for_canonical(code: str) -> CanonicalCodeDefinition | None:
    return CANONICAL_REGISTRY.get(code)


def definition_for_legacy(source_type: str, source_key: str) -> CanonicalCodeDefinition | None:
    canonical = canonical_for_legacy(source_type, source_key)
    if canonical:
        return CANONICAL_REGISTRY.get(canonical)
    return None


def all_source_keys(definition: CanonicalCodeDefinition) -> Iterable[str]:
    return definition.source_keys
