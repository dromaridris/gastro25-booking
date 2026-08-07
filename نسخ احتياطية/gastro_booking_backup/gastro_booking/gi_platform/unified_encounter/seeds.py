"""Knowledge seeds for known-disease mode — specialty-agnostic structure, GI content first.

Engine code must not hardcode GI logic; extend by adding entries here or via KB.
"""

from __future__ import annotations

# Structure is specialty-agnostic; domain packs supply codes/labels.
KNOWN_DISEASES: list[dict] = [
    {'code': 'dx.cirrhosis', 'label': 'Cirrhosis / chronic liver disease', 'domain': 'gastroenterology'},
    {'code': 'dx.ibd', 'label': 'Inflammatory bowel disease (UC / Crohn)', 'domain': 'gastroenterology'},
    {'code': 'dx.pud', 'label': 'Peptic ulcer disease', 'domain': 'gastroenterology'},
    {'code': 'dx.gerd', 'label': 'GERD / reflux disease', 'domain': 'gastroenterology'},
    {'code': 'dx.chronic_pancreatitis', 'label': 'Chronic pancreatitis', 'domain': 'gastroenterology'},
    {'code': 'dx.cholelithiasis', 'label': 'Gallstone disease', 'domain': 'gastroenterology'},
    {'code': 'dx.celiac', 'label': 'Coeliac disease', 'domain': 'gastroenterology'},
    {'code': 'dx.viral_hepatitis', 'label': 'Chronic viral hepatitis', 'domain': 'gastroenterology'},
    {'code': 'dx.colorectal_cancer', 'label': 'Colorectal neoplasia (known)', 'domain': 'gastroenterology'},
    {'code': 'dx.other', 'label': 'Other known disease (specify in notes)', 'domain': 'general'},
]

# Current clinical problems — not only complications; includes routine follow-up.
CURRENT_PROBLEMS: list[dict] = [
    # maps_complaint → existing ward catalogue codes (knowledge data, not engine hardcoding)
    {'code': 'cp.hematemesis', 'label': 'Hematemesis / vomiting blood', 'maps_complaint': 'hist.upper_gi_bleeding'},
    {'code': 'cp.melena', 'label': 'Melena', 'maps_complaint': 'hist.upper_gi_bleeding'},
    {'code': 'cp.hematochezia', 'label': 'Hematochezia / rectal bleeding', 'maps_complaint': 'hist.lower_gi_bleeding'},
    {'code': 'cp.ascites', 'label': 'Ascites / abdominal distention', 'maps_complaint': 'hist.ascites'},
    {'code': 'cp.fever', 'label': 'Fever', 'maps_complaint': 'hist.chronic_liver_disease'},
    {'code': 'cp.confusion', 'label': 'Confusion / altered mental status', 'maps_complaint': 'hist.chronic_liver_disease'},
    {'code': 'cp.jaundice', 'label': 'Jaundice', 'maps_complaint': 'hist.jaundice'},
    {'code': 'cp.new_pain', 'label': 'New or worsening pain', 'maps_complaint': 'hist.abdominal_pain'},
    {'code': 'cp.weight_loss', 'label': 'Weight loss', 'maps_complaint': 'hist.weight_loss'},
    {'code': 'cp.diarrhea', 'label': 'Diarrhea / loose stools', 'maps_complaint': 'hist.loose_stools'},
    {'code': 'cp.vomiting', 'label': 'Vomiting / nausea', 'maps_complaint': 'hist.vomiting'},
    {'code': 'cp.routine_followup', 'label': 'Routine follow-up / stable review', 'maps_complaint': 'hist.chronic_liver_disease'},
    {'code': 'cp.other', 'label': 'Other current problem', 'maps_complaint': 'hist.abdominal_pain'},
]

# Complaint-category → ODPARA template family (not disease names).
PAIN_LIKE_TOKENS = (
    'pain', 'ache', 'dysuria', 'heartburn', 'chest', 'flank', 'anal', 'back', 'headache',
)
BLEED_TOKENS = ('hematemesis', 'melena', 'hematochezia', 'bleed', 'hemoptysis', 'hematuria')

# Shared choice catalogues (knowledge data — engines must consume these, not invent options).
ONSET_TIMING_CHOICES = ['Hours', 'Days', 'Weeks', 'Months', 'Years']
ONSET_PATTERN_CHOICES = ['Sudden', 'Gradual', 'Unclear']
COURSE_CHOICES = ['Improving', 'Stable', 'Worsening', 'Fluctuating', 'Intermittent']
SEVERITY_CHOICES = ['Mild', 'Moderate', 'Severe', 'Life-threatening / incapacitating']
PAIN_SITE_CHOICES = [
    'Epigastric', 'RUQ', 'LUQ', 'Periumbilical', 'RLQ', 'LLQ', 'Diffuse', 'Flank', 'Other',
]
PAIN_RADIATION_CHOICES = ['None', 'To back', 'To shoulder', 'To groin', 'To chest', 'Other']
PAIN_CHARACTER_CHOICES = [
    'Dull / aching', 'Sharp / stabbing', 'Colicky', 'Burning', 'Pressure / tightness', 'Other',
]
AGGRAVATING_CHOICES = [
    'None clear', 'Food', 'Hunger / empty stomach', 'Movement', 'Lying flat', 'Breathing', 'Other',
]
RELIEVING_CHOICES = [
    'Nothing', 'Antacids / PPI', 'Food', 'Vomiting', 'Position change', 'Analgesia', 'Other',
]
BLEED_VOLUME_CHOICES = [
    'Spotting / streaks', 'Cupful', 'Large / bowlful', 'Unknown / mixed with stool or vomit',
]
SYSTEMIC_CHOICES = ['None', 'Fever', 'Weight loss', 'Both', 'Unknown']
PRIOR_EPISODE_CHOICES = ['First episode', 'Recurrent similar', 'Chronic ongoing', 'Unknown']
YES_NO_UNKNOWN = ['Yes', 'No', 'Unknown']
ASSOCIATED_SYMPTOM_CHOICES = [
    'Nausea', 'Vomiting', 'Diarrhea', 'Constipation', 'Fever', 'Anorexia',
    'Jaundice', 'Dark urine', 'Pale stools', 'Heartburn', 'Dysphagia',
    'Melena', 'Hematochezia', 'Weight loss', 'None of these', 'Other',
]
FREQUENCY_CHOICES = [
    'Constant', 'Several times daily', 'Daily', 'Several times weekly', 'Weekly or less', 'Unclear',
]
CONTEXT_SETTING_CHOICES = [
    'At rest', 'After meals', 'After exertion', 'After alcohol', 'After medication',
    'Post-procedure', 'No clear trigger', 'Other',
]
TREATMENTS_TRIED_CHOICES = [
    'None', 'Antacids / PPI', 'Analgesia', 'Antibiotics', 'IV fluids / hospital care',
    'Home remedies', 'Other',
]

# ODPARA / SOCRATES characterization banks by family (suffix → question template).
# answer_type preference order for UI: choice → multi_choice → boolean → numeric → date → text(other only).
CHARACTERIZATION_BANKS: dict[str, list[dict]] = {
    'common': [
        {
            'suffix': 'onset_timing',
            'prompt': 'When did {symptom} start?',
            'answer_type': 'choice',
            'choices': ONSET_TIMING_CHOICES,
            'help_text': 'Onset timing classifies acute vs chronic course and urgency (ODPARA — Onset).',
        },
        {
            'suffix': 'onset_date',
            'prompt': 'Exact onset date (if known)?',
            'answer_type': 'date',
            'choices': [],
            'help_text': 'Precise date anchors timeline for investigations and prior episodes.',
            'optional': True,
        },
        {
            'suffix': 'onset_pattern',
            'prompt': 'Was the onset sudden or gradual?',
            'answer_type': 'choice',
            'choices': ONSET_PATTERN_CHOICES,
            'help_text': 'Sudden onset raises vascular, perforation, and catastrophic differentials.',
        },
        {
            'suffix': 'course',
            'prompt': 'How has it progressed since onset?',
            'answer_type': 'choice',
            'choices': COURSE_CHOICES,
            'help_text': 'Progression informs severity and need for urgent work-up (ODPARA — Progress).',
        },
        {
            'suffix': 'severity',
            'prompt': 'How severe is it now?',
            'answer_type': 'choice',
            'choices': SEVERITY_CHOICES,
            'help_text': 'Severity guides resuscitation priority and red-flag thresholds (ODPARA — Severity).',
        },
        {
            'suffix': 'severity_score',
            'prompt': 'Pain/symptom score 0–10 (if applicable)?',
            'answer_type': 'numeric',
            'choices': [],
            'help_text': 'Numeric severity supports longitudinal comparison and triage.',
            'min': 0,
            'max': 10,
            'unit': '/10',
            'optional': True,
        },
    ],
    'pain': [
        {
            'suffix': 'site',
            'prompt': 'Where is the pain mainly located?',
            'answer_type': 'choice',
            'choices': PAIN_SITE_CHOICES,
            'help_text': 'Site narrows organ-system hypotheses (SOCRATES — Site).',
            'allow_other': True,
        },
        {
            'suffix': 'radiation',
            'prompt': 'Does the pain radiate?',
            'answer_type': 'choice',
            'choices': PAIN_RADIATION_CHOICES,
            'help_text': 'Radiation patterns help separate biliary, pancreatic, renal, and cardiac mimics.',
            'allow_other': True,
        },
        {
            'suffix': 'character',
            'prompt': 'What is the character of the pain?',
            'answer_type': 'choice',
            'choices': PAIN_CHARACTER_CHOICES,
            'help_text': 'Character supports visceral vs peritoneal vs neuropathic patterns (SOCRATES — Character).',
            'allow_other': True,
        },
        {
            'suffix': 'aggravating',
            'prompt': 'What makes it worse? (select all that apply)',
            'answer_type': 'multi_choice',
            'choices': AGGRAVATING_CHOICES,
            'help_text': 'Aggravating factors discriminate ulcer, peritoneal, and musculoskeletal pain.',
            'allow_other': True,
        },
        {
            'suffix': 'relieving',
            'prompt': 'What relieves it? (select all that apply)',
            'answer_type': 'multi_choice',
            'choices': RELIEVING_CHOICES,
            'help_text': 'Relieving factors refine ulcer vs biliary vs functional patterns.',
            'allow_other': True,
        },
    ],
    'bleed': [
        {
            'suffix': 'volume',
            'prompt': 'Estimated volume of blood loss?',
            'answer_type': 'choice',
            'choices': BLEED_VOLUME_CHOICES,
            'help_text': 'Volume estimate drives resuscitation and endoscopy urgency.',
        },
        {
            'suffix': 'hemodynamic',
            'prompt': 'Any syncope, dizziness on standing, or shock features?',
            'answer_type': 'boolean',
            'choices': YES_NO_UNKNOWN,
            'help_text': 'Hemodynamic compromise is a must-not-miss red flag in GI bleeding.',
        },
        {
            'suffix': 'anticoag',
            'prompt': 'On anticoagulant, antiplatelet, or NSAID?',
            'answer_type': 'boolean',
            'choices': YES_NO_UNKNOWN,
            'help_text': 'Drug exposure changes bleed source likelihood and reversal needs.',
        },
    ],
    'general': [
        {
            'suffix': 'associated_pain',
            'prompt': 'Is there associated pain?',
            'answer_type': 'boolean',
            'choices': YES_NO_UNKNOWN,
            'help_text': 'Associated pain links constitutional or luminal symptoms to local pathology.',
        },
        {
            'suffix': 'systemic',
            'prompt': 'Fever, night sweats, or unintentional weight loss?',
            'answer_type': 'choice',
            'choices': SYSTEMIC_CHOICES,
            'help_text': 'Systemic features raise infection, inflammation, and malignancy hypotheses.',
        },
        {
            'suffix': 'temperature',
            'prompt': 'Highest recorded temperature (°C), if febrile?',
            'answer_type': 'numeric',
            'choices': [],
            'help_text': 'Documented fever height supports infectious vs inflammatory differentials.',
            'min': 35,
            'max': 42,
            'step': 0.1,
            'unit': '°C',
            'optional': True,
        },
    ],
    'shared_tail': [
        {
            'suffix': 'associated_symptoms',
            'prompt': 'Associated symptoms? (select all that apply)',
            'answer_type': 'multi_choice',
            'choices': ASSOCIATED_SYMPTOM_CHOICES,
            'help_text': 'Associated symptoms refine the differential before discriminating questions.',
            'allow_other': True,
        },
        {
            'suffix': 'frequency',
            'prompt': 'How often does it occur?',
            'answer_type': 'choice',
            'choices': FREQUENCY_CHOICES,
            'help_text': 'Frequency distinguishes constant inflammatory pain from episodic colic.',
        },
        {
            'suffix': 'prior_similar',
            'prompt': 'Has this happened before?',
            'answer_type': 'choice',
            'choices': PRIOR_EPISODE_CHOICES,
            'help_text': 'Prior episodes suggest chronic disease packs vs first presentation.',
        },
        {
            'suffix': 'weight_change_kg',
            'prompt': 'Unintentional weight change (kg), if any? (0 if none)',
            'answer_type': 'numeric',
            'choices': [],
            'help_text': 'Quantified weight loss is an alarm feature across presenting complaints.',
            'min': -50,
            'max': 50,
            'step': 0.5,
            'unit': 'kg',
            'optional': True,
        },
        {
            'suffix': 'redflag_weight',
            'prompt': 'Unintentional weight loss?',
            'answer_type': 'boolean',
            'choices': YES_NO_UNKNOWN,
            'help_text': 'Weight loss is an alarm feature across many presenting complaints.',
        },
    ],
}

# Deduplicate keys for KB question library patches (characterization / discrimination).
KB_STRUCTURED_PATCHES: dict[str, dict] = {
    'Q000002': {
        'answer_type': 'choice',
        'choices': ONSET_TIMING_CHOICES,
    },
    'Q000004': {
        'answer_type': 'choice',
        'choices': PAIN_SITE_CHOICES,
        'allow_other': True,
    },
    'Q000005': {
        'answer_type': 'choice',
        'choices': PAIN_RADIATION_CHOICES,
        'allow_other': True,
    },
    'Q000006': {
        'answer_type': 'choice',
        'choices': PAIN_CHARACTER_CHOICES,
        'allow_other': True,
    },
    'Q000007': {
        'answer_type': 'numeric',
        'choices': [],
        'min': 0,
        'max': 10,
        'unit': '/10',
    },
    'Q000009': {
        'answer_type': 'choice',
        'choices': ONSET_TIMING_CHOICES,
    },
    'Q000010': {
        'answer_type': 'choice',
        'choices': FREQUENCY_CHOICES,
    },
    'Q000011': {
        'answer_type': 'multi_choice',
        'choices': AGGRAVATING_CHOICES,
        'allow_other': True,
    },
    'Q000012': {
        'answer_type': 'multi_choice',
        'choices': RELIEVING_CHOICES,
        'allow_other': True,
    },
    'Q000015': {
        'answer_type': 'choice',
        'choices': CONTEXT_SETTING_CHOICES,
        'allow_other': True,
    },
    'Q000016': {
        'answer_type': 'multi_choice',
        'choices': TREATMENTS_TRIED_CHOICES,
        'allow_other': True,
    },
    'Q000047': {
        'answer_type': 'choice',
        'choices': ['1–3 / day', '4–6 / day', '7–10 / day', '>10 / day', '<3 / week', 'Variable'],
    },
    'Q000048': {
        'answer_type': 'choice',
        'choices': [
            'Watery (Bristol 7)', 'Loose (Bristol 6)', 'Soft (Bristol 5)',
            'Formed (Bristol 3–4)', 'Hard lumps (Bristol 1–2)', 'Variable',
        ],
    },
    'Q000056': {
        'answer_type': 'choice',
        'choices': ['Neck / oropharyngeal', 'Mid-chest', 'Lower chest / epigastric', 'No sticking', 'Unclear'],
    },
    'Q000060': {
        'answer_type': 'choice',
        'choices': FREQUENCY_CHOICES,
    },
    'Q000061': {
        'answer_type': 'choice',
        'choices': ['Good response', 'Partial response', 'No response', 'Not tried', 'Unknown'],
    },
    'Q000062': {
        'answer_type': 'choice',
        'choices': ['With pain', 'With fever', 'Painless / asymptomatic', 'Mixed', 'Unknown'],
    },
    'Q000063': {
        'answer_type': 'multi_choice',
        'choices': [
            'None known', 'Chronic liver disease / cirrhosis', 'Viral hepatitis',
            'Heavy alcohol use', 'Metabolic / fatty liver', 'Other',
        ],
        'allow_other': True,
    },
    'Q000066': {
        'answer_type': 'multi_choice',
        'choices': ['None', 'Arm', 'Jaw', 'Back', 'Neck', 'Other'],
        'allow_other': True,
    },
    'Q000068': {
        'answer_type': 'choice',
        'choices': ['Worse with breathing', 'Worse with position', 'Both', 'Neither', 'Unclear'],
    },
    'Q000070': {
        'answer_type': 'choice',
        'choices': ['At rest', 'With exertion', 'Orthopnea / PND', 'Mixed', 'Unclear'],
    },
    'Q000071': {
        'answer_type': 'choice',
        'choices': ['Wheeze only', 'Known asthma/COPD', 'Both', 'Neither', 'Unknown'],
    },
    'Q000085': {
        'answer_type': 'choice',
        'choices': ['Never', 'Former', 'Current — light', 'Current — heavy', 'Unknown'],
    },
    'Q000086': {
        'answer_type': 'choice',
        'choices': ['None', 'Occasional', 'Regular', 'Heavy', 'Unknown'],
    },
    'Q000087': {
        'answer_type': 'choice',
        'choices': ['None', 'Past use', 'Current use', 'Unknown'],
    },
    # Free-text retained only where narrative verbatim / open lists are intentional:
    # Q000001 chief complaint words, Q000078 PMH list, Q000080 surgeries, Q000081 meds,
    # Q000083 allergy detail, Q000084 FH, Q000088 occupation, Q000089 support, Q000090 ROS other.
}

# Extra diagnosis priors (knowledge) so Stage 3 is never empty after characterization.
DIAGNOSIS_PRIOR_SEEDS: list[dict] = [
    {
        'complaint_code': 'hist.abdominal_pain',
        'items': [
            ('Peptic ulcer disease', 'most_likely', 0.75),
            ('Biliary colic / choledocholithiasis', 'important_alternative', 0.55),
            ('Acute pancreatitis', 'must_not_miss', 0.5),
            ('Mesenteric ischaemia', 'must_not_miss', 0.35),
            ('Functional dyspepsia / IBS', 'important_alternative', 0.4),
        ],
    },
    {
        'complaint_code': 'hist.upper_gi_bleeding',
        'items': [
            ('Peptic ulcer bleeding', 'most_likely', 0.8),
            ('Variceal haemorrhage', 'must_not_miss', 0.55),
            ('Mallory–Weiss tear', 'important_alternative', 0.45),
            ('Malignancy-related bleed', 'important_alternative', 0.35),
        ],
    },
    {
        'complaint_code': 'hist.lower_gi_bleeding',
        'items': [
            ('Diverticular bleed', 'most_likely', 0.7),
            ('Colonic angiodysplasia', 'important_alternative', 0.5),
            ('Colorectal neoplasia', 'must_not_miss', 0.45),
            ('Inflammatory colitis', 'important_alternative', 0.4),
        ],
    },
    {
        'complaint_code': 'hist.diarrhea',
        'items': [
            ('Infectious gastroenteritis', 'most_likely', 0.7),
            ('IBD flare', 'important_alternative', 0.5),
            ('Medication / antibiotic-associated', 'important_alternative', 0.45),
            ('Malabsorption', 'important_alternative', 0.35),
        ],
    },
    {
        'complaint_code': 'hist.loose_stools',
        'items': [
            ('Infectious gastroenteritis', 'most_likely', 0.7),
            ('IBD flare', 'important_alternative', 0.5),
            ('Medication / antibiotic-associated', 'important_alternative', 0.45),
        ],
    },
    {
        'complaint_code': 'hist.jaundice',
        'items': [
            ('Obstructive jaundice', 'most_likely', 0.7),
            ('Hepatocellular jaundice', 'important_alternative', 0.55),
            ('Haemolytic jaundice', 'important_alternative', 0.35),
            ('Drug-induced liver injury', 'must_not_miss', 0.4),
        ],
    },
    {
        'complaint_code': 'hist.dysphagia',
        'items': [
            ('Structural oesophageal lesion', 'most_likely', 0.65),
            ('Motility disorder', 'important_alternative', 0.5),
            ('Oesophagitis / stricture', 'important_alternative', 0.45),
        ],
    },
    {
        'complaint_code': 'hist.abdominal_distension',
        'items': [
            ('Ascites (portal hypertension)', 'most_likely', 0.65),
            ('Bowel obstruction', 'must_not_miss', 0.55),
            ('Constipation / faecal loading', 'important_alternative', 0.4),
            ('Organomegaly / mass', 'important_alternative', 0.35),
        ],
    },
    {
        'complaint_code': 'hist.ascites',
        'items': [
            ('Cirrhotic ascites', 'most_likely', 0.75),
            ('Malignant ascites', 'must_not_miss', 0.45),
            ('Cardiac ascites', 'important_alternative', 0.4),
        ],
    },
    {
        'complaint_code': 'hist.heartburn',
        'items': [
            ('GERD', 'most_likely', 0.75),
            ('Peptic ulcer disease', 'important_alternative', 0.45),
            ('Cardiac ischaemia (mimic)', 'must_not_miss', 0.4),
        ],
    },
    {
        'complaint_code': 'hist.vomiting',
        'items': [
            ('Gastroenteritis', 'most_likely', 0.6),
            ('Gastric outlet obstruction', 'must_not_miss', 0.45),
            ('Medication / metabolic cause', 'important_alternative', 0.4),
            ('Raised intracranial pressure (mimic)', 'must_not_miss', 0.3),
        ],
    },
    {
        'complaint_code': 'hist.hematemesis',
        'items': [
            ('Peptic ulcer bleeding', 'most_likely', 0.75),
            ('Variceal haemorrhage', 'must_not_miss', 0.55),
            ('Mallory–Weiss tear', 'important_alternative', 0.45),
        ],
    },
    {
        'complaint_code': 'hist.melena',
        'items': [
            ('Upper GI bleeding source', 'most_likely', 0.8),
            ('Small-bowel bleed', 'important_alternative', 0.4),
            ('Right colonic bleed', 'important_alternative', 0.35),
        ],
    },
    {
        'complaint_code': 'hist.constipation',
        'items': [
            ('Functional constipation', 'most_likely', 0.6),
            ('Medication-induced', 'important_alternative', 0.5),
            ('Obstructing lesion', 'must_not_miss', 0.4),
        ],
    },
    {
        'complaint_code': 'hist.fever',
        'items': [
            ('Infectious cause — systemic', 'most_likely', 0.6),
            ('Intra-abdominal sepsis', 'must_not_miss', 0.5),
            ('Drug fever', 'important_alternative', 0.3),
        ],
    },
]

# Disease-contextual question banks (MCQ) keyed by known disease code.
DISEASE_CONTEXT_QUESTIONS: dict[str, list[dict]] = {
    'dx.cirrhosis': [
        {
            'code': 'kd.cirrhosis.decomp',
            'prompt': 'Any new decompensation features (ascites, encephalopathy, jaundice, bleed)?',
            'answer_type': 'choice',
            'choices': ['None', 'Ascites', 'Encephalopathy', 'Jaundice', 'Bleed', 'Multiple'],
            'help_text': 'Decompensation changes urgency and differential of the current problem.',
        },
        {
            'code': 'kd.cirrhosis.beta_blocker',
            'prompt': 'Is the patient on non-selective beta-blocker for varices?',
            'answer_type': 'boolean',
            'choices': ['Yes', 'No', 'Unknown'],
            'help_text': 'Affects bleeding risk management and hemodynamic interpretation.',
        },
    ],
    'dx.ibd': [
        {
            'code': 'kd.ibd.activity',
            'prompt': 'Current IBD disease activity vs baseline?',
            'answer_type': 'choice',
            'choices': ['Quiescent', 'Mild flare', 'Moderate–severe flare', 'Unknown'],
            'help_text': 'Frames whether the current problem is flare-related or a new process.',
        },
        {
            'code': 'kd.ibd.steroids',
            'prompt': 'Recent systemic corticosteroids or biologics?',
            'answer_type': 'boolean',
            'choices': ['Yes', 'No', 'Unknown'],
            'help_text': 'Infection risk and severity of presentation.',
        },
    ],
    'dx.pud': [
        {
            'code': 'kd.pud.nsaid',
            'prompt': 'Ongoing NSAID / aspirin / anticoagulant use?',
            'answer_type': 'boolean',
            'choices': ['Yes', 'No', 'Unknown'],
            'help_text': 'Key risk for ulcer recurrence and bleeding.',
        },
    ],
    'dx.gerd': [
        {
            'code': 'kd.gerd.alarm',
            'prompt': 'Any alarm features (dysphagia, weight loss, anaemia, GI bleed)?',
            'answer_type': 'boolean',
            'choices': ['Yes', 'No', 'Unknown'],
            'help_text': 'Alarm features shift from routine reflux care to urgent evaluation.',
        },
    ],
}

# Default exam systems (specialty-agnostic checklist shells).
DEFAULT_EXAM_SYSTEMS: list[dict] = [
    {
        'key': 'general',
        'title': 'General',
        'items': [
            'Looks well / comfortable',
            'Distress / toxic appearance',
            'Fever / hypothermia',
            'Tachycardia',
            'Hypotension / shock',
            'Pallor',
            'Jaundice / icterus',
            'Lymphadenopathy',
            'Dehydration',
        ],
    },
    {
        'key': 'abdomen',
        'title': 'Abdomen',
        'items': [
            'Soft, non-tender',
            'Tenderness — localized',
            'Tenderness — generalized',
            'Guarding / rigidity',
            'Rebound tenderness',
            'Distension / ascites',
            'Organomegaly (liver / spleen)',
            'Mass palpable',
            'Bowel sounds absent / tinkling',
            'Hernial orifices abnormal',
        ],
    },
    {
        'key': 'cardiorespiratory',
        'title': 'Cardiorespiratory',
        'items': [
            'Heart sounds normal',
            'Murmur',
            'Crackles / reduced air entry',
            'Wheeze',
            'Peripheral oedema',
        ],
    },
    {
        'key': 'neuro',
        'title': 'Neurological (focused)',
        'items': [
            'Alert / oriented',
            'Confusion / encephalopathy signs',
            'Focal deficit',
            'Asterixis',
        ],
    },
    {
        'key': 'rectal',
        'title': 'PR / perianal (if indicated)',
        'items': [
            'Not performed',
            'Melena on glove',
            'Fresh blood',
            'Mass / lesion',
            'Normal PR',
        ],
    },
]
