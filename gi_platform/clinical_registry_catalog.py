"""Clinical registry card catalog — hospital-facing definitions (not developer inventory)."""

from __future__ import annotations

# Built-in GI disease / syndrome groups shown as dashboard cards.
# New cards are auto-added from gi_history_template and gi_registry_diagnosis.
BUILTIN_DISEASE_GROUPS: list[dict] = [
    {
        'code': 'gi_bleeding',
        'name': 'GI Bleeding',
        'category': 'disease',
        'icon': '🩸',
        'match_terms': ['gi bleed', 'gastrointestinal bleed', 'ugib', 'lgib', 'melena', 'hematemesis'],
        'subtypes': [
            {'code': 'upper_gi_bleed', 'name': 'Upper GI Bleeding', 'match_terms': ['upper gi bleed', 'ugib', 'hematemesis', 'melena']},
            {'code': 'lower_gi_bleed', 'name': 'Lower GI Bleeding', 'match_terms': ['lower gi bleed', 'lgib', 'hematochezia']},
            {'code': 'variceal_bleed', 'name': 'Variceal Bleeding', 'match_terms': ['variceal', 'varices bleed']},
            {'code': 'non_variceal_bleed', 'name': 'Non-variceal Bleeding', 'match_terms': ['non-variceal', 'non variceal', 'peptic ulcer bleed']},
        ],
    },
    {
        'code': 'liver_disease',
        'name': 'Liver Diseases',
        'category': 'disease',
        'icon': '🫀',
        'match_terms': ['liver disease', 'hepatic', 'cirrhosis', 'hepatitis'],
        'subtypes': [
            {'code': 'cirrhosis', 'name': 'Cirrhosis', 'match_terms': ['cirrhosis', 'cirrhotic']},
            {'code': 'hbv', 'name': 'HBV', 'match_terms': ['hbv', 'hepatitis b']},
            {'code': 'hcv', 'name': 'HCV', 'match_terms': ['hcv', 'hepatitis c']},
            {'code': 'nafld', 'name': 'NAFLD', 'match_terms': ['nafld', 'nash', 'fatty liver']},
            {'code': 'autoimmune_hepatitis', 'name': 'Autoimmune Hepatitis', 'match_terms': ['autoimmune hepatitis', 'aih']},
            {'code': 'wilson', 'name': 'Wilson Disease', 'match_terms': ['wilson']},
            {'code': 'pbc', 'name': 'PBC', 'match_terms': ['pbc', 'primary biliary']},
            {'code': 'psc', 'name': 'PSC', 'match_terms': ['psc', 'primary sclerosing']},
        ],
    },
    {
        'code': 'pancreatic_disease',
        'name': 'Pancreatic Diseases',
        'category': 'disease',
        'icon': '🧬',
        'match_terms': ['pancreatitis', 'pancreatic', 'cp', 'acute pancreatitis', 'chronic pancreatitis'],
        'subtypes': [],
    },
    {
        'code': 'ibd',
        'name': 'IBD',
        'category': 'disease',
        'icon': '🔥',
        'match_terms': ['ibd', 'inflammatory bowel', 'colitis', 'crohn'],
        'subtypes': [
            {'code': 'ulcerative_colitis', 'name': 'Ulcerative Colitis', 'match_terms': ['ulcerative colitis', 'uc']},
            {'code': 'crohn', 'name': "Crohn's Disease", 'match_terms': ['crohn', "crohn's"]},
            {'code': 'ibd_active', 'name': 'Active Disease', 'match_terms': ['active ibd', 'flare', 'active disease']},
            {'code': 'ibd_biologics', 'name': 'Patients on Biologics', 'match_terms': ['biologic', 'infliximab', 'adalimumab', 'vedolizumab', 'ustekinumab']},
        ],
    },
    {
        'code': 'hepatobiliary',
        'name': 'Hepatobiliary Diseases',
        'category': 'disease',
        'icon': '🏥',
        'match_terms': ['hepatobiliary', 'biliary', 'choledocholithiasis', 'cholangitis', 'gallstone'],
        'subtypes': [],
    },
]

# Core dashboard cards (non-diagnosis).
CORE_CARDS: list[dict] = [
    {'id': 'patients', 'title': 'Patients', 'icon': '👤', 'category': 'core',
     'endpoint': 'search_patients', 'description': 'Search and open complete patient timelines.'},
    {'id': 'appointments', 'title': 'Appointments', 'icon': '📅', 'category': 'core',
     'endpoint': 'dashboard', 'description': "Today's endoscopy schedule and bookings."},
    {'id': 'admissions', 'title': 'Admissions', 'icon': '🛏️', 'category': 'core',
     'endpoint': 'ward_dashboard', 'description': 'Inpatient ward list and active admissions.'},
]

PROCEDURE_CARDS: list[dict] = [
    {'id': 'upper_gi', 'title': 'Upper GI Endoscopy', 'icon': '🔬', 'category': 'procedure',
     'procedure_keys': ['upper_gi'], 'report_table': 'upper_gi_v2_report',
     'endpoint': 'upper_gi_research_registry'},
    {'id': 'colonoscopy', 'title': 'Colonoscopy', 'icon': '🔭', 'category': 'procedure',
     'procedure_keys': ['colonoscopy'], 'report_table': 'colonoscopy_v2_report',
     'endpoint': 'colonoscopy_research_registry'},
    {'id': 'sigmoidoscopy', 'title': 'Sigmoidoscopy', 'icon': '📋', 'category': 'procedure',
     'procedure_keys': ['sigmoidoscopy'], 'report_table': None},
    {'id': 'ercp', 'title': 'ERCP', 'icon': '🧪', 'category': 'procedure',
     'procedure_keys': ['ercp'], 'report_table': 'ercp_report', 'endpoint': 'ercp_research_registry'},
    {'id': 'esophageal_dilatation', 'title': 'Esophageal Dilatation', 'icon': '⭕', 'category': 'procedure',
     'procedure_keys': ['dilatation', 'esophageal_dilatation', 'balloon_dilatation'],
     'report_table': 'dilatation_report', 'endpoint': 'dilatation_registry'},
    {'id': 'peg', 'title': 'PEG', 'icon': '🍽️', 'category': 'procedure',
     'procedure_keys': ['peg_tube'], 'report_table': 'upper_gi_v2_report',
     'endpoint': 'upper_gi_research_registry'},
]

CLINICAL_MODULE_CARDS: list[dict] = [
    {'id': 'research', 'title': 'Research Registry', 'icon': '📊', 'category': 'module',
     'endpoint': 'gi_research_index'},
    {'id': 'knowledge', 'title': 'Knowledge Library', 'icon': '📚', 'category': 'module',
     'endpoint': 'gi_knowledge_index'},
    {'id': 'encounters', 'title': 'Clinical Encounters', 'icon': '📝', 'category': 'module',
     'endpoint': 'ward_dashboard'},
    {'id': 'laboratory', 'title': 'Laboratory', 'icon': '🧫', 'category': 'module',
     'endpoint': 'ward_dashboard'},
    {'id': 'medications', 'title': 'Medication History', 'icon': '💊', 'category': 'module',
     'endpoint': 'ward_dashboard'},
    {'id': 'followup', 'title': 'Follow-up', 'icon': '🔁', 'category': 'module',
     'endpoint': 'ercp_research_registry'},
    {'id': 'documents', 'title': 'Documents', 'icon': '📄', 'category': 'module',
     'endpoint': 'gi_gov_documents'},
    {'id': 'ai_assistant', 'title': 'AI Clinical Assistant', 'icon': '🤖', 'category': 'module',
     'endpoint': 'ward_dashboard'},
]

CATEGORY_LABELS = {
    'core': 'Department overview',
    'procedure': 'Endoscopy & procedures',
    'disease': 'Disease registries',
    'module': 'Clinical modules',
    'custom': 'Consultant diagnoses',
}
