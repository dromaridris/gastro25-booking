"""Upper GI and Colonoscopy report services."""

from __future__ import annotations

import report_service


PROCEDURE_CONFIG = {
    'upper_gi': {
        'table': 'upper_gi_report',
        'procedure_type': 'upper_gi',
        'label': 'Upper GI Endoscopy',
    },
    'colonoscopy': {
        'table': 'colonoscopy_report',
        'procedure_type': 'colonoscopy',
        'label': 'Colonoscopy',
    },
}


def get_config(procedure_key: str) -> dict:
    if procedure_key not in PROCEDURE_CONFIG:
        raise ValueError(f'Unknown procedure: {procedure_key}')
    return PROCEDURE_CONFIG[procedure_key]


def get_or_create(db, procedure_key: str, appointment_id: int, username: str):
    cfg = get_config(procedure_key)
    return report_service.get_or_create_report(
        db, cfg['table'], 'appointment_id', appointment_id, username,
    )


def save_report(db, procedure_key: str, report_id: int, fields: dict) -> None:
    cfg = get_config(procedure_key)
    allowed = {
        'upper_gi': ('indication', 'procedure_detail', 'findings_text', 'impression',
                     'recommendations', 'complications', 'endoscopist_id', 'procedure_note'),
        'colonoscopy': ('indication', 'procedure_detail', 'prep_quality', 'caecum_reached',
                        'findings_text', 'impression', 'recommendations', 'complications',
                        'endoscopist_id', 'procedure_note'),
    }[procedure_key]
    field_dict = {}
    for key in allowed:
        if key in fields:
            field_dict[key] = fields[key] if fields[key] != '' else None
    if not field_dict:
        return
    report_service.save_fields(db, cfg['table'], report_id, field_dict)
    db.commit()


def generate_note(procedure_key: str, report_row) -> str:
    if procedure_key == 'upper_gi':
        parts = [
            f"Indication: {report_row['indication'] or '—'}",
            f"Procedure: {report_row['procedure_detail'] or '—'}",
            f"Findings: {report_row['findings_text'] or '—'}",
            f"Impression: {report_row['impression'] or '—'}",
            f"Recommendations: {report_row['recommendations'] or '—'}",
        ]
        if report_row['complications']:
            parts.append(f"Complications: {report_row['complications']}")
    else:
        parts = [
            f"Indication: {report_row['indication'] or '—'}",
            f"Preparation: {report_row['prep_quality'] or '—'}",
            f"Caecum reached: {report_row['caecum_reached'] or '—'}",
            f"Procedure: {report_row['procedure_detail'] or '—'}",
            f"Findings: {report_row['findings_text'] or '—'}",
            f"Impression: {report_row['impression'] or '—'}",
            f"Recommendations: {report_row['recommendations'] or '—'}",
        ]
        if report_row['complications']:
            parts.append(f"Complications: {report_row['complications']}")
    return '\n\n'.join(parts)
