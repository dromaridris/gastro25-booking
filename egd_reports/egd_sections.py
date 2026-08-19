"""Extra structured sections for EGD — variceal banding, bleeding control, detailed findings."""

from __future__ import annotations

from advanced_reports.gi_vocabulary import vocab_labels

_FORREST = [
    'Type 1a — spurting hemorrhage',
    'Type 1b — oozing hemorrhage',
    'Type 2a — non-bleeding visible vessel',
    'Type 2b — adherent clot',
    'Type 2c — flat pigmented spot',
    'Type 3 — clean base (no stigmata)',
]

_BAVENO = ['Small', 'Medium', 'Large']
_VARIX_COLUMN = [
    'Lower oesophagus',
    'Mid oesophagus',
    'GO junction',
    'Gastric varix GOV1',
    'Gastric varix GOV2 / IGV',
]

_HILL_GRADE = ['Grade I', 'Grade II', 'Grade III', 'Grade IV']

_PHG = ['Mild', 'Moderate', 'Severe']

_FINDINGS = vocab_labels('upper_gi_finding_type') or [
    'Varices',
    'Portal hypertensive gastropathy',
    'Ulcer',
    'Erosion',
    'Hiatus hernia',
    'Fundal varix (IGV)',
    'Gastric varix (GOV)',
    'Duodenopathy',
    'Mass / lesion',
    'Oesophagitis',
    'Barrett oesophagus',
    'Other',
]

_HEMO_METHOD = vocab_labels('upper_gi_intervention_type') or [
    'Injection therapy (adrenaline / sclerosant)',
    'Histoacryl sclerotherapy',
    'Thermal coagulation',
    'Clip placement',
    'Variceal band ligation',
    'APC',
    'OTSC / over-the-scope clip',
    'Combination therapy',
]

_SEDATION_AGENTS = vocab_labels('sedation_type') or [
    'Midazolam',
    'Nalbuphine',
    'Fentanyl',
    'Propofol',
    'Local pharyngeal spray',
    'General anaesthesia',
]

_DIAGNOSIS = [
    'Oesophageal varices',
    'Gastric / fundal varix',
    'Portal hypertensive gastropathy',
    'Gastric ulcer',
    'Duodenal ulcer',
    'Duodenopathy',
    'Hiatus hernia',
    'Oesophagitis',
    'Barrett oesophagus',
    'Upper GI bleeding',
    'Mass / lesion',
    'Normal study',
]

EGD_HEADER_SECTION = {
    'id': 'egd_header',
    'title': 'Referral & Presentation',
    'fields': [
        {'key': 'refer_to', 'label': 'Refer / ward', 'type': 'text', 'placeholder': 'e.g. GI-ward'},
        {'key': 'chief_complaints', 'label': 'Chief complaints', 'type': 'long_text', 'placeholder': 'e.g. Haematemesis and melaena (DCLD/HCV)'},
        {'key': 'sedation_agents', 'label': 'Sedation agents', 'type': 'multi_checkbox', 'options': _SEDATION_AGENTS},
        {'key': 'sedation_regimen', 'label': 'Sedation regimen (doses)', 'type': 'text', 'placeholder': 'e.g. Inj midazolam 2 mg + inj nalbuphine 2 mg'},
    ],
}

EGD_DETAILED_FINDINGS = {
    'id': 'detailed_findings',
    'title': 'Detailed Segmental Findings',
    'fields': [
        {'key': 'hill_grade', 'label': 'Hiatus hernia — Hill grade', 'type': 'dropdown', 'options': _HILL_GRADE},
        {'key': 'stomach_fundus_findings', 'label': 'Fundus — findings', 'type': 'multi_checkbox', 'options': _FINDINGS},
        {'key': 'stomach_fundus_detail', 'label': 'Fundus — detail / therapy', 'type': 'long_text'},
        {'key': 'stomach_body_findings', 'label': 'Body — findings', 'type': 'multi_checkbox', 'options': _FINDINGS},
        {'key': 'stomach_body_detail', 'label': 'Body — detail', 'type': 'long_text'},
        {'key': 'stomach_antrum_findings', 'label': 'Antrum — findings', 'type': 'multi_checkbox', 'options': _FINDINGS},
        {'key': 'stomach_antrum_detail', 'label': 'Antrum — detail', 'type': 'long_text'},
        {'key': 'duodenum_d1_findings', 'label': 'D1 — findings', 'type': 'multi_checkbox', 'options': _FINDINGS},
        {'key': 'duodenum_d1_detail', 'label': 'D1 — detail', 'type': 'long_text'},
        {'key': 'duodenum_d2_findings', 'label': 'D2 — findings', 'type': 'multi_checkbox', 'options': _FINDINGS},
        {'key': 'duodenum_d2_detail', 'label': 'D2 — detail', 'type': 'long_text'},
        {'key': 'phg_severity', 'label': 'Portal hypertensive gastropathy severity', 'type': 'dropdown', 'options': _PHG},
    ],
}

EGD_THERAPY_SECTIONS = [
    {
        'id': 'variceal',
        'title': 'Variceal Band Ligation',
        'fields': [
            {'key': 'variceal_banding_performed', 'label': 'EVBL performed', 'type': 'yes_no', 'compact': True},
            {'key': 'evbl_session', 'label': 'EVBL session', 'type': 'text', 'placeholder': 'e.g. 3rd session'},
            {
                'key': 'variceal_indication',
                'label': 'Indication for banding',
                'type': 'dropdown',
                'options': [
                    'Acute variceal haemorrhage',
                    'Secondary prophylaxis',
                    'Primary prophylaxis (high-risk varices)',
                ],
            },
            {'key': 'variceal_grade', 'label': 'Variceal size (Baveno)', 'type': 'dropdown', 'options': _BAVENO},
            {'key': 'red_wale_markings', 'label': 'Red wale markings', 'type': 'yes_no', 'compact': True},
            {'key': 'varix_column', 'label': 'Varix column / site', 'type': 'dropdown', 'options': _VARIX_COLUMN},
            {'key': 'bands_placed', 'label': 'Bands placed', 'type': 'text'},
            {'key': 'active_bleeding_at_banding', 'label': 'Active bleeding at banding', 'type': 'yes_no', 'compact': True},
            {'key': 'hemostasis_achieved_banding', 'label': 'Haemostasis achieved', 'type': 'yes_no', 'compact': True},
            {'key': 'variceal_banding_detail', 'label': 'Additional EVBL detail', 'type': 'long_text'},
        ],
    },
    {
        'id': 'sclerotherapy',
        'title': 'Sclerotherapy (Histoacryl / Lipiodol)',
        'fields': [
            {'key': 'sclerotherapy_performed', 'label': 'Sclerotherapy performed', 'type': 'yes_no', 'compact': True},
            {'key': 'sclerotherapy_session', 'label': 'Sclerotherapy session', 'type': 'text', 'placeholder': 'e.g. 1st session'},
            {'key': 'sclerotherapy_site', 'label': 'Injection site', 'type': 'text', 'placeholder': 'e.g. Fundal varix IGV-I'},
            {'key': 'sclerotherapy_agent', 'label': 'Sclerosant', 'type': 'text', 'placeholder': 'e.g. Histoacryl 1 cc'},
            {'key': 'sclerotherapy_diluent', 'label': 'Diluent / carrier', 'type': 'text', 'placeholder': 'e.g. Lipiodol 0.5 cc'},
            {'key': 'sclerotherapy_hemostasis', 'label': 'Haemostasis achieved', 'type': 'yes_no', 'compact': True},
            {'key': 'sclerotherapy_detail', 'label': 'Sclerotherapy detail', 'type': 'long_text'},
        ],
    },
    {
        'id': 'bleeding_control',
        'title': 'Bleeding Control / Haemostasis',
        'fields': [
            {'key': 'hemostasis_performed', 'label': 'Haemostasis performed', 'type': 'yes_no', 'compact': True},
            {'key': 'bleeding_source_site', 'label': 'Bleeding source / lesion site', 'type': 'text'},
            {'key': 'forrest_classification', 'label': 'Forrest classification', 'type': 'dropdown', 'options': _FORREST},
            {'key': 'hemostasis_method', 'label': 'Haemostasis method(s)', 'type': 'multi_checkbox', 'options': _HEMO_METHOD},
            {'key': 'hemostasis_success', 'label': 'Immediate haemostasis successful', 'type': 'yes_no', 'compact': True},
            {'key': 'rebleed_during_procedure', 'label': 'Rebleeding during procedure', 'type': 'yes_no', 'compact': True},
            {'key': 'hemostasis_detail', 'label': 'Haemostasis detail', 'type': 'long_text'},
        ],
    },
    {
        'id': 'other_interventions',
        'title': 'Other Therapeutic Interventions',
        'fields': [
            {'key': 'intervention_biopsy', 'label': 'Biopsy', 'type': 'yes_no', 'compact': True},
            {'key': 'biopsy_detail', 'label': 'Biopsy detail', 'type': 'text', 'placeholder': 'e.g. None / Antrum x2'},
            {'key': 'intervention_polypectomy', 'label': 'Polypectomy', 'type': 'yes_no', 'compact': True},
            {'key': 'intervention_dilatation', 'label': 'Dilatation', 'type': 'yes_no', 'compact': True},
            {'key': 'intervention_stent', 'label': 'Stent', 'type': 'yes_no', 'compact': True},
            {'key': 'intervention_peg', 'label': 'PEG', 'type': 'yes_no', 'compact': True},
            {'key': 'intervention_apc', 'label': 'APC', 'type': 'yes_no', 'compact': True},
            {'key': 'intervention_emr_esd', 'label': 'EMR / ESD', 'type': 'yes_no', 'compact': True},
            {'key': 'other_interventions_detail', 'label': 'Other interventions detail', 'type': 'long_text'},
        ],
    },
    {
        'id': 'egd_diagnosis',
        'title': 'Diagnosis (structured)',
        'fields': [
            {'key': 'diagnosis_list', 'label': 'Diagnosis(es)', 'type': 'multi_checkbox', 'options': _DIAGNOSIS},
            {'key': 'diagnosis_detail', 'label': 'Diagnosis detail / free text', 'type': 'long_text'},
        ],
    },
]
