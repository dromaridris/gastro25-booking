"""Professional narrative generator for structured colonoscopy reports.

Note policy: segmental findings + interventions only.
Metadata (sedation, BBPS, caecum, prep, scope, etc.) → print tables.
Impression & clinical plan → separate report fields.
"""

from __future__ import annotations

from advanced_reports.note_generators import _fmt_list, _no, _yes

COLON_SEGMENTS = [
    ('terminal_ileum', 'Terminal ileum'),
    ('caecum', 'Caecum'),
    ('ascending', 'Ascending colon'),
    ('transverse', 'Transverse colon'),
    ('descending', 'Descending colon'),
    ('sigmoid', 'Sigmoid colon'),
    ('rectum', 'Rectum'),
    ('anus', 'Anus'),
]


def _lower_list(val) -> str:
    text = _fmt_list(val)
    return text.lower() if text else ''


def _segment_line(prefix: str, label: str, payload: dict) -> str | None:
    normal = payload.get(f'{prefix}_normal')
    findings = _lower_list(payload.get(f'{prefix}_findings'))
    detail = (payload.get(f'{prefix}_detail') or '').strip()

    if _yes(normal):
        return f'{label}: Normal mucosa.'
    if findings or detail or _no(normal):
        text = findings if findings else 'abnormal mucosa'
        line = f'{label}: {text} seen'
        if detail:
            line += f'. {detail.rstrip(".")}'
        return line + '.'
    return None


def _findings_block(payload: dict) -> list[str]:
    lines = []
    for prefix, label in COLON_SEGMENTS:
        if prefix == 'terminal_ileum' and not _yes(payload.get('ti_intubated')):
            if not payload.get(f'{prefix}_normal') and not payload.get(f'{prefix}_findings'):
                continue
        seg = _segment_line(prefix, label, payload)
        if seg:
            lines.append(seg)
    if not lines:
        if _yes(payload.get('caecum_reached')):
            return ['Normal mucosa throughout the examined colon to caecum.']
        return []
    return lines


def _interventions_block(payload: dict) -> str:
    parts = []
    if _yes(payload.get('polypectomy_performed')):
        count = (payload.get('polyps_resected_count') or '').strip()
        techniques = _lower_list(payload.get('polypectomy_technique'))
        sites = (payload.get('polypectomy_sites') or payload.get('polypectomy_detail') or '').strip()
        label = 'Polypectomy'
        if count:
            label += f' — {count} polyp(s)'
        if techniques:
            label += f' ({techniques})'
        if sites:
            label += f': {sites.rstrip(".")}'
        parts.append(label)
    if _yes(payload.get('intervention_emr')):
        parts.append('EMR performed')
    if _yes(payload.get('intervention_hemostasis')):
        methods = _lower_list(payload.get('hemostasis_method'))
        parts.append(f'Haemostasis{" — " + methods if methods else ""}')
    if _yes(payload.get('intervention_apc')):
        parts.append('APC performed')
    if _yes(payload.get('intervention_dilatation')):
        parts.append('Colonic dilatation performed')
    if _yes(payload.get('intervention_clip')):
        parts.append('Endoscopic clip(s) placed')
    biopsy = (payload.get('biopsy_detail') or '').strip()
    if _yes(payload.get('intervention_biopsy')):
        parts.append(f'Biopsy: {biopsy or "as documented"}')
    elif biopsy:
        parts.append(f'Biopsy: {biopsy.rstrip(".")}')
    elif _yes(payload.get('specimens_sent')):
        spec = (payload.get('specimen_details') or '').strip()
        parts.append(f'Specimens: {spec or "sent for histology"}')
    histo = (payload.get('specimens_to_histology') or '').strip()
    if histo and histo not in ' '.join(parts):
        parts.append(f'Specimens to histology: {histo.rstrip(".")}')
    other = (payload.get('other_interventions_detail') or '').strip()
    if other:
        parts.append(other.rstrip('.'))
    if not parts:
        if _no(payload.get('intervention_biopsy')) and not _yes(payload.get('polypectomy_performed')):
            return 'Biopsy: None.'
        return ''
    return 'Interventions: ' + '. '.join(parts) + '.'


def generate_colonoscopy_note(payload: dict, report_row) -> str:
    """Findings-only colonoscopy note — no header, procedure metrics, diagnosis, or advice."""
    sections = []

    findings = _findings_block(payload)
    if findings:
        sections.extend(findings)

    interventions = _interventions_block(payload)
    if interventions:
        if sections:
            sections.append('')
        sections.append(interventions)

    if not sections:
        return 'Colonoscopy performed. No segmental findings documented.'

    return '\n'.join(sections).strip()
