"""Thin GI specialty overlay — uses core engines; links endoscopy IX codes when present.

Not a full GI module. Defers procedure engine / EGD report deep integration.
"""

from __future__ import annotations

from typing import Any

# Dictionary investigation codes that map to existing Gastro booking / report modules
GI_ENDOSCOPY_LINKS = {
    "IX_upper_endoscopy": {
        "label": "Upper endoscopy (EGD)",
        "hint": "Use existing EGD / upper GI report module when booking an endoscopy.",
        "booking_procedure_hint": "upper_gi",
    },
    "IX_colonoscopy": {
        "label": "Colonoscopy",
        "hint": "Use existing colonoscopy report module when booking.",
        "booking_procedure_hint": "colonoscopy",
    },
}


def enrich_investigations_for_gi(ix_result: dict[str, Any]) -> dict[str, Any]:
    """Attach endoscopy booking hints without changing core investigation engine."""
    if not ix_result.get("available"):
        return ix_result
    entries = []
    for item in ix_result.get("entries") or []:
        row = dict(item)
        link = GI_ENDOSCOPY_LINKS.get(row.get("code"))
        if link:
            row["gi_overlay"] = link
        entries.append(row)
    out = dict(ix_result)
    out["entries"] = entries
    out["gi_overlay_note"] = (
        "GI module overlay: endoscopy investigations link to existing booking/report flows; "
        "no duplicate procedure engine here."
    )
    return out
