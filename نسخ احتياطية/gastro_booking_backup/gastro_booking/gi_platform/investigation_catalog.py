"""Common investigation / procedure order catalogues for dropdowns."""

COMMON_LABS = [
    ('lab.cbc', 'CBC / Full blood count'),
    ('lab.coagulation', 'Coagulation profile (PT/INR, APTT)'),
    ('lab.lft', 'Liver function tests (LFTs)'),
    ('lab.amylase', 'Serum amylase / lipase'),
    ('lab.crp', 'CRP / ESR'),
    ('lab.renal', 'Urea & electrolytes (U&E)'),
    ('lab.calprotectin', 'Faecal calprotectin'),
    ('lab.h_pylori', 'H. pylori test (stool Ag / breath)'),
    ('lab.afp', 'Alpha-fetoprotein (AFP)'),
    ('lab.inrhbsag', 'Hepatitis B surface antigen'),
    ('lab.hcv_ab', 'Hepatitis C antibody'),
]

COMMON_IMAGING = [
    ('img.us_abdomen', 'Abdominal ultrasound'),
    ('img.ct_abdomen', 'CT abdomen / CT angiography'),
    ('img.mrcp', 'MRCP'),
    ('img.cxr', 'Chest X-ray'),
    ('img.bar_swallow', 'Barium swallow'),
    ('img.bar_enema', 'Barium enema'),
]

COMMON_ENDOSCOPY = [
    ('proc.egd', 'Upper GI endoscopy (EGD)'),
    ('proc.colonoscopy', 'Colonoscopy'),
    ('proc.flex_sig', 'Flexible sigmoidoscopy'),
    ('proc.ercp', 'ERCP'),
    ('proc.eus', 'Endoscopic ultrasound (EUS)'),
    ('proc.capsule', 'Capsule endoscopy'),
]

ORDER_TYPES = (
    ('lab', 'Laboratory', COMMON_LABS),
    ('imaging', 'Imaging', COMMON_IMAGING),
    ('endoscopy', 'Endoscopy / Procedure', COMMON_ENDOSCOPY),
)
