"""Clinical Knowledge Platform (CKP) — specialty-agnostic knowledge foundation.

Gastroenterology is Domain Pack #1 content only — never hardcoded in engines.
"""

from __future__ import annotations

__version__ = "1.0.0"

# Controlled vocabularies (architecture contract)
ENTITY_TYPES = frozenset({
    "symptom",
    "disease",
    "sign",
    "investigation",
    "investigation_finding",
    "history_question",
    "history_section",
    "risk_factor",
    "drug",
    "procedure",
    "management_action",
    "follow_up_scheme",
    "education",
    "guideline_assertion",
    "pathway",
    "diagnostic_criteria",
    "severity_classification",
    "domain",  # rare as entity; domains also have ckp_domain table
})

RELATIONSHIP_TYPES = frozenset({
    "supports",
    "strongly_supports",
    "argues_against",
    "strongly_argues_against",
    "excludes",
    "suggests",
    "requires",
    "indicates",
    "investigated_by",
    "managed_by",
    "activates",
    "activates_pathway",
    "complication_of",
    "contraindicates",
    "confirms",
    "refutes",
    "associated_with",
    "discriminates",
    "causes",
    "produces",
    "priority_section_for",
    "contains_question",
    "bound_by",
    "supersedes",
})

# Epistemic edges that affect diagnostic confidence
EPISTEMIC_TYPES = frozenset({
    "supports",
    "strongly_supports",
    "argues_against",
    "strongly_argues_against",
    "excludes",
    "suggests",
    "confirms",
    "refutes",
    "associated_with",
    "causes",
})

STRENGTH_CLASSES = (
    "very_strong",
    "strong",
    "moderate",
    "weak",
    "neutral",
    "against",
    "strongly_against",
)

LIFECYCLE_STATES = frozenset({
    "draft",
    "active",
    "deprecated",
    "retired",
})

CONFIDENCE_LABELS = (
    "established",
    "very_strong",
    "strong",
    "moderate",
    "weak",
    "neutral",
    "against",
    "strongly_against",
    "excluded",
    "deferred",
)

# Ordinal for aggregation (higher = more supportive of disease)
STRENGTH_SCORE = {
    "very_strong": 3.0,
    "strong": 2.0,
    "moderate": 1.0,
    "weak": 0.4,
    "neutral": 0.0,
    "against": -1.0,
    "strongly_against": -2.5,
}

REL_DEFAULT_STRENGTH = {
    "suggests": "weak",
    "supports": "moderate",
    "strongly_supports": "strong",
    "argues_against": "against",
    "strongly_argues_against": "strongly_against",
    "excludes": "strongly_against",
    "confirms": "very_strong",
    "refutes": "strongly_against",
    "associated_with": "neutral",
    "causes": "weak",
}
