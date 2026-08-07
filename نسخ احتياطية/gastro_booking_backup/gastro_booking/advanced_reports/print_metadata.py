"""Structured metadata rows for print tables (not duplicated in procedure note)."""

from __future__ import annotations

from advanced_reports.note_generators import _fmt_list
from advanced_reports.services import parse_payload


def _val(payload: dict, key: str) -> str:
    raw = payload.get(key)
    if raw is None:
        return ''
    if isinstance(raw, list):
        return _fmt_list(raw)
    return str(raw).strip()


def _normalize(text: str) -> str:
    return ' '.join(str(text).lower().split())


def _values_equivalent(a: str, b: str) -> bool:
    if not a or not b:
        return False
    na, nb = _normalize(a), _normalize(b)
    if na == nb:
        return True
    return na in nb or nb in na


def _sedation(payload: dict, report_row) -> str:
    regimen = (payload.get('sedation_regimen') or '').strip()
    if regimen:
        return regimen
    agents = _fmt_list(payload.get('sedation_agents') or payload.get('sedation_type'))
    if agents:
        return agents
    if hasattr(report_row, 'keys'):
        try:
            return (report_row['sedation'] or '').strip()
        except (KeyError, TypeError):
            pass
    return (getattr(report_row, 'sedation', None) or '').strip()


def _indication_rows(payload: dict) -> list[tuple[str, str]]:
    """Single indication row — merges complaints, category, and detail without repetition."""
    parts: list[str] = []
    for raw in (
        (payload.get('chief_complaints') or '').strip(),
        (payload.get('indication_detail') or '').strip(),
        _val(payload, 'indication_category'),
    ):
        if not raw:
            continue
        if any(_values_equivalent(raw, existing) for existing in parts):
            continue
        parts.append(raw)
    if not parts:
        return []
    return [('Indication', parts[0] if len(parts) == 1 else ' — '.join(parts))]


def _bbps_summary(payload: dict) -> str:
    scores = []
    for key, label in (('bbps_right', 'R'), ('bbps_transverse', 'T'), ('bbps_left', 'L')):
        raw = _val(payload, key)
        if raw and raw[0].isdigit():
            scores.append(f'{label}{raw[0]}')
    if len(scores) == 3:
        total = sum(int(s[1]) for s in scores)
        return f'{" / ".join(scores)} (total {total})'
    return ' / '.join(scores)


def _rows(*pairs: tuple[str, str]) -> list[tuple[str, str]]:
    return [(label, value) for label, value in pairs if value]


def _refer_row(payload: dict, appt) -> list[tuple[str, str]]:
    ward = _val(payload, 'refer_to')
    booking_ref = _appt_val(appt, 'referral') if appt else ''
    if ward and appt and not _values_equivalent(ward, booking_ref):
        return [('Refer / ward', ward)]
    return []


def build_egd_clinical_rows(payload: dict, report_row, appt=None) -> list[tuple[str, str]]:
    return _refer_row(payload, appt) + _indication_rows(payload) + _rows(
        ('Urgency', _val(payload, 'urgency')),
        ('Scope', _val(payload, 'scope_type')),
        ('D2 reached', _val(payload, 'd2_reached')),
        ('Retroflexion', _val(payload, 'retroflexion_performed')),
        ('Procedure duration (min)', _val(payload, 'procedure_duration_min')),
        ('ASA class', _val(payload, 'asa_class')),
        ('Anticoagulation', _val(payload, 'anticoagulation')),
        ('Variceal banding', _val(payload, 'variceal_banding_performed')),
        ('Bands placed', _val(payload, 'bands_placed')),
        ('Sclerotherapy', _val(payload, 'sclerotherapy_performed')),
        ('PEG placement', _val(payload, 'intervention_peg')),
        ('Polypectomy', _val(payload, 'intervention_polypectomy')),
        ('Dilatation', _val(payload, 'intervention_dilatation')),
        ('EMR / ESD', _val(payload, 'intervention_emr_esd')),
        ('Immediate complication', _val(payload, 'immediate_complication')),
    )


def build_colonoscopy_clinical_rows(payload: dict, report_row, appt=None) -> list[tuple[str, str]]:
    return _refer_row(payload, appt) + _indication_rows(payload) + _rows(
        ('Urgency', _val(payload, 'urgency')),
        ('Scope', _val(payload, 'scope_type')),
        ('Caecum reached', _val(payload, 'caecum_reached')),
        ('Terminal ileum intubated', _val(payload, 'ti_intubated')),
        ('BBPS (R / T / L)', _bbps_summary(payload)),
        ('Withdrawal time (min)', _val(payload, 'withdrawal_time_min')),
        ('Bowel preparation', _val(payload, 'prep_regimen')),
        ('Polypectomy', _val(payload, 'polypectomy_performed')),
        ('Polyps resected', _val(payload, 'polyps_resected_count')),
        ('Adenoma documented', _val(payload, 'adenoma_documented')),
        ('Immediate complication', _val(payload, 'immediate_complication')),
    )


def build_egd_metadata_rows(payload: dict, report_row) -> list[tuple[str, str]]:
    return build_egd_clinical_rows(payload, report_row)


def build_colonoscopy_metadata_rows(payload: dict, report_row) -> list[tuple[str, str]]:
    return build_colonoscopy_clinical_rows(payload, report_row)


_SKIP_UNIFIED_KEYS = frozenset({
    'impression_primary', 'clinical_plan', 'addendum_text',
    'chief_complaints', 'indication_category', 'indication_detail',
    'refer_to', 'sedation_regimen', 'sedation_agents', 'sedation_type',
})


def build_generic_clinical_rows(
    cfg: dict,
    payload: dict,
    appt=None,
) -> list[tuple[str, str]]:
    """Schema-driven metadata rows for unified print table (non-EGD/colonoscopy)."""
    rows: list[tuple[str, str]] = []
    rows.extend(_refer_row(payload, appt))
    rows.extend(_indication_rows(payload))
    for section in cfg.get('sections', []):
        if section.get('id') == 'synthesis':
            continue
        for field in section.get('fields', []):
            key = field['key']
            if key in _SKIP_UNIFIED_KEYS:
                continue
            val = payload.get(key)
            if val in (None, '', [], {}):
                continue
            if field.get('type') in ('multi_checkbox', 'multi_select'):
                text = _fmt_list(val)
            else:
                text = str(val).strip()
            if not text:
                continue
            label = field['label']
            if any(r[0] == label and _values_equivalent(text, r[1]) for r in rows):
                continue
            rows.append((label, text))
    return rows


def build_print_metadata(procedure_key: str, report_row, cfg: dict | None = None) -> list[tuple[str, str]]:
    payload = parse_payload(report_row['payload_json'])
    if procedure_key == 'upper_gi_v2':
        return build_egd_clinical_rows(payload, report_row)
    if procedure_key == 'colonoscopy_v2':
        return build_colonoscopy_clinical_rows(payload, report_row)
    if cfg:
        return build_generic_clinical_rows(cfg, payload)
    return []


def _appt_val(appt, key: str, default: str = '') -> str:
    if hasattr(appt, 'keys'):
        try:
            val = appt[key]
            return (val if val is not None else default) or default
        except (KeyError, TypeError, IndexError):
            return default
    return getattr(appt, key, default) or default


def build_unified_print_rows(
    procedure_key: str,
    report_row,
    appt,
    cfg: dict,
    *,
    assistants_lines: list[str] | None = None,
) -> list[tuple[str, str]]:
    """One deduplicated table: patient + team + clinical (each fact once)."""
    payload = parse_payload(report_row['payload_json'])
    rows: list[tuple[str, str]] = [
        ('Patient Name', _appt_val(appt, 'patient_name', '—')),
        ('MR Number', _appt_val(appt, 'mrn', '—') or '—'),
        ('Age / Gender', f"{_appt_val(appt, 'age')} / {_appt_val(appt, 'gender')}"),
        ('Procedure Date', _appt_val(appt, 'appointment_date', '—')),
    ]

    referral = _appt_val(appt, 'referral') or _val(payload, 'refer_to')
    rows.append(('Referral', referral or '—'))

    sedation = _sedation(payload, report_row)
    if sedation:
        rows.append(('Sedation', sedation))

    technician = (report_row['technician'] or '').strip()
    if technician:
        rows.append(('Technician', technician))

    if assistants_lines:
        assistants = ', '.join(line for line in assistants_lines if line)
    else:
        assistants = (report_row['assistants'] or '').strip()
    if assistants:
        rows.append(('Assistants', assistants))

    if cfg.get('has_anesthesiologist'):
        try:
            anes = (report_row['anesthesiologist'] or '').strip()
        except (KeyError, TypeError):
            anes = ''
        if anes:
            rows.append(('Anesthesiologist', anes if anes.lower().startswith('dr') else f'Dr. {anes}'))

    if procedure_key == 'upper_gi_v2':
        rows.extend(build_egd_clinical_rows(payload, report_row, appt))
    elif procedure_key == 'colonoscopy_v2':
        rows.extend(build_colonoscopy_clinical_rows(payload, report_row, appt))
    else:
        rows.extend(build_generic_clinical_rows(cfg, payload, appt))

    return rows


def image_caption(payload: dict, slot: int) -> str:
    caps = payload.get('image_captions')
    if isinstance(caps, dict):
        return str(caps.get(str(slot)) or caps.get(slot) or '').strip()
    return str(payload.get(f'image_caption_{slot}') or '').strip()


def build_all_print_images(
    slots: list,
    payload: dict,
    *,
    url_for_image,
) -> list[dict]:
    """All uploaded images for ERCP-style page-2 grid (≥5 images mode)."""
    items: list[dict] = []
    for slot, img in slots:
        if not img:
            continue
        items.append({
            'slot': slot,
            'url': url_for_image(slot),
            'caption': image_caption(payload, slot),
        })
    return items


def build_print_images(
    slots: list,
    payload: dict,
    *,
    sidebar_max: int,
    url_for_image,
) -> tuple[list[dict], list[dict]]:
    """Return (sidebar_images, page2_images) — uploaded slots only."""
    sidebar: list[dict] = []
    page2: list[dict] = []
    for slot, img in slots:
        if not img:
            continue
        item = {
            'slot': slot,
            'url': url_for_image(slot),
            'caption': image_caption(payload, slot),
        }
        if slot <= sidebar_max:
            sidebar.append(item)
        else:
            page2.append(item)
    return sidebar, page2
