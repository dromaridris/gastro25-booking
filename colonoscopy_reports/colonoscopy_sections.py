"""Extra structured sections for colonoscopy — polypectomy, QI, diagnosis."""

from __future__ import annotations

from advanced_reports.gi_vocabulary import vocab_labels

_FINDINGS = vocab_labels('colonic_finding_type') or [
    'Normal',
    'Polyp',
    'Mass / lesion',
    'Inflammation / colitis',
    'Diverticulosis',
    'Angiodysplasia',
    'Stricture',
    'Other',
]

_INTERVENTIONS = vocab_labels('colonoscopy_intervention_type') or [
    'Biopsy',
    'Polypectomy',
    'EMR',
    'ESD',
    'APC',
    'Injection therapy',
    'Hemostasis',
    'Colonic dilatation',
    'Clip placement',
    'Other',
]

_SEDATION = vocab_labels('sedation_type') or [
    'Midazolam',
    'Nalbuphine',
    'Fentanyl',
    'Propofol',
    'Local pharyngeal spray',
    'General anaesthesia',
]

_POLYP_MORPHOLOGY = ['Paris Ip', 'Paris Is', 'Paris IIa', 'Paris IIb', 'Paris IIc', 'Paris III', 'LST-G', 'LST-NG']

_POLYP_TECHNIQUE = [
    'Cold forceps',
    'Cold snare',
    'Hot snare',
    'EMR',
    'ESD',
    'APC',
]

_DIAGNOSIS = [
    'Normal colonoscopy',
    'Colonic polyp(s) — adenomatous',
    'Colonic polyp(s) — hyperplastic',
    'Colonic mass / lesion',
    'Colonic angiodysplasia',
    'Diverticular disease',
    'Colitis / IBD',
    'Colonic stricture',
    'Incomplete colonoscopy',
    'Post-polypectomy site',
]

COLONOSCOPY_HEADER_SECTION = {
    'id': 'colon_header',
    'title': 'Referral & Presentation',
    'fields': [
        {'key': 'refer_to', 'label': 'Refer / ward', 'type': 'text', 'placeholder': 'e.g. GI-ward'},
        {'key': 'chief_complaints', 'label': 'Chief complaints', 'type': 'long_text'},
        {'key': 'sedation_agents', 'label': 'Sedation agents', 'type': 'multi_checkbox', 'options': _SEDATION},
        {'key': 'sedation_regimen', 'label': 'Sedation regimen (doses)', 'type': 'text',
         'placeholder': 'e.g. Inj midazolam 2 mg + inj nalbuphine 2 mg'},
    ],
}

COLONOSCOPY_THERAPY_SECTIONS = [
    {
        'id': 'polypectomy',
        'title': 'Polypectomy / Resection',
        'fields': [
            {'key': 'polypectomy_performed', 'label': 'Polypectomy performed', 'type': 'yes_no', 'compact': True},
            {'key': 'polyps_resected_count', 'label': 'Polyps resected (number)', 'type': 'text'},
            {'key': 'polypectomy_technique', 'label': 'Technique(s)', 'type': 'multi_checkbox', 'options': _POLYP_TECHNIQUE},
            {'key': 'polypectomy_morphology', 'label': 'Morphology (Paris)', 'type': 'multi_checkbox', 'options': _POLYP_MORPHOLOGY},
            {'key': 'polypectomy_sites', 'label': 'Polypectomy site(s) & size', 'type': 'long_text',
             'placeholder': 'e.g. Ascending 5 mm sessile — cold snare; Sigmoid 12 mm LST — EMR'},
            {'key': 'adenoma_documented', 'label': 'Adenoma documented', 'type': 'yes_no', 'compact': True},
            {'key': 'specimens_to_histology', 'label': 'Specimens to histology', 'type': 'text',
             'placeholder': 'e.g. Jar A x2 polyps ascending + sigmoid'},
            {'key': 'polypectomy_detail', 'label': 'Additional polypectomy detail', 'type': 'long_text'},
        ],
    },
    {
        'id': 'other_interventions',
        'title': 'Other Therapeutic Interventions',
        'fields': [
            {'key': 'intervention_biopsy', 'label': 'Biopsy', 'type': 'yes_no', 'compact': True},
            {'key': 'biopsy_detail', 'label': 'Biopsy detail', 'type': 'text', 'placeholder': 'e.g. Random left colon x2'},
            {'key': 'intervention_emr', 'label': 'EMR', 'type': 'yes_no', 'compact': True},
            {'key': 'intervention_hemostasis', 'label': 'Haemostasis', 'type': 'yes_no', 'compact': True},
            {'key': 'intervention_apc', 'label': 'APC', 'type': 'yes_no', 'compact': True},
            {'key': 'intervention_dilatation', 'label': 'Dilatation', 'type': 'yes_no', 'compact': True},
            {'key': 'intervention_clip', 'label': 'Clip placement', 'type': 'yes_no', 'compact': True},
            {'key': 'hemostasis_method', 'label': 'Haemostasis method(s)', 'type': 'multi_checkbox', 'options': _INTERVENTIONS},
            {'key': 'other_interventions_detail', 'label': 'Other interventions detail', 'type': 'long_text'},
        ],
    },
    {
        'id': 'colon_diagnosis',
        'title': 'Diagnosis (structured)',
        'fields': [
            {'key': 'diagnosis_list', 'label': 'Diagnosis(es)', 'type': 'multi_checkbox', 'options': _DIAGNOSIS},
            {'key': 'diagnosis_detail', 'label': 'Diagnosis detail / free text', 'type': 'long_text'},
        ],
    },
]

COLON_SEGMENT_FINDINGS = _FINDINGS
