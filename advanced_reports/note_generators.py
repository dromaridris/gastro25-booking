"""Professional procedure-note narrative builders for advanced reports."""

from __future__ import annotations


def _fmt_list(val, *, conj: str = 'and') -> str:
    if isinstance(val, list):
        items = [str(v).strip() for v in val if str(v).strip()]
    elif isinstance(val, str) and val.strip():
        items = [val.strip()]
    else:
        return ''
    if not items:
        return ''
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f'{items[0]} {conj} {items[1]}'
    return f'{", ".join(items[:-1])}, {conj} {items[-1]}'


def _yes(val) -> bool:
    return str(val or '').strip().lower() == 'yes'


def _no(val) -> bool:
    return str(val or '').strip().lower() == 'no'


def _normalize_completion(raw: str) -> str:
    text = (raw or '').strip().lower()
    if not text:
        return ''
    if text in ('complete', 'complete study'):
        return 'complete'
    if 'retained in stomach' in text or 'incomplete_gastric' in text:
        return 'incomplete_gastric'
    if 'small bowel' in text or 'incomplete_small_bowel' in text:
        return 'incomplete_small_bowel'
    if text.startswith('complete'):
        return 'complete'
    if 'incomplete' in text and 'stomach' in text:
        return 'incomplete_gastric'
    if 'incomplete' in text:
        return 'incomplete_small_bowel'
    return text


def _section(title: str, body: str) -> str:
    text = (body or '').strip()
    if not text:
        return ''
    return f'{title}\n{text}'


def _capsule_indication_sentence(payload: dict) -> str:
    categories = _fmt_list(payload.get('indication_category'))
    detail = (payload.get('indication_detail') or '').strip()
    if categories and detail:
        return (
            f'Wireless capsule endoscopy was performed for evaluation of {categories}, '
            f'with the following clinical context: {detail.rstrip(".")}.'
        )
    if categories:
        return f'Wireless capsule endoscopy was performed for evaluation of {categories}.'
    if detail:
        return f'Wireless capsule endoscopy was performed. Clinical indication: {detail.rstrip(".")}.'
    return 'Wireless capsule endoscopy was performed.'


def _capsule_context_sentences(payload: dict) -> list[str]:
    sentences = []

    urgency = (payload.get('urgency') or '').strip()
    if urgency and urgency.lower() != 'elective':
        sentences.append(f'The study was performed on an {urgency.lower()} basis.')

    if _yes(payload.get('consent_obtained')):
        sentences.append('Written informed consent was obtained prior to capsule ingestion.')

    flags = []
    if _yes(payload.get('prior_gi_surgery')):
        flags.append('prior gastrointestinal surgery')
    if _yes(payload.get('pacemaker_implant')):
        flags.append('an implanted cardiac device')
    if _yes(payload.get('swallowing_difficulty')):
        flags.append('reported swallowing difficulty')
    if flags:
        sentences.append(
            f'Pre-procedure review noted {_fmt_list(flags)}; appropriate precautions were taken before ingestion.'
        )
    elif any(payload.get(k) for k in ('prior_gi_surgery', 'pacemaker_implant', 'swallowing_difficulty')):
        sentences.append(
            'There was no relevant prior gastrointestinal surgery, implanted cardiac device, '
            'or significant swallowing difficulty reported.'
        )

    return sentences


def _capsule_technique_sentences(payload: dict) -> list[str]:
    sentences = []

    prep = (payload.get('prep_regimen') or '').strip()
    if prep:
        sentences.append(f'Bowel preparation consisted of a {prep.lower()} regimen.')

    if _yes(payload.get('prokinetic_given')):
        sentences.append('A prokinetic agent was administered to facilitate gastric emptying and small-bowel transit.')
    elif _no(payload.get('prokinetic_given')):
        sentences.append('No prokinetic agent was required.')

    patency = payload.get('patency_result')
    if _yes(patency):
        sentences.append('Prior patency capsule testing was performed and was considered satisfactory for ingestion.')
    elif _no(patency):
        sentences.append('Patency capsule testing had not been performed prior to this study.')

    capsule_type = (payload.get('capsule_type') or '').strip()
    if capsule_type:
        sentences.append(f'A {capsule_type.lower()} was ingested without difficulty.')

    completion = _normalize_completion(payload.get('completion_status') or '')
    if completion == 'complete':
        sentences.append(
            'The recording captured the full intended small-bowel transit and the study is considered complete.'
        )
    elif completion == 'incomplete_gastric':
        sentences.append(
            'The study was incomplete because the capsule remained within the stomach at the end of the recording period.'
        )
    elif completion == 'incomplete_small_bowel':
        sentences.append(
            'The study was incomplete with failure to fully visualize the entire small bowel during the recording window.'
        )
    elif payload.get('completion_status'):
        sentences.append(f'Completion status: {payload.get("completion_status")}.')

    transit = (payload.get('gastric_transit_hours') or '').strip()
    if transit:
        sentences.append(f'Estimated gastric transit time was approximately {transit} hours.')

    return sentences


def _capsule_closure_sentences(payload: dict) -> list[str]:
    sentences = []

    if _no(payload.get('procedure_completed')):
        sentences.append('The study was not completed as originally planned.')
    elif _yes(payload.get('procedure_completed')):
        sentences.append('The study was completed as planned.')

    if _yes(payload.get('immediate_complication')):
        comps = _fmt_list(payload.get('complication_types'))
        detail = (payload.get('complication_detail') or '').strip()
        if comps and detail:
            sentences.append(
                f'Immediate complication(s) were noted ({comps.lower()}): {detail.rstrip(".")}.'
            )
        elif comps:
            sentences.append(f'Immediate complication(s) were noted: {comps.lower()}.')
        elif detail:
            sentences.append(f'An immediate complication was noted: {detail.rstrip(".")}.')
        else:
            sentences.append('An immediate complication was noted during the study.')
    else:
        sentences.append('No immediate complications were observed during the study period.')

    retention = (payload.get('retention_risk') or '').strip()
    if retention:
        sentences.append(f'Capsule retention risk is assessed as {retention.lower()}.')

    return sentences


def _capsule_segment_finding(prefix: str, label: str, payload: dict) -> str | None:
    normal = payload.get(f'{prefix}_normal')
    findings = _fmt_list(payload.get(f'{prefix}_findings'))
    detail = (payload.get(f'{prefix}_detail') or '').strip()

    if _yes(normal):
        return f'{label}: The visualized mucosa appeared normal with no significant abnormality identified.'
    if _no(normal):
        parts = []
        if findings:
            parts.append(findings.lower())
        else:
            parts.append('abnormal mucosa')
        line = f'{label}: {parts[0].capitalize()} was observed'
        if len(parts) > 1:
            line += f', together with {", ".join(parts[1:]).lower()}'
        if detail:
            line += f'. {detail.rstrip(".")}'
        else:
            line += '.'
        return line
    if findings or detail:
        text = findings.lower() if findings else 'Findings were documented'
        line = f'{label}: {text.capitalize()}'
        if detail:
            line += f'. {detail.rstrip(".")}'
        line += '.'
        return line
    return None


def _capsule_findings_section(payload: dict) -> str:
    segments = [
        ('oesophagus', 'Oesophagus'),
        ('duodenum', 'Duodenum'),
        ('jejunum', 'Jejunum'),
        ('ileum', 'Ileum'),
        ('colon', 'Colon'),
    ]
    lines = []
    all_normal = True
    any_documented = False

    for prefix, label in segments:
        line = _capsule_segment_finding(prefix, label, payload)
        if line:
            lines.append(line)
            any_documented = True
            if not _yes(payload.get(f'{prefix}_normal')):
                all_normal = False
        elif payload.get(f'{prefix}_normal') is not None:
            any_documented = True
            if not _yes(payload.get(f'{prefix}_normal')):
                all_normal = False

    supplementary = (payload.get('supplementary_notes') or '').strip()
    if supplementary:
        lines.append(f'Additional observations: {supplementary.rstrip(".")}.')

    if not lines:
        completion = _normalize_completion(payload.get('completion_status') or '')
        if completion.startswith('incomplete'):
            return (
                'Detailed segmental findings are limited by incomplete small-bowel visualization. '
                'No definitive source of pathology was identified within the visualized segments.'
            )
        return (
            'Segmental review of the oesophagus, duodenum, jejunum, ileum, and visualized colon '
            'showed no significant abnormality.'
        )

    if all_normal and any_documented and len(lines) >= 3:
        summary = (
            'Overall, the visualized oesophagus, duodenum, jejunum, ileum, and colon appeared normal '
            'with no evidence of active bleeding, angioectasia, ulceration, mass lesion, or significant inflammatory change.'
        )
        return '\n'.join(lines + [summary])

    return '\n'.join(lines)


def _capsule_impression_section(payload: dict, report_row) -> str:
    impression = (report_row['impression'] or payload.get('impression_primary') or '').strip()
    if impression:
        return impression.rstrip('.')

    segments = ('oesophagus', 'duodenum', 'jejunum', 'ileum', 'colon')
    documented = [s for s in segments if payload.get(f'{s}_normal') is not None]
    if documented and all(_yes(payload.get(f'{s}_normal')) for s in documented):
        indication = _fmt_list(payload.get('indication_category')).lower()
        if 'obscure' in indication or 'bleeding' in indication:
            return (
                'Normal capsule endoscopy with no identifiable source of obscure gastrointestinal bleeding '
                'within the visualized small bowel.'
            )
        return 'Normal capsule endoscopy with no significant abnormality identified.'

    abnormal = [
        label for prefix, label in (
            ('oesophagus', 'oesophagus'),
            ('duodenum', 'duodenum'),
            ('jejunum', 'jejunum'),
            ('ileum', 'ileum'),
            ('colon', 'colon'),
        )
        if _no(payload.get(f'{prefix}_normal'))
    ]
    if abnormal:
        sites = _fmt_list(abnormal)
        return f'Capsule endoscopy demonstrated abnormality within the {sites.lower()}.'
    return 'Capsule endoscopy findings as detailed above.'


def _capsule_recommendation_section(payload: dict, report_row) -> str:
    parts = []
    plan = (report_row['clinical_plan'] or payload.get('clinical_plan') or '').strip()
    if plan:
        parts.append(plan.rstrip('.'))

    retention = (payload.get('retention_risk') or '').strip().lower()
    if retention in ('moderate', 'high'):
        parts.append(
            'Given the elevated capsule retention risk, close clinical follow-up is advised with low threshold '
            'for cross-sectional imaging if symptoms suggest retention.'
        )

    completion = _normalize_completion(payload.get('completion_status') or '')
    if completion == 'incomplete_gastric':
        parts.append(
            'Incomplete gastric transit was observed; consider repeat capsule study after optimization of gastric '
            'emptying, or alternative small-bowel imaging if clinically indicated.'
        )
    elif completion == 'incomplete_small_bowel':
        parts.append(
            'Incomplete small-bowel visualization was observed; consider repeat capsule endoscopy, device-assisted '
            'enteroscopy, or cross-sectional imaging depending on clinical urgency.'
        )

    if _yes(payload.get('immediate_complication')):
        parts.append('Appropriate clinical follow-up and monitoring for post-procedure complications are recommended.')

    addendum = (payload.get('addendum_text') or '').strip()
    if addendum:
        parts.append(f'Addendum: {addendum.rstrip(".")}.')

    if not parts:
        indication = _fmt_list(payload.get('indication_category')).lower()
        if 'obscure' in indication or 'bleeding' in indication:
            parts.append(
                'Continue clinical follow-up. If bleeding recurs or remains unexplained, consider repeat capsule '
                'endoscopy, device-assisted enteroscopy, or cross-sectional imaging as clinically indicated.'
            )
        else:
            parts.append('Routine clinical follow-up as indicated by the primary treating team.')

    return '. '.join(p.rstrip('.') for p in parts if p) + '.'


def generate_capsule_note(payload: dict, report_row) -> str:
    """Structured capsule endoscopy note: Procedure Details, Findings, Impression, Recommendation."""
    procedure_bits = [_capsule_indication_sentence(payload)]
    procedure_bits.extend(_capsule_context_sentences(payload))
    procedure_bits.extend(_capsule_technique_sentences(payload))
    procedure_bits.extend(_capsule_closure_sentences(payload))

    sections = [
        _section('PROCEDURE DETAILS', ' '.join(procedure_bits)),
        _section('FINDINGS', _capsule_findings_section(payload)),
        _section('IMPRESSION', _capsule_impression_section(payload, report_row)),
        _section('RECOMMENDATION', _capsule_recommendation_section(payload, report_row)),
    ]
    return '\n\n'.join(s for s in sections if s)


SCOPE_NEGOTIATION_PHRASES = {
    'Easy': ('negotiated', 'without difficulty'),
    'Mild difficulty': ('negotiated', 'with mild difficulty'),
    'Moderate difficulty': ('advanced', 'with moderate difficulty'),
    'Difficult': ('advanced', 'with difficulty'),
    'Very difficult': ('advanced', 'with significant difficulty'),
}


def _eus_scope_label(scope_type: str) -> str:
    text = (scope_type or '').strip().lower()
    if 'linear' in text:
        return 'linear echoendoscope'
    if 'radial' in text:
        return 'radial echoendoscope'
    if scope_type:
        return scope_type.strip().lower()
    return 'echoendoscope'


def _build_scope_negotiation_sentence(scope_type: str, negotiation: str) -> str:
    scope_name = _eus_scope_label(scope_type)
    negotiation = (negotiation or '').strip()
    if not negotiation:
        return f'The {scope_name} was advanced to the target region for EUS evaluation.'
    verb, phrase = SCOPE_NEGOTIATION_PHRASES.get(negotiation, ('advanced', ''))
    if phrase:
        return f'The {scope_name} was {verb} to the target region {phrase}.'
    return f'The {scope_name} was {verb} to the target region.'


def _eus_indication_sentence(payload: dict) -> str:
    categories = _fmt_list(payload.get('indication_category'))
    detail = (payload.get('indication_detail') or '').strip()
    if categories and detail:
        return (
            f'Endoscopic ultrasound was performed for evaluation of {categories}, '
            f'with the following clinical context: {detail.rstrip(".")}.'
        )
    if categories:
        return f'Endoscopic ultrasound was performed for evaluation of {categories}.'
    if detail:
        return f'Endoscopic ultrasound was performed. Clinical indication: {detail.rstrip(".")}.'
    return 'Endoscopic ultrasound (EUS) was performed.'


def _eus_context_sentences(payload: dict) -> list[str]:
    sentences = []
    urgency = (payload.get('urgency') or '').strip()
    if urgency and urgency.lower() != 'elective':
        sentences.append(f'The procedure was performed on an {urgency.lower()} basis.')

    if _yes(payload.get('consent_obtained')):
        sentences.append('Written informed consent was obtained prior to the procedure.')

    anticoag = (payload.get('anticoagulation') or '').strip()
    if anticoag and anticoag.lower() not in ('none', ''):
        sentences.append(f'Antithrombotic status: {anticoag}.')

    lesion = (payload.get('targeted_lesion') or '').strip()
    if lesion:
        sentences.append(f'The clinical target was described as: {lesion.rstrip(".")}.')

    return sentences


def _eus_technique_sentences(payload: dict) -> list[str]:
    sentences = [_build_scope_negotiation_sentence(payload.get('scope_type'), payload.get('scope_negotiation'))]

    frequency = (payload.get('frequency') or '').strip()
    if frequency:
        sentences.append(f'Examination was performed using {frequency} ultrasound frequency.')

    imaging_bits = []
    if _yes(payload.get('doppler_used')):
        imaging_bits.append('Doppler interrogation')
    if _yes(payload.get('contrast_used')):
        imaging_bits.append('contrast-enhanced imaging')
    if imaging_bits:
        sentences.append(f'{" and ".join(imaging_bits)} was utilized during the examination.')

    target = (payload.get('target_organ') or '').strip()
    location = (payload.get('lesion_location') or '').strip()
    size = (payload.get('lesion_size_mm') or '').strip()
    echo_layer = (payload.get('echo_layer') or '').strip()

    target_bits = []
    if target:
        target_bits.append(f'the {target.lower()}')
    if location:
        target_bits.append(f'at {location}')
    if size:
        target_bits.append(f'measuring approximately {size} mm')
    if echo_layer:
        target_bits.append(f'originating from the {echo_layer.lower()}')
    if target_bits:
        if len(target_bits) == 1:
            sentences.append(f'EUS evaluation focused on {target_bits[0]}.')
        else:
            sentences.append(f'EUS evaluation focused on {", ".join(target_bits[:-1])}, {target_bits[-1]}.')

    return sentences


def _eus_sampling_sentences(payload: dict) -> list[str]:
    if not _yes(payload.get('fna_performed')):
        return []
    needle = (payload.get('needle_type') or 'an unspecified needle').strip()
    passes = (payload.get('pass_count') or '').strip()
    pass_text = f' using {passes} needle pass(es)' if passes else ''
    sentences = [f'EUS-guided tissue acquisition was performed with {needle}{pass_text}.']
    if _yes(payload.get('rose_performed')):
        sentences.append('Rapid on-site evaluation (ROSE) was performed to assess sample adequacy.')
    adequacy = (payload.get('cytology_adequacy') or '').strip()
    if adequacy:
        sentences.append(f'Initial cytology adequacy was assessed as {adequacy.lower()}.')
    if _yes(payload.get('specimens_sent')):
        detail = (payload.get('specimen_details') or '').strip()
        if detail:
            sentences.append(f'Specimens were sent for analysis: {detail.rstrip(".")}.')
        else:
            sentences.append('Specimens were sent for cytology and/or histopathology as appropriate.')
    return sentences


def _eus_closure_sentences(payload: dict) -> list[str]:
    sentences = []
    if _no(payload.get('procedure_completed')):
        sentences.append('The procedure was not completed as originally planned.')
    elif _yes(payload.get('procedure_completed')):
        sentences.append('The procedure was completed as planned.')

    if _yes(payload.get('immediate_complication')):
        comps = _fmt_list(payload.get('complication_types'))
        detail = (payload.get('complication_detail') or '').strip()
        if comps and detail:
            sentences.append(f'Immediate complication(s) were noted ({comps.lower()}): {detail.rstrip(".")}.')
        elif comps:
            sentences.append(f'Immediate complication(s) were noted: {comps.lower()}.')
        elif detail:
            sentences.append(f'An immediate complication was noted: {detail.rstrip(".")}.')
        else:
            sentences.append('An immediate complication was noted during the procedure.')
    else:
        sentences.append('The patient tolerated the procedure well with no immediate procedure-related complications observed.')
    return sentences


def _eus_segment_finding(prefix: str, label: str, payload: dict) -> str | None:
    normal = payload.get(f'{prefix}_normal')
    findings = _fmt_list(payload.get(f'{prefix}_findings'))
    detail = (payload.get(f'{prefix}_detail') or '').strip()

    if _yes(normal):
        return f'{label}: No focal mass, cystic lesion, ductal abnormality, or suspicious lymphadenopathy was identified.'
    if _no(normal):
        finding_text = findings.lower() if findings else 'abnormal echogenicity or architecture'
        line = f'{label}: {finding_text.capitalize()} was demonstrated'
        if detail:
            line += f'. {detail.rstrip(".")}.'
        else:
            line += '.'
        return line
    if findings or detail:
        text = findings if findings else 'Findings were documented'
        line = f'{label}: {text}'
        if detail:
            line += f'. {detail.rstrip(".")}'
        line += '.'
        return line
    return None


def _eus_findings_section(payload: dict) -> str:
    segments = [
        ('pancreas', 'Pancreas'),
        ('bile_duct', 'Bile duct'),
        ('mediastinal', 'Mediastinal region'),
        ('rectal', 'Rectal wall'),
    ]
    lines = []
    for prefix, label in segments:
        line = _eus_segment_finding(prefix, label, payload)
        if line:
            lines.append(line)

    if not lines:
        target = (payload.get('target_organ') or '').strip()
        if target:
            return f'Focused EUS evaluation of the {target.lower()} demonstrated no significant abnormality within the examined field.'
        return 'EUS evaluation demonstrated no significant abnormality within the examined regions.'

    return '\n'.join(lines)


def _eus_impression_section(payload: dict, report_row) -> str:
    impression = (report_row['impression'] or payload.get('impression_primary') or '').strip()
    if impression:
        return impression.rstrip('.')

    t_stage = (payload.get('t_stage') or '').strip()
    if t_stage and t_stage.lower() not in ('not applicable', 'tx', ''):
        return f'EUS findings as detailed above, with T stage {t_stage} where applicable.'

    abnormal = []
    for prefix, label in (
        ('pancreas', 'pancreas'),
        ('bile_duct', 'bile duct'),
        ('mediastinal', 'mediastinal region'),
        ('rectal', 'rectal wall'),
    ):
        if _no(payload.get(f'{prefix}_normal')):
            abnormal.append(label)
    if abnormal:
        sites = _fmt_list(abnormal)
        return f'EUS demonstrated abnormality involving the {sites.lower()}.'
    return 'EUS evaluation without significant abnormality identified.'


def _eus_recommendation_section(payload: dict, report_row) -> str:
    parts = []
    plan = (report_row['clinical_plan'] or payload.get('clinical_plan') or '').strip()
    if plan:
        parts.append(plan.rstrip('.'))

    adequacy = (payload.get('cytology_adequacy') or '').strip().lower()
    if _yes(payload.get('fna_performed')) and adequacy == 'pending':
        parts.append('Await final cytology and/or histopathology results before definitive management decisions.')
    elif _yes(payload.get('fna_performed')) and adequacy == 'inadequate':
        parts.append('Repeat EUS-guided sampling or alternative diagnostic approach should be considered if clinically indicated.')

    t_stage = (payload.get('t_stage') or '').strip()
    if t_stage and t_stage.lower() not in ('not applicable', 'tx', ''):
        parts.append(f'Staging and management should proceed according to the documented T stage ({t_stage}) and multidisciplinary discussion as appropriate.')

    if _yes(payload.get('immediate_complication')):
        parts.append('Appropriate post-procedure monitoring and follow-up for the documented complication are recommended.')

    addendum = (payload.get('addendum_text') or '').strip()
    if addendum:
        parts.append(f'Addendum: {addendum.rstrip(".")}.')

    if not parts:
        if _yes(payload.get('fna_performed')):
            parts.append('Clinical management should be guided by the sampling results and correlated with cross-sectional imaging and laboratory findings.')
        else:
            parts.append('Clinical follow-up and further investigation should be guided by the primary treating team based on the EUS findings.')

    return '. '.join(p.rstrip('.') for p in parts if p) + '.'


def generate_eus_note(payload: dict, report_row) -> str:
    """Structured EUS note: Procedure Details, Findings, Impression, Recommendation."""
    procedure_bits = [_eus_indication_sentence(payload)]
    procedure_bits.extend(_eus_context_sentences(payload))
    procedure_bits.extend(_eus_technique_sentences(payload))
    procedure_bits.extend(_eus_sampling_sentences(payload))
    procedure_bits.extend(_eus_closure_sentences(payload))

    sections = [
        _section('PROCEDURE DETAILS', ' '.join(procedure_bits)),
        _section('FINDINGS', _eus_findings_section(payload)),
        _section('IMPRESSION', _eus_impression_section(payload, report_row)),
        _section('RECOMMENDATION', _eus_recommendation_section(payload, report_row)),
    ]
    return '\n\n'.join(s for s in sections if s)


def _is_egd_cfg(cfg: dict) -> bool:
    return cfg.get('key') == 'upper_gi_v2' or cfg.get('table') == 'upper_gi_v2_report'


def _is_colonoscopy_cfg(cfg: dict) -> bool:
    return cfg.get('key') == 'colonoscopy_v2' or cfg.get('table') == 'colonoscopy_v2_report'


def generate_structured_note(cfg: dict, payload: dict, report_row) -> str:
    """Four-section note for schema-driven advanced reports."""
    if _is_egd_cfg(cfg):
        from egd_reports.narrative import generate_upper_gi_note
        return generate_upper_gi_note(payload, report_row)
    if _is_colonoscopy_cfg(cfg):
        from colonoscopy_reports.narrative import generate_colonoscopy_note
        return generate_colonoscopy_note(payload, report_row)

    label = cfg.get('label') or 'Procedure'
    procedure_lines = [f'{label} was performed.']
    findings_lines = []
    for section in cfg.get('sections', []):
        sid = section.get('id', '')
        for field in section.get('fields', []):
            key = field['key']
            val = payload.get(key)
            if val in (None, '', [], {}):
                continue
            text = _fmt_list(val) if field.get('type') == 'multi_checkbox' else str(val).strip()
            if not text:
                continue
            if sid in ('findings', 'technique', 'sampling', 'acquisition', 'supplementary'):
                findings_lines.append(f"{field['label']}: {text}.")
            elif sid in ('synthesis',):
                continue
            elif sid in ('closure',):
                if key in ('immediate_complication', 'complication_types', 'complication_detail'):
                    findings_lines.append(f"{field['label']}: {text}.")
                else:
                    procedure_lines.append(f"{field['label']}: {text.rstrip('.')}.")
            else:
                procedure_lines.append(f"{field['label']}: {text.rstrip('.')}.")

    impression = (report_row['impression'] or payload.get('impression_primary') or '').strip()
    if not impression and findings_lines:
        impression = f'{label} findings as detailed below.'

    plan = (report_row['clinical_plan'] or payload.get('clinical_plan') or '').strip()
    if not plan:
        plan = 'Routine clinical follow-up as indicated by the primary treating team.'

    sections = [
        _section('PROCEDURE DETAILS', ' '.join(procedure_lines)),
        _section('FINDINGS', ' '.join(findings_lines) if findings_lines else 'No significant abnormality documented.'),
        _section('IMPRESSION', impression),
        _section('RECOMMENDATION', plan),
    ]
    return '\n\n'.join(s for s in sections if s)
