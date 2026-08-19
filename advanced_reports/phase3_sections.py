"""Phase 3 therapeutic report sections — derived from Upper GI / ERCP / EUS patterns."""

from __future__ import annotations

from advanced_reports import vocabulary as vocab
from advanced_reports.gi_vocabulary import vocab_labels

_SEDATION = vocab_labels('sedation_type') or vocab.SEDATION_TYPE
_COMPLICATIONS = vocab_labels('standard_complication_type') or vocab.STANDARD_COMPLICATIONS
_URGENCY = vocab_labels('procedure_urgency') or vocab.PROCEDURE_URGENCY


def _closure_fields():
    return [
        {'key': 'procedure_completed', 'label': 'Procedure completed as planned', 'type': 'yes_no'},
        {'key': 'immediate_complication', 'label': 'Immediate complication', 'type': 'yes_no'},
        {'key': 'complication_types', 'label': 'Complication types', 'type': 'multi_checkbox', 'options': _COMPLICATIONS},
        {'key': 'complication_detail', 'label': 'Complication detail', 'type': 'long_text'},
    ]


def _synthesis_fields():
    return [
        {'key': 'impression_primary', 'label': 'Primary impression', 'type': 'long_text'},
        {'key': 'clinical_plan', 'label': 'Clinical plan', 'type': 'long_text'},
    ]


EVL_SECTIONS = [
    {
        'id': 'context',
        'title': 'Clinical Context',
        'fields': [
            {'key': 'indication_category', 'label': 'Indication', 'type': 'multi_checkbox',
             'options': ['Acute variceal bleed', 'Secondary prophylaxis', 'Primary prophylaxis', 'Portal hypertensive gastropathy']},
            {'key': 'indication_detail', 'label': 'Indication detail', 'type': 'long_text'},
            {'key': 'urgency', 'label': 'Urgency', 'type': 'dropdown', 'options': _URGENCY},
            {'key': 'consent_obtained', 'label': 'Consent obtained', 'type': 'yes_no'},
        ],
    },
    {
        'id': 'procedure',
        'title': 'EVL Procedure',
        'fields': [
            {'key': 'sedation_type', 'label': 'Sedation', 'type': 'multi_checkbox', 'options': _SEDATION},
            {'key': 'varix_column', 'label': 'Varix column treated', 'type': 'dropdown',
             'options': ['Lower oesophagus', 'Mid oesophagus', 'GO junction', 'Gastric varix (GOV1)', 'Gastric varix (GOV2/IGV)']},
            {'key': 'bands_placed', 'label': 'Number of bands placed', 'type': 'text'},
            {'key': 'active_bleeding', 'label': 'Active bleeding at banding', 'type': 'yes_no'},
            {'key': 'hemostasis_achieved', 'label': 'Haemostasis achieved', 'type': 'yes_no'},
            {'key': 'procedure_detail', 'label': 'Procedure detail', 'type': 'long_text'},
        ],
    },
    {'id': 'closure', 'title': 'Closure & Complications', 'fields': _closure_fields()},
    {'id': 'synthesis', 'title': 'Impression & Plan', 'fields': _synthesis_fields()},
]

SCLEROTHERAPY_SECTIONS = [
    {
        'id': 'context',
        'title': 'Clinical Context',
        'fields': [
            {'key': 'indication_category', 'label': 'Indication', 'type': 'multi_checkbox',
             'options': ['Acute variceal bleed', 'Secondary prophylaxis', 'Gastric varix']},
            {'key': 'indication_detail', 'label': 'Indication detail', 'type': 'long_text'},
            {'key': 'urgency', 'label': 'Urgency', 'type': 'dropdown', 'options': _URGENCY},
            {'key': 'consent_obtained', 'label': 'Consent obtained', 'type': 'yes_no'},
        ],
    },
    {
        'id': 'procedure',
        'title': 'Sclerotherapy',
        'fields': [
            {'key': 'sedation_type', 'label': 'Sedation', 'type': 'multi_checkbox', 'options': _SEDATION},
            {'key': 'target_lesion', 'label': 'Target lesion', 'type': 'text'},
            {'key': 'sclerosant_agent', 'label': 'Sclerosant agent', 'type': 'dropdown',
             'options': ['Ethanolamine oleate', 'Polidocanol', 'Sodium tetradecyl sulfate', 'Cyanoacrylate', 'Other']},
            {'key': 'volume_injected_ml', 'label': 'Volume injected (mL)', 'type': 'text'},
            {'key': 'hemostasis_achieved', 'label': 'Haemostasis achieved', 'type': 'yes_no'},
            {'key': 'procedure_detail', 'label': 'Procedure detail', 'type': 'long_text'},
        ],
    },
    {'id': 'closure', 'title': 'Closure & Complications', 'fields': _closure_fields()},
    {'id': 'synthesis', 'title': 'Impression & Plan', 'fields': _synthesis_fields()},
]

STENT_SECTIONS = [
    {
        'id': 'context',
        'title': 'Clinical Context',
        'fields': [
            {'key': 'indication_category', 'label': 'Indication', 'type': 'multi_checkbox',
             'options': ['Malignant obstruction', 'Benign stricture', 'Leak/fistula', 'Perforation cover']},
            {'key': 'indication_detail', 'label': 'Indication detail', 'type': 'long_text'},
            {'key': 'consent_obtained', 'label': 'Consent obtained', 'type': 'yes_no'},
        ],
    },
    {
        'id': 'procedure',
        'title': 'Stent Placement',
        'fields': [
            {'key': 'sedation_type', 'label': 'Sedation', 'type': 'multi_checkbox', 'options': _SEDATION},
            {'key': 'stent_location', 'label': 'Stent location', 'type': 'dropdown',
             'options': ['Oesophagus', 'Duodenum', 'Colon', 'Biliary (ERCP)', 'Pancreatic duct']},
            {'key': 'stent_type', 'label': 'Stent type', 'type': 'dropdown',
             'options': ['Fully covered SEMS', 'Partially covered SEMS', 'Uncovered SEMS', 'Plastic biliary', 'Plastic pancreatic']},
            {'key': 'stent_diameter_mm', 'label': 'Stent diameter (mm)', 'type': 'text'},
            {'key': 'stent_length_mm', 'label': 'Stent length (mm)', 'type': 'text'},
            {'key': 'deployment_success', 'label': 'Successful deployment', 'type': 'yes_no'},
            {'key': 'procedure_detail', 'label': 'Procedure detail', 'type': 'long_text'},
        ],
    },
    {'id': 'closure', 'title': 'Closure & Complications', 'fields': _closure_fields()},
    {'id': 'synthesis', 'title': 'Impression & Plan', 'fields': _synthesis_fields()},
]

LIVER_BIOPSY_SECTIONS = [
    {
        'id': 'context',
        'title': 'Clinical Context',
        'fields': [
            {'key': 'indication_category', 'label': 'Indication', 'type': 'multi_checkbox',
             'options': ['Chronic liver disease staging', 'Mass lesion', 'Abnormal LFTs', 'Post-transplant', 'TJLB']},
            {'key': 'indication_detail', 'label': 'Indication detail', 'type': 'long_text'},
            {'key': 'consent_obtained', 'label': 'Consent obtained', 'type': 'yes_no'},
        ],
    },
    {
        'id': 'technique',
        'title': 'Biopsy Technique',
        'fields': [
            {'key': 'approach', 'label': 'Approach', 'type': 'dropdown',
             'options': ['EUS-guided', 'Transjugular (TJLB)', 'Percutaneous (referral)']},
            {'key': 'target_lobe', 'label': 'Target lobe/segment', 'type': 'text'},
            {'key': 'needle_type', 'label': 'Needle type', 'type': 'dropdown', 'options': vocab.EUS_NEEDLE},
            {'key': 'pass_count', 'label': 'Number of passes', 'type': 'text'},
            {'key': 'adequate_sample', 'label': 'Adequate sample obtained', 'type': 'yes_no'},
            {'key': 'complications', 'label': 'Immediate complications', 'type': 'long_text'},
        ],
    },
    {'id': 'closure', 'title': 'Closure', 'fields': _closure_fields()},
    {'id': 'synthesis', 'title': 'Impression & Plan', 'fields': _synthesis_fields()},
]
