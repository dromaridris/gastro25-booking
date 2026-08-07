"""Professional narrative generator for structured EGD (Upper GI) reports.

Note policy: segmental findings + biopsy/interventions only.
Metadata (sedation, refer, complaints, scope, D2, etc.) → print tables.
Impression & clinical plan → separate report fields.
"""

from __future__ import annotations

from advanced_reports.note_generators import _fmt_list, _no, _yes


def _lower_list(val) -> str:
    text = _fmt_list(val)
    return text.lower() if text else ''


def _oesophagus_block(payload: dict) -> str:
    parts = []
    findings = _lower_list(payload.get('oesophagus_findings'))
    hill = (payload.get('hill_grade') or '').strip()
    detail = (payload.get('oesophagus_detail') or payload.get('ge_junction_detail') or '').strip()

    desc_bits = []
    if findings:
        desc_bits.append(findings)
    elif _no(payload.get('oesophagus_normal')):
        desc_bits.append('abnormal mucosa')
    if hill and ('hernia' in findings or 'hiatus' in findings):
        desc_bits.append(f'({hill})')
    if _yes(payload.get('red_wale_markings')) and 'red wale' not in findings:
        desc_bits.append('red wale markings')
    grade = (payload.get('variceal_grade') or '').strip()
    if grade and 'varic' in findings:
        desc_bits.append(f'{grade.lower()} varices')

    if desc_bits:
        parts.append(', '.join(desc_bits) + ' seen')

    if _yes(payload.get('variceal_banding_performed')):
        bands = (payload.get('bands_placed') or '').strip()
        band_text = f'{bands} band(s) applied' if bands else 'Band ligation performed'
        if _yes(payload.get('hemostasis_achieved_banding')):
            band_text += ', good haemostasis achieved'
        parts.append(band_text)

    gej = detail if detail and ('cm' in detail.lower() or '@' in detail) else ''
    if not gej and detail:
        gej = detail
    if gej:
        gej_clean = gej.replace('GE junction', 'GEJ').replace('ge junction', 'GEJ')
        if not gej_clean.upper().startswith('GEJ'):
            gej_clean = f'GEJ@{gej_clean.lstrip("@")}'
        parts.append(gej_clean.rstrip('.') + '.')

    if not parts:
        if _yes(payload.get('oesophagus_normal')):
            return 'Oesophagus: Normal mucosa.'
        return ''

    body = '. '.join(p.rstrip('.') for p in parts) + '.'
    if body:
        body = body[0].upper() + body[1:]
    return f'Oesophagus: {body}'


def _stomach_subregion(label: str, prefix: str, payload: dict) -> str | None:
    findings = _lower_list(payload.get(f'{prefix}_findings'))
    detail = (payload.get(f'{prefix}_detail') or '').strip()
    if not findings and not detail:
        return None
    line = f'{label}: '
    if findings:
        line += findings + ' seen'
    elif detail:
        line += detail.rstrip('.')
    else:
        line += 'findings documented'
    if detail and findings:
        line += f'. {detail.rstrip(".")}'
    return line + '.'


def _stomach_block(payload: dict) -> list[str]:
    lines = ['Stomach:']
    sub_lines = [
        _stomach_subregion('Fundus', 'stomach_fundus', payload),
        _stomach_subregion('Body', 'stomach_body', payload),
        _stomach_subregion('Antrum', 'stomach_antrum', payload),
    ]
    sub_lines = [s for s in sub_lines if s]

    if sub_lines:
        lines.extend(['\t' + s for s in sub_lines])
    else:
        findings = _lower_list(payload.get('stomach_findings'))
        detail = (payload.get('stomach_detail') or '').strip()
        phg = (payload.get('phg_severity') or '').strip()
        if findings or detail or phg:
            text = findings or 'findings documented'
            if phg and 'portal hypertensive' not in text:
                text = f'{phg.lower()} portal hypertensive gastropathy, {text}'
            line = f'{text} seen'
            if detail:
                line += f'. {detail.rstrip(".")}'
            lines.append(f'\t{line.capitalize()}.')

    if _yes(payload.get('sclerotherapy_performed')):
        agent = (payload.get('sclerotherapy_agent') or 'Histoacryl').strip()
        diluent = (payload.get('sclerotherapy_diluent') or '').strip()
        site = (payload.get('sclerotherapy_site') or 'the varix').strip()
        inj = f'Inj {agent}'
        if diluent:
            inj += f' diluted in {diluent}'
        inj += f' injected into {site.lower()}'
        if _yes(payload.get('sclerotherapy_hemostasis')):
            inj += ', good haemostasis achieved'
        lines.append(f'\t{inj}.')

    if len(lines) == 1:
        if _yes(payload.get('stomach_normal')):
            return ['Stomach: Normal mucosa.']
        return []
    return lines


def _duodenum_block(payload: dict) -> list[str]:
    d1 = _stomach_subregion('D1', 'duodenum_d1', payload)
    d2 = _stomach_subregion('D2', 'duodenum_d2', payload)
    if d1 or d2:
        lines = ['Duodenum:']
        if d1:
            lines.append('\t' + d1)
        if d2:
            lines.append('\t' + d2)
        return lines

    findings = _lower_list(payload.get('duodenum_findings'))
    detail = (payload.get('duodenum_detail') or '').strip()
    if _yes(payload.get('duodenum_normal')):
        return ['Duodenum: Normal mucosa to D2.']
    if findings or detail:
        text = findings or 'abnormal mucosa'
        line = f'Duodenum: {text} seen'
        if detail:
            line += f'. {detail.rstrip(".")}'
        return [line + '.']
    if _yes(payload.get('d2_reached')):
        return ['Duodenum: Normal mucosa to D2.']
    return []


def _biopsy_line(payload: dict) -> str:
    detail = (payload.get('biopsy_detail') or '').strip()
    if detail:
        return f'Biopsy: {detail.rstrip(".")}.'
    if _yes(payload.get('intervention_biopsy')):
        spec = (payload.get('specimen_details') or '').strip()
        return f'Biopsy: {spec or "Specimens taken as documented"}.'
    if _no(payload.get('intervention_biopsy')):
        return 'Biopsy: None.'
    if _yes(payload.get('specimens_sent')):
        spec = (payload.get('specimen_details') or '').strip()
        return f'Biopsy: {spec or "Specimens sent for histology"}.'
    return 'Biopsy: None.'


def _other_interventions_block(payload: dict) -> list[str]:
    labels = (
        ('intervention_peg', 'PEG placement'),
        ('intervention_polypectomy', 'Polypectomy'),
        ('intervention_dilatation', 'Dilatation'),
        ('intervention_stent', 'Stent placement'),
        ('intervention_apc', 'APC'),
        ('intervention_emr_esd', 'EMR / ESD'),
    )
    done = [label for key, label in labels if _yes(payload.get(key))]
    detail = (payload.get('other_interventions_detail') or '').strip()
    if not done and not detail:
        return []
    parts = []
    if done:
        parts.append('Other interventions: ' + ', '.join(done) + '.')
    if detail:
        parts.append(detail.rstrip('.') + '.')
    return parts


def generate_upper_gi_note(payload: dict, report_row) -> str:
    """Findings-only OGD note — no header metadata, diagnosis, or advice."""
    sections = []

    oes = _oesophagus_block(payload)
    if oes:
        sections.append(oes)

    stomach_lines = _stomach_block(payload)
    if stomach_lines:
        sections.append('\n'.join(stomach_lines))

    duodenum_lines = _duodenum_block(payload)
    if duodenum_lines:
        sections.append('\n'.join(duodenum_lines))

    biopsy = _biopsy_line(payload)
    if biopsy:
        if sections:
            sections.append('')
        sections.append(biopsy)

    other = _other_interventions_block(payload)
    if other:
        if sections:
            sections.append('')
        sections.extend(other)

    if not sections:
        return 'Upper GI endoscopy performed. No segmental findings documented.'

    return '\n'.join(sections).strip()
