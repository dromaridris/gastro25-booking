"""Build PROCEDURE_REGISTRY from gi_import schemas + phase 3 configs."""

from __future__ import annotations

from advanced_reports.phase3_sections import (
    EVL_SECTIONS,
    LIVER_BIOPSY_SECTIONS,
    SCLEROTHERAPY_SECTIONS,
    STENT_SECTIONS,
)
from advanced_reports.schema_loader import load_schema_meta, load_schema_sections

# Phase 2 — schemas in gi_import
PHASE2_PROCEDURES = [
    {
        'key': 'upper_gi_v2',
        'procedure_type': 'upper_gi',
        'booking_procedure_types': ('upper_gi', 'peg_tube'),
        'schema': 'upper_gi_v2.json',
        'url_prefix': 'upper-gi',
        'report_prefix': 'OGD',
        'has_sedation': True,
        'image_slots': 8,
        'merge_egd_sections': True,
        'print_layout': 'sidebar_images',
        'print_sidebar_slots': 4,
    },
    {
        'key': 'colonoscopy_v2',
        'procedure_type': 'colonoscopy',
        'booking_procedure_types': ('colonoscopy', 'polypectomy'),
        'schema': 'colonoscopy_v2.json',
        'url_prefix': 'colonoscopy',
        'report_prefix': 'COL',
        'has_sedation': True,
        'image_slots': 8,
        'merge_colonoscopy_sections': True,
        'print_layout': 'sidebar_images',
        'print_sidebar_slots': 4,
    },
    {
        'key': 'sigmoidoscopy',
        'procedure_type': 'sigmoidoscopy',
        'schema': 'flex_sig_v2.json',
        'url_prefix': 'sigmoidoscopy',
        'report_prefix': 'FSIG',
        'has_sedation': True,
        'image_slots': 6,
    },
    {
        'key': 'proctoscopy',
        'procedure_type': 'proctoscopy',
        'schema': 'proctoscopy_v2.json',
        'url_prefix': 'proctoscopy',
        'report_prefix': 'PROC',
        'has_sedation': True,
        'image_slots': 4,
    },
    {
        'key': 'enteroscopy',
        'procedure_type': 'enteroscopy',
        'schema': 'enteroscopy.json',
        'url_prefix': 'enteroscopy',
        'report_prefix': 'ENT',
        'has_sedation': True,
        'has_anesthesiologist': True,
        'sedation_options_key': 'ercp',
        'image_slots': 8,
    },
    {
        'key': 'emr',
        'procedure_type': 'emr',
        'schema': 'emr.json',
        'url_prefix': 'emr',
        'report_prefix': 'EMR',
        'has_sedation': True,
        'image_slots': 8,
    },
    {
        'key': 'esd',
        'procedure_type': 'esd',
        'schema': 'esd.json',
        'url_prefix': 'esd',
        'report_prefix': 'ESD',
        'has_sedation': True,
        'has_anesthesiologist': True,
        'sedation_options_key': 'ercp',
        'image_slots': 8,
    },
]

# Phase 3 — custom sections (booking keys already exist)
PHASE3_PROCEDURES = [
    {
        'key': 'variceal_band_ligation',
        'procedure_type': 'variceal_band_ligation',
        'url_prefix': 'variceal-band-ligation',
        'report_prefix': 'EVL',
        'label': 'Variceal Band Ligation (EVL)',
        'sections': EVL_SECTIONS,
        'has_sedation': True,
        'image_slots': 6,
    },
    {
        'key': 'sclerotherapy',
        'procedure_type': 'sclerotherapy',
        'url_prefix': 'sclerotherapy',
        'report_prefix': 'SCL',
        'label': 'Sclerotherapy',
        'sections': SCLEROTHERAPY_SECTIONS,
        'has_sedation': True,
        'image_slots': 4,
    },
    {
        'key': 'stent_placement',
        'procedure_type': 'stent_placement',
        'url_prefix': 'stent-placement',
        'report_prefix': 'STENT',
        'label': 'Endoscopic Stent Placement',
        'sections': STENT_SECTIONS,
        'has_sedation': True,
        'image_slots': 6,
    },
    {
        'key': 'liver_biopsy',
        'procedure_type': 'liver_biopsy',
        'url_prefix': 'liver-biopsy',
        'report_prefix': 'LBX',
        'label': 'Liver Biopsy (EUS/TJLB)',
        'sections': LIVER_BIOPSY_SECTIONS,
        'has_sedation': True,
        'has_anesthesiologist': True,
        'sedation_options_key': 'ercp',
        'image_slots': 4,
    },
]

DILATATION_ALIASES = frozenset({'balloon_dilatation', 'esophageal_dilatation'})


def _table_names(key: str) -> tuple[str, str, str]:
    safe = key.replace('-', '_')
    return f'{safe}_report', f'{safe}_report_image', f'{safe}_images'


def build_loaded_registry() -> dict:
    from colonoscopy_reports.colonoscopy_sections import (
        COLONOSCOPY_HEADER_SECTION,
        COLONOSCOPY_THERAPY_SECTIONS,
    )
    from egd_reports.egd_sections import (
        EGD_DETAILED_FINDINGS,
        EGD_HEADER_SECTION,
        EGD_THERAPY_SECTIONS,
    )

    out = {}
    for spec in PHASE2_PROCEDURES:
        meta = load_schema_meta(spec['schema'])
        sections = load_schema_sections(spec['schema'])
        if spec.get('merge_egd_sections'):
            ctx_end = next((i for i, s in enumerate(sections) if s['id'] == 'findings'), len(sections))
            sections = (
                [EGD_HEADER_SECTION]
                + sections[:ctx_end]
                + [EGD_DETAILED_FINDINGS]
                + sections[ctx_end:]
                + EGD_THERAPY_SECTIONS
            )
        if spec.get('merge_colonoscopy_sections'):
            ctx_end = next((i for i, s in enumerate(sections) if s['id'] == 'findings'), len(sections))
            synth_start = next((i for i, s in enumerate(sections) if s['id'] == 'synthesis'), len(sections))
            sections = (
                [COLONOSCOPY_HEADER_SECTION]
                + sections[:ctx_end]
                + sections[ctx_end:synth_start]
                + COLONOSCOPY_THERAPY_SECTIONS
                + sections[synth_start:]
            )
        table, image_table, image_dir = _table_names(spec['key'])
        out[spec['key']] = {
            'key': spec['key'],
            'procedure_type': spec['procedure_type'],
            'booking_procedure_types': spec.get('booking_procedure_types'),
            'label': meta['label'],
            'report_prefix': spec['report_prefix'],
            'table': table,
            'image_table': image_table,
            'image_dir': image_dir,
            'image_slots': spec.get('image_slots', 6),
            'url_prefix': spec['url_prefix'],
            'sections': sections,
            'has_sedation': spec.get('has_sedation', True),
            'has_anesthesiologist': spec.get('has_anesthesiologist', False),
            'sedation_options_key': spec.get('sedation_options_key'),
            'print_title': meta['label'],
            'images_title': f"{meta['label']} Images",
            'print_layout': spec.get('print_layout', 'sidebar_images'),
            'print_sidebar_slots': spec.get('print_sidebar_slots', 4),
        }
    for spec in PHASE3_PROCEDURES:
        table, image_table, image_dir = _table_names(spec['key'])
        out[spec['key']] = {
            'key': spec['key'],
            'procedure_type': spec['procedure_type'],
            'booking_procedure_types': spec.get('booking_procedure_types'),
            'label': spec['label'],
            'report_prefix': spec['report_prefix'],
            'table': table,
            'image_table': image_table,
            'image_dir': image_dir,
            'image_slots': spec.get('image_slots', 6),
            'url_prefix': spec['url_prefix'],
            'sections': spec['sections'],
            'has_sedation': spec.get('has_sedation', True),
            'has_anesthesiologist': spec.get('has_anesthesiologist', False),
            'sedation_options_key': spec.get('sedation_options_key'),
            'print_title': spec['label'],
            'images_title': f"{spec['label']} Images",
            'print_layout': spec.get('print_layout', 'sidebar_images'),
            'print_sidebar_slots': spec.get('print_sidebar_slots', 4),
        }
    return out
