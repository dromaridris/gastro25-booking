"""Platform — validation rule evaluation."""

from dataclasses import dataclass

from app.modules.clinical_reports.platform.registry import load_bundle


@dataclass
class ValidationFinding:
    rule_id: str
    severity: str
    message: str


def evaluate_validation(template_key: str, payload: dict, acknowledgments: list | None = None) -> list[ValidationFinding]:
    bundle = load_bundle(template_key)
    ack_set = set(acknowledgments or [])
    from app.modules.clinical_reports.fields.payload import StructuredPayload

    check_payload = StructuredPayload(payload, template_key=template_key).legacy_dict()
    findings = []
    for rule in bundle.validation_rules:
        if not rule["check"](check_payload):
            if rule["severity"] == "warning" and rule["id"] in ack_set:
                continue
            findings.append(
                ValidationFinding(
                    rule_id=rule["id"],
                    severity=rule["severity"],
                    message=rule["message"],
                )
            )
    return findings


def blocking_findings(findings: list[ValidationFinding]) -> list[ValidationFinding]:
    return [f for f in findings if f.severity == "error"]


def has_blocking_errors(findings: list[ValidationFinding]) -> bool:
    return any(f.severity == "error" for f in findings)
