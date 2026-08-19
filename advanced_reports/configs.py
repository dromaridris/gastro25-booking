"""Procedure report configurations — field sections and metadata."""

from __future__ import annotations

from advanced_reports import vocabulary as vocab

# Field types: text, long_text, dropdown, yes_no, multi_checkbox


def _segment_fields(prefix: str, label: str, *, finding_options=None) -> list:
    opts = finding_options or vocab.EUS_FINDING
    return [
        {'key': f'{prefix}_normal', 'label': f'{label} — normal', 'type': 'yes_no'},
        {'key': f'{prefix}_findings', 'label': f'{label} — findings', 'type': 'multi_checkbox', 'options': opts},
        {'key': f'{prefix}_detail', 'label': f'{label} — detail', 'type': 'long_text'},
    ]


EUS_SECTIONS = [
    {
        'id': 'context',
        'title': 'Clinical Context',
        'fields': [
            {'key': 'indication_category', 'label': 'Indication category', 'type': 'multi_checkbox', 'options': vocab.EUS_INDICATION},
            {'key': 'indication_detail', 'label': 'Indication detail', 'type': 'long_text'},
            {'key': 'urgency', 'label': 'Urgency', 'type': 'dropdown', 'options': vocab.PROCEDURE_URGENCY},
            {'key': 'consent_obtained', 'label': 'Consent obtained', 'type': 'yes_no'},
            {'key': 'anticoagulation', 'label': 'Anticoagulation / antiplatelet', 'type': 'dropdown', 'options': vocab.ANTICOAGULATION_STATUS},
            {'key': 'targeted_lesion', 'label': 'Targeted lesion description', 'type': 'long_text'},
        ],
    },
    {
        'id': 'technique',
        'title': 'Technique & Target',
        'fields': [
            {'key': 'scope_type', 'label': 'Scope type', 'type': 'dropdown', 'options': vocab.EUS_SCOPE},
            {'key': 'scope_negotiation', 'label': 'Scope negotiation to target', 'type': 'dropdown', 'options': vocab.SCOPE_NEGOTIATION},
            {'key': 'frequency', 'label': 'Frequency', 'type': 'dropdown', 'options': vocab.EUS_FREQUENCY},
            {'key': 'doppler_used', 'label': 'Doppler used', 'type': 'yes_no'},
            {'key': 'contrast_used', 'label': 'Contrast used', 'type': 'yes_no'},
            {'key': 'target_organ', 'label': 'Target organ', 'type': 'dropdown', 'options': vocab.EUS_ORGAN},
            {'key': 'lesion_location', 'label': 'Lesion location', 'type': 'text'},
            {'key': 'lesion_size_mm', 'label': 'Lesion size (mm)', 'type': 'text'},
            {'key': 'echo_layer', 'label': 'Echo layer', 'type': 'dropdown', 'options': vocab.EUS_ECHO_LAYER},
        ],
    },
    {
        'id': 'findings',
        'title': 'Findings by Region',
        'fields': [
            *_segment_fields('pancreas', 'Pancreas'),
            *_segment_fields('bile_duct', 'Bile duct'),
            *_segment_fields('mediastinal', 'Mediastinal'),
            *_segment_fields('rectal', 'Rectal'),
        ],
    },
    {
        'id': 'sampling',
        'title': 'Sampling & Interventions',
        'fields': [
            {'key': 'fna_performed', 'label': 'FNA / FNB performed', 'type': 'yes_no'},
            {'key': 'needle_type', 'label': 'Needle type', 'type': 'dropdown', 'options': vocab.EUS_NEEDLE},
            {'key': 'pass_count', 'label': 'Number of passes', 'type': 'text'},
            {'key': 'rose_performed', 'label': 'ROSE performed', 'type': 'yes_no'},
            {'key': 'cytology_adequacy', 'label': 'Cytology adequacy', 'type': 'dropdown', 'options': vocab.EUS_CYTOLOGY},
        ],
    },
    {
        'id': 'closure',
        'title': 'Closure & Complications',
        'fields': [
            {'key': 'procedure_completed', 'label': 'Procedure completed as planned', 'type': 'yes_no'},
            {'key': 'immediate_complication', 'label': 'Immediate complication', 'type': 'yes_no'},
            {'key': 'complication_types', 'label': 'Complication types', 'type': 'multi_checkbox', 'options': vocab.STANDARD_COMPLICATIONS},
            {'key': 'complication_detail', 'label': 'Complication detail', 'type': 'long_text'},
            {'key': 'specimens_sent', 'label': 'Specimens sent', 'type': 'yes_no'},
            {'key': 'specimen_details', 'label': 'Specimen details', 'type': 'long_text'},
        ],
    },
    {
        'id': 'synthesis',
        'title': 'Impression & Plan',
        'fields': [
            {'key': 'impression_primary', 'label': 'Primary impression', 'type': 'long_text'},
            {'key': 'clinical_plan', 'label': 'Clinical plan', 'type': 'long_text'},
            {'key': 't_stage', 'label': 'T stage (if applicable)', 'type': 'dropdown', 'options': vocab.EUS_T_STAGE},
            {'key': 'addendum_text', 'label': 'Addendum', 'type': 'long_text'},
        ],
    },
]

CAPSULE_SECTIONS = [
    {
        'id': 'context',
        'title': 'Clinical Context',
        'fields': [
            {'key': 'indication_category', 'label': 'Indication category', 'type': 'multi_checkbox', 'options': vocab.CAPSULE_INDICATION},
            {'key': 'indication_detail', 'label': 'Indication detail', 'type': 'long_text'},
            {'key': 'urgency', 'label': 'Urgency', 'type': 'dropdown', 'options': vocab.PROCEDURE_URGENCY},
            {'key': 'consent_obtained', 'label': 'Consent obtained', 'type': 'yes_no'},
            {'key': 'prior_gi_surgery', 'label': 'Prior GI surgery', 'type': 'yes_no'},
            {'key': 'pacemaker_implant', 'label': 'Pacemaker / implantable device', 'type': 'yes_no'},
            {'key': 'swallowing_difficulty', 'label': 'Swallowing difficulty', 'type': 'yes_no'},
        ],
    },
    {
        'id': 'acquisition',
        'title': 'Preparation & Acquisition',
        'fields': [
            {'key': 'prep_regimen', 'label': 'Bowel preparation regimen', 'type': 'dropdown', 'options': vocab.BOWEL_PREP},
            {'key': 'prokinetic_given', 'label': 'Prokinetic given', 'type': 'yes_no'},
            {'key': 'patency_result', 'label': 'Patency capsule result (if done)', 'type': 'yes_no'},
            {'key': 'capsule_type', 'label': 'Capsule type', 'type': 'dropdown', 'options': vocab.CAPSULE_TYPE},
            {'key': 'completion_status', 'label': 'Completion status', 'type': 'dropdown', 'options': vocab.CAPSULE_COMPLETION},
            {'key': 'gastric_transit_hours', 'label': 'Gastric transit (hours)', 'type': 'text'},
        ],
    },
    {
        'id': 'findings',
        'title': 'Findings by Segment',
        'fields': [
            *_segment_fields('oesophagus', 'Oesophagus', finding_options=vocab.CAPSULE_FINDING),
            *_segment_fields('duodenum', 'Duodenum', finding_options=vocab.CAPSULE_FINDING),
            *_segment_fields('jejunum', 'Jejunum', finding_options=vocab.CAPSULE_FINDING),
            *_segment_fields('ileum', 'Ileum', finding_options=vocab.CAPSULE_FINDING),
            *_segment_fields('colon', 'Colon', finding_options=vocab.CAPSULE_FINDING),
        ],
    },
    {
        'id': 'supplementary',
        'title': 'Supplementary Notes',
        'fields': [
            {'key': 'supplementary_notes', 'label': 'Additional notes', 'type': 'long_text'},
        ],
    },
    {
        'id': 'closure',
        'title': 'Closure & Retention Risk',
        'fields': [
            {'key': 'procedure_completed', 'label': 'Study completed as planned', 'type': 'yes_no'},
            {'key': 'immediate_complication', 'label': 'Immediate complication', 'type': 'yes_no'},
            {'key': 'complication_types', 'label': 'Complication types', 'type': 'multi_checkbox', 'options': vocab.STANDARD_COMPLICATIONS},
            {'key': 'complication_detail', 'label': 'Complication detail', 'type': 'long_text'},
            {'key': 'retention_risk', 'label': 'Capsule retention risk', 'type': 'dropdown', 'options': vocab.CAPSULE_RETENTION},
        ],
    },
    {
        'id': 'synthesis',
        'title': 'Impression & Plan',
        'fields': [
            {'key': 'impression_primary', 'label': 'Primary impression', 'type': 'long_text'},
            {'key': 'clinical_plan', 'label': 'Clinical plan', 'type': 'long_text'},
            {'key': 'addendum_text', 'label': 'Addendum', 'type': 'long_text'},
        ],
    },
]


PROCEDURE_REGISTRY = {
    'eus': {
        'key': 'eus',
        'procedure_type': 'eus',
        'label': 'EUS (Endoscopic Ultrasound)',
        'report_prefix': 'EUS',
        'table': 'eus_report',
        'image_table': 'eus_report_image',
        'image_dir': 'eus_images',
        'image_slots': 8,
        'url_prefix': 'eus',
        'sections': EUS_SECTIONS,
        'has_sedation': True,
        'has_anesthesiologist': True,
        'sedation_options_key': 'ercp',
        'print_title': 'Endoscopic Ultrasound (EUS) Report',
        'images_title': 'EUS Images',
    },
    'capsule': {
        'key': 'capsule',
        'procedure_type': 'capsule_endoscopy',
        'label': 'Capsule Endoscopy',
        'report_prefix': 'CAP',
        'table': 'capsule_report',
        'image_table': 'capsule_report_image',
        'image_dir': 'capsule_images',
        'image_slots': 8,
        'url_prefix': 'capsule-endoscopy',
        'sections': CAPSULE_SECTIONS,
        'has_sedation': False,
        'print_title': 'Capsule Endoscopy Report',
        'images_title': 'Capsule Endoscopy Images',
        'print_layout': 'sidebar_images',
        'print_sidebar_slots': 4,
    },
}

# Phase 2 + 3 structured reports loaded from gi_import schemas
from advanced_reports.procedure_catalog import build_loaded_registry  # noqa: E402

try:
    PROCEDURE_REGISTRY.update(build_loaded_registry())
except Exception as _catalog_exc:
    import sys
    print(f'Warning: could not load extended procedure catalog: {_catalog_exc}', file=sys.stderr)


def get_config(procedure_key: str) -> dict:
    cfg = PROCEDURE_REGISTRY.get(procedure_key)
    if not cfg:
        raise KeyError(procedure_key)
    return cfg
