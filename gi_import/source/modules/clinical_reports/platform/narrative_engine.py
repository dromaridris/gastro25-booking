"""Platform — Generic Narrative Engine."""

from app.modules.clinical_reports.platform.registry import load_bundle
from app.modules.reports.models import (
    SECTION_CLINICAL_INDICATION,
    SECTION_COMPLICATIONS,
    SECTION_FINDINGS,
    SECTION_IMPRESSION,
    SECTION_PROCEDURE_DESCRIPTION,
    SECTION_RECOMMENDATIONS,
)


def generate_narrative(template_key: str, payload: dict) -> dict[str, str]:
    """Return mapping of frozen 3A section_key -> generated text."""
    bundle = load_bundle(template_key)
    if bundle.field_schema is not None:
        from app.modules.clinical_reports.fields.narrative_bindings import generate_narrative_from_fsd

        fsd_sections = generate_narrative_from_fsd(bundle.field_schema, payload)
        if fsd_sections:
            return fsd_sections

    sections = {}
    for section_key, generator in bundle.narrative_sections.items():
        from app.modules.clinical_reports.fields.payload import StructuredPayload

        legacy = StructuredPayload(payload, template_key=template_key).legacy_dict()
        sections[section_key] = generator(legacy)
    return sections


def default_section_keys():
    return [
        SECTION_CLINICAL_INDICATION,
        SECTION_PROCEDURE_DESCRIPTION,
        SECTION_FINDINGS,
        SECTION_IMPRESSION,
        SECTION_RECOMMENDATIONS,
        SECTION_COMPLICATIONS,
    ]
