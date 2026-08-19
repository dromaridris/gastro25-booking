"""Controlled vocabulary for advanced endoscopy reports (from gi_import seeds)."""

from __future__ import annotations


def _labels(items):
    return [label for _code, label, _order in items]


def _choices(items):
    return [(code, label) for code, label, _order in items]


YES_NO = ['Yes', 'No']

PROCEDURE_URGENCY = _labels([
    ('elective', 'Elective', 10),
    ('urgent', 'Urgent (< 72 hours)', 20),
    ('emergency', 'Emergency', 30),
])

ANTICOAGULATION_STATUS = _labels([
    ('none', 'None', 10),
    ('antiplatelet', 'Antiplatelet therapy', 20),
    ('anticoagulant', 'Anticoagulant therapy', 30),
    ('both', 'Antiplatelet and anticoagulant', 40),
])

SEDATION_TYPE = _labels([
    ('local_spray', 'Local pharyngeal spray', 10),
    ('midazolam', 'Midazolam', 20),
    ('propofol', 'Propofol', 30),
    ('fentanyl', 'Fentanyl', 40),
    ('general_anaesthesia', 'General anaesthesia', 50),
])

# Matches ERCP SEDATION_OPTIONS in app.py — used for EUS and other sedated advanced reports.
ERCP_SEDATION = [
    'Moderate Sedation (Conscious Sedation)',
    'Deep Sedation',
    'General Anesthesia',
    'None',
]

SCOPE_NEGOTIATION = ['Easy', 'Mild difficulty', 'Moderate difficulty', 'Difficult', 'Very difficult']

STANDARD_COMPLICATIONS = _labels([
    ('bleeding', 'Bleeding', 10),
    ('perforation', 'Perforation', 20),
    ('aspiration', 'Aspiration', 30),
    ('cardiorespiratory', 'Cardiorespiratory event', 40),
    ('pancreatitis', 'Post-procedure pancreatitis', 50),
    ('other', 'Other', 99),
])

BOWEL_PREP = _labels([
    ('clear_liquid', 'Clear liquid diet', 10),
    ('peg', 'PEG-based prep', 20),
    ('picosulfate', 'Sodium picosulfate', 30),
    ('other', 'Other', 99),
])

EUS_INDICATION = _labels([
    ('pancreatic_mass', 'Pancreatic mass / lesion', 10),
    ('biliary_stricture', 'Biliary stricture', 20),
    ('submucosal_lesion', 'Submucosal lesion', 30),
    ('staging', 'Cancer staging', 40),
    ('cystic_lesion', 'Cystic lesion', 50),
    ('other', 'Other / specify in detail', 99),
])

EUS_SCOPE = _labels([('linear', 'Linear echoendoscope', 10), ('radial', 'Radial echoendoscope', 20)])
EUS_FREQUENCY = _labels([('5mhz', '5 MHz', 10), ('7_5mhz', '7.5 MHz', 20), ('10mhz', '10 MHz', 30), ('12mhz', '12 MHz', 40)])
EUS_ORGAN = _labels([
    ('pancreas', 'Pancreas', 10), ('bile_duct', 'Bile duct', 20),
    ('mediastinum', 'Mediastinum', 30), ('rectum', 'Rectum', 40), ('other', 'Other', 99),
])
EUS_ECHO_LAYER = _labels([
    ('mucosa', 'Mucosa', 10), ('submucosa', 'Submucosa', 20),
    ('muscularis', 'Muscularis propria', 30), ('serosa', 'Serosa / adventitia', 40),
    ('extramural', 'Extramural', 50),
])
EUS_NEEDLE = _labels([
    ('fna_22g', 'FNA 22G', 10), ('fnb_22g', 'FNB 22G', 20),
    ('fnb_25g', 'FNB 25G', 30), ('core_biopsy', 'Core biopsy needle', 40),
])
EUS_CYTOLOGY = _labels([('adequate', 'Adequate', 10), ('inadequate', 'Inadequate', 20), ('pending', 'Pending', 30)])
EUS_T_STAGE = _labels([
    ('tx', 'Tx', 10), ('t0', 'T0', 20), ('t1', 'T1', 30), ('t2', 'T2', 40),
    ('t3', 'T3', 50), ('t4', 'T4', 60), ('not_applicable', 'Not applicable', 99),
])
EUS_FINDING = _labels([
    ('normal', 'Normal', 10), ('mass', 'Mass', 20), ('cyst', 'Cyst', 30),
    ('chronic_pancreatitis', 'Chronic pancreatitis', 40), ('stone', 'Stone', 50),
    ('lymphadenopathy', 'Lymphadenopathy', 60), ('other', 'Other', 99),
])

CAPSULE_INDICATION = _labels([
    ('obscure_bleeding', 'Obscure GI bleeding', 10),
    ('crohn_surveillance', 'Crohn disease surveillance', 20),
    ('polyposis', 'Polyposis syndrome', 30),
    ('malabsorption', 'Malabsorption / diarrhoea', 40),
    ('other', 'Other / specify in detail', 99),
])
CAPSULE_COMPLETION = _labels([
    ('complete', 'Complete study', 10),
    ('incomplete_gastric', 'Incomplete — retained in stomach', 20),
    ('incomplete_small_bowel', 'Incomplete — small bowel not fully visualized', 30),
])
CAPSULE_TYPE = _labels([
    ('standard', 'Standard video capsule', 10),
    ('patency', 'Patency capsule (prior)', 20),
    ('panenteric', 'Pan-enteric capsule', 30),
])
CAPSULE_RETENTION = _labels([('low', 'Low', 10), ('moderate', 'Moderate', 20), ('high', 'High', 30)])
CAPSULE_FINDING = _labels([
    ('normal', 'Normal', 10), ('erosion', 'Erosion / ulceration', 20),
    ('angioectasia', 'Angioectasia', 30), ('mass', 'Mass / polyp', 40),
    ('stricture', 'Stricture', 50), ('blood', 'Active bleeding', 60), ('other', 'Other', 99),
])
