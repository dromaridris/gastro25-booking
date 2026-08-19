"""Procedural metrics and QI indicator computation."""

from app.modules.clinical_reports.platform.registry import load_bundle


def compute_metrics(template_key: str, payload: dict) -> dict[str, str]:
    bundle = load_bundle(template_key)
    if bundle.field_schema is not None:
        from app.modules.clinical_reports.fields.payload import StructuredPayload
        from app.modules.clinical_reports.fields.presence import qi_metrics_from_fsd

        fsd_metrics = qi_metrics_from_fsd(
            bundle.field_schema, StructuredPayload(payload, template_key=template_key)
        )
        if fsd_metrics:
            return fsd_metrics

    results = {}
    from app.modules.clinical_reports.fields.payload import StructuredPayload

    legacy = StructuredPayload(payload, template_key=template_key).legacy_dict()
    for indicator in bundle.qi_indicators:
        value = indicator["compute"](legacy)
        if value is not None:
            results[indicator["key"]] = str(value)
    return results
