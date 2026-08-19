"""Shared interview tail and helpers for GI intelligence bundles."""

import json


def common_context_rules(start_sort: int = 900) -> list:
    """PMH, drugs, family — low priority contextual closure."""
    step = 10
    return [
        ("q.common.pmh", start_sort, "contextual", 0.5, None, None, None, None, None),
        ("q.common.surgical", start_sort + step, "contextual", 0.4, None, None, None, None, None),
        ("q.common.drugs", start_sort + step * 2, "contextual", 1.0, None, None, None, None, None),
        ("q.common.allergy", start_sort + step * 3, "contextual", 0.3, None, None, None, None, None),
        ("q.common.family", start_sort + step * 4, "contextual", 0.5, None, None, None, None, None),
        ("q.common.smoking", start_sort + step * 5, "contextual", 0.4, None, None, None, None, None),
        ("q.common.alcohol_social", start_sort + step * 6, "contextual", 0.6, None, None, None, None, None),
    ]


def targets(*codes: str) -> str:
    return json.dumps(list(codes))
