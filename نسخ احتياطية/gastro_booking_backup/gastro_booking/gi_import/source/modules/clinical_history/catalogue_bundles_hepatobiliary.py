"""Hepatobiliary complaint intelligence bundles."""

from app.modules.clinical_history.catalogue_bundle_common import common_context_rules, targets

JAUND_DIAGNOSES = [
    ("dx.obstructive_cholestasis", "Obstructive cholestasis", "hepatology", "kl.jaundice.obstructive"),
    ("dx.alcoholic_hepatitis", "Alcoholic hepatitis", "hepatology", "kl.jaundice.alcoholic_hepatitis"),
    ("dx.dili", "Drug-induced liver injury", "hepatology", "kl.jaundice.dili"),
    ("dx.hemolysis", "Haemolytic jaundice", "hepatology", "kl.jaundice.hemolysis"),
    ("dx.pancreatic_head_cancer", "Pancreatic head malignancy", "hepatology", "kl.jaundice.pancreatic_cancer"),
    ("dx.primary_biliary_cholangitis", "Primary biliary cholangitis", "hepatology", "kl.jaundice.pbc"),
]

JAUND_QUESTIONS = [
    ("q.jaund.pain", "Associated right upper quadrant pain?", "presenting", "boolean", None, False,
     "Biliary obstruction vs painless obstructive cancer", "supports"),
    ("q.jaund.dark_urine", "Dark urine?", "presenting", "boolean", None, False,
     "Conjugated hyperbilirubinaemia", "supports"),
    ("q.jaund.pale_stool", "Pale stools?", "presenting", "boolean", None, False,
     "Choledoch obstruction pattern", "supports"),
    ("q.jaund.fever", "Fever or rigors?", "presenting", "boolean", None, False,
     "Cholangitis until excluded", "alarm"),
    ("q.jaund.itch", "Generalised pruritus?", "presenting", "boolean", None, False,
     "Cholestatic pattern", "supports"),
    ("q.jaund.weight_loss", "Unintentional weight loss?", "alarm", "boolean", None, True,
     "Malignancy alarm", "alarm"),
    ("q.jaund.alcohol", "Heavy alcohol use?", "presenting", "boolean", None, False,
     "Alcoholic hepatitis", "risk_factor"),
    ("q.jaund.new_drugs", "New medication within past 8 weeks?", "presenting", "boolean", None, False,
     "DILI", "risk_factor"),
    ("q.jaund.travel", "Recent travel or IV drug use?", "exclusion", "boolean", None, True,
     "Viral hepatitis risk", "risk_factor"),
    ("q.jaund.acholic_duration", "Progressive jaundice over weeks?", "alarm", "boolean", None, True,
     "Structural obstruction or chronic cholestasis", "alarm"),
    ("q.jaund.encephalopathy", "Confusion or asterixis?", "alarm", "boolean", None, True,
     "Acute liver failure / decompensation", "alarm"),
    ("q.jaund.joint_pain", "Joint pains or rash?", "presenting", "boolean", None, False,
     "Autoimmune hepatitis overlap", "supports"),
]

JAUND_PRIORS = [
    ("hist.jaundice", "dx.cholelithiasis", 1.5),
    ("hist.jaundice", "dx.obstructive_cholestasis", 1.2),
    ("hist.jaundice", "dx.viral_hepatitis", 1.0),
    ("hist.jaundice", "dx.alcoholic_hepatitis", 0.7),
    ("hist.jaundice", "dx.dili", 0.6),
    ("hist.jaundice", "dx.hemolysis", 0.4),
    ("hist.jaundice", "dx.pancreatic_head_cancer", 0.5),
    ("hist.jaundice", "dx.primary_biliary_cholangitis", 0.4),
]

JAUND_WEIGHT_RULES = [
    ("hist.jaundice", "q.jaund.pain", "yes", "dx.cholelithiasis", 2.5),
    ("hist.jaundice", "q.jaund.pain", "no", "dx.pancreatic_head_cancer", 1.5),
    ("hist.jaundice", "q.jaund.fever", "yes", "dx.cholelithiasis", 2.0),
    ("hist.jaundice", "q.jaund.pale_stool", "yes", "dx.obstructive_cholestasis", 3.0),
    ("hist.jaundice", "q.jaund.dark_urine", "yes", "dx.obstructive_cholestasis", 2.0),
    ("hist.jaundice", "q.jaund.travel", "yes", "dx.viral_hepatitis", 2.5),
    ("hist.jaundice", "q.jaund.alcohol", "yes", "dx.alcoholic_hepatitis", 3.0),
    ("hist.jaundice", "q.jaund.new_drugs", "yes", "dx.dili", 3.0),
    ("hist.jaundice", "q.jaund.weight_loss", "yes", "dx.pancreatic_head_cancer", 2.5),
    ("hist.jaundice", "q.jaund.encephalopathy", "yes", "dx.alcoholic_hepatitis", 2.0),
    ("hist.jaundice", "q.jaund.itch", "yes", "dx.primary_biliary_cholangitis", 2.0),
]

JAUND_RULES = [
    ("q.jaund.dark_urine", 10, "supports", 2.5, None, None, None, targets("dx.obstructive_cholestasis"), None),
    ("q.jaund.pale_stool", 20, "supports", 3.0, None, None, None, targets("dx.obstructive_cholestasis"), None),
    ("q.jaund.pain", 30, "supports", 2.5, None, None, None, targets("dx.cholelithiasis"), None),
    ("q.jaund.fever", 40, "alarm", 3.0, None, None, None, targets("dx.cholelithiasis"), "Cholangitis concern"),
    ("q.jaund.itch", 50, "supports", 2.0, None, None, None, targets("dx.primary_biliary_cholangitis"), None),
    ("q.jaund.alcohol", 60, "risk_factor", 2.5, None, None, None, targets("dx.alcoholic_hepatitis"), None),
    ("q.jaund.new_drugs", 70, "risk_factor", 2.5, None, None, None, targets("dx.dili"), None),
    ("q.jaund.travel", 80, "risk_factor", 2.0, None, None, None, targets("dx.viral_hepatitis"), None),
    ("q.jaund.weight_loss", 90, "alarm", 2.5, None, None, None, targets("dx.pancreatic_head_cancer"), None),
    ("q.jaund.acholic_duration", 100, "alarm", 2.0, None, None, None, targets("dx.obstructive_cholestasis"), None),
    ("q.jaund.encephalopathy", 110, "alarm", 4.0, None, None, None, None, "Acute liver failure pathway"),
    ("q.jaund.joint_pain", 120, "supports", 1.5, None, None, None, None, None),
] + common_context_rules(900)

JAUND_BASELINE = [
    ("hist.jaundice", "lab.lft", "LFTs — pattern of injury"),
    ("hist.jaundice", "lab.cbc", "CBC — haemolysis and infection"),
    ("hist.jaundice", "lab.inr", "INR — synthetic function"),
    ("hist.jaundice", "lab.viral_hepatitis_serology", "Hepatitis A, B, C serology"),
    ("hist.jaundice", "img.us_abdomen", "Abdominal ultrasound — biliary dilation"),
]

JAUND_ADVANCED = [
    ("dx.obstructive_cholestasis", "img.mrcp", "MRCP for biliary obstruction"),
    ("dx.pancreatic_head_cancer", "img.ct_pancreas", "CT pancreas protocol"),
    ("dx.cholelithiasis", "proc.ercp", "ERCP if cholangitis or confirmed choledocholithiasis"),
    ("dx.dili", "proc.liver_biopsy", "Biopsy if diagnosis uncertain after drug withdrawal"),
    ("dx.primary_biliary_cholangitis", "lab.ama", "AMA and cholestatic serology"),
]

JAUND_MANAGEMENT = [
    (
        "dx.obstructive_cholestasis",
        "Conjugated hyperbilirubinaemia from biliary obstruction.",
        "Urgent imaging; ERCP for cholangitis; relieve obstruction; treat underlying cause.",
        "No universal score — assess sepsis and synthetic function.",
        "Cholangitis, encephalopathy, INR not correcting with vitamin K.",
        "Hepatobiliary MDT follow-up.",
        "kl.jaundice.obstructive",
    ),
    (
        "dx.alcoholic_hepatitis",
        "Alcohol-related acute hepatic injury with jaundice.",
        "Abstinence; nutrition; consider corticosteroids if Maddrey >32; monitor for infection.",
        "Maddrey discriminant function; MELD.",
        "Encephalopathy, renal failure, GI bleeding.",
        "Addiction medicine and hepatology follow-up.",
        "kl.jaundice.alcoholic_hepatitis",
    ),
]

# --- Ascites ---

ASCITES_DIAGNOSES = [
    ("dx.cirrhosis_ascites", "Cirrhosis with ascites", "hepatology", "kl.ascites.cirrhosis"),
    ("dx.malignant_ascites", "Malignant ascites", "hepatology", "kl.ascites.malignancy"),
    ("dx.tuberculous_peritonitis", "Tuberculous peritonitis", "hepatology", "kl.ascites.tb"),
    ("dx.cardiac_ascites", "Cardiac ascites", "hepatology", "kl.ascites.cardiac"),
    ("dx.nephrotic_ascites", "Nephrotic syndrome", "hepatology", "kl.ascites.nephrotic"),
    ("dx.sbp", "Spontaneous bacterial peritonitis", "hepatology", "kl.ascites.sbp"),
]

ASCITES_QUESTIONS = [
    ("q.asc.new_onset", "New abdominal distension or increasing girth?", "presenting", "boolean", None, False, None, "contextual"),
    ("q.asc.pain", "Abdominal pain with ascites?", "presenting", "boolean", None, False,
     "SBP, malignancy, TB", "supports"),
    ("q.asc.fever", "Fever?", "alarm", "boolean", None, True, "SBP until excluded", "alarm"),
    ("q.asc.jaundice", "Jaundice or known liver disease?", "presenting", "boolean", None, False,
     "Cirrhosis leading cause", "risk_factor"),
    ("q.asc.alcohol", "Significant alcohol use?", "presenting", "boolean", None, False, None, "risk_factor"),
    ("q.asc.leg_oedema", "Peripheral oedema?", "presenting", "boolean", None, False,
     "Cardiac or nephrotic", "supports"),
    ("q.asc.weight_gain", "Rapid weight gain?", "presenting", "boolean", None, False, None, "contextual"),
    ("q.asc.night_sweats", "Night sweats or weight loss?", "alarm", "boolean", None, True,
     "Malignancy or TB", "alarm"),
    ("q.asc.previous_tb", "TB exposure or immunosuppression?", "presenting", "boolean", None, False,
     "TB peritonitis", "risk_factor"),
    ("q.asc.heart_failure", "Known heart failure?", "presenting", "boolean", None, False, None, "risk_factor"),
    ("q.asc.renal_disease", "Known renal disease or nephrotic syndrome?", "presenting", "boolean", None, False,
     None, "risk_factor"),
    ("q.asc.encephalopathy", "Confusion or hepatic encephalopathy?", "alarm", "boolean", None, True,
     "Decompensated cirrhosis", "alarm"),
]

ASCITES_PRIORS = [
    ("hist.ascites", "dx.cirrhosis_ascites", 1.5),
    ("hist.ascites", "dx.malignant_ascites", 0.6),
    ("hist.ascites", "dx.tuberculous_peritonitis", 0.4),
    ("hist.ascites", "dx.cardiac_ascites", 0.5),
    ("hist.ascites", "dx.nephrotic_ascites", 0.3),
    ("hist.ascites", "dx.sbp", 0.5),
]

ASCITES_WEIGHT_RULES = [
    ("hist.ascites", "q.asc.jaundice", "yes", "dx.cirrhosis_ascites", 3.0),
    ("hist.ascites", "q.asc.alcohol", "yes", "dx.cirrhosis_ascites", 2.0),
    ("hist.ascites", "q.asc.fever", "yes", "dx.sbp", 3.0),
    ("hist.ascites", "q.asc.pain", "yes", "dx.sbp", 2.0),
    ("hist.ascites", "q.asc.heart_failure", "yes", "dx.cardiac_ascites", 3.0),
    ("hist.ascites", "q.asc.leg_oedema", "yes", "dx.cardiac_ascites", 1.5),
    ("hist.ascites", "q.asc.renal_disease", "yes", "dx.nephrotic_ascites", 3.0),
    ("hist.ascites", "q.asc.night_sweats", "yes", "dx.malignant_ascites", 2.0),
    ("hist.ascites", "q.asc.previous_tb", "yes", "dx.tuberculous_peritonitis", 2.5),
    ("hist.ascites", "q.asc.encephalopathy", "yes", "dx.cirrhosis_ascites", 2.0),
]

ASCITES_RULES = [
    ("q.asc.new_onset", 10, "contextual", 2.0, None, None, None, None, None),
    ("q.asc.jaundice", 20, "risk_factor", 3.0, None, None, None, targets("dx.cirrhosis_ascites"), None),
    ("q.asc.alcohol", 30, "risk_factor", 2.0, None, None, None, targets("dx.cirrhosis_ascites"), None),
    ("q.asc.fever", 40, "alarm", 3.5, None, None, None, targets("dx.sbp"), "Diagnostic paracentesis required"),
    ("q.asc.pain", 50, "supports", 2.0, None, None, None, targets("dx.sbp", "dx.malignant_ascites"), None),
    ("q.asc.heart_failure", 60, "risk_factor", 2.5, None, None, None, targets("dx.cardiac_ascites"), None),
    ("q.asc.leg_oedema", 70, "supports", 2.0, None, None, None, targets("dx.cardiac_ascites", "dx.nephrotic_ascites"), None),
    ("q.asc.renal_disease", 80, "risk_factor", 2.5, None, None, None, targets("dx.nephrotic_ascites"), None),
    ("q.asc.night_sweats", 90, "alarm", 2.0, None, None, None, targets("dx.malignant_ascites", "dx.tuberculous_peritonitis"), None),
    ("q.asc.previous_tb", 100, "risk_factor", 2.0, None, None, None, targets("dx.tuberculous_peritonitis"), None),
    ("q.asc.encephalopathy", 110, "alarm", 3.5, None, None, None, targets("dx.cirrhosis_ascites"), None),
    ("q.asc.weight_gain", 120, "contextual", 1.0, None, None, None, None, None),
] + common_context_rules(900)

ASCITES_BASELINE = [
    ("hist.ascites", "lab.lft", "LFTs — synthetic function"),
    ("hist.ascites", "lab.cbc", "CBC"),
    ("hist.ascites", "lab.inr", "INR"),
    ("hist.ascites", "lab.albumin", "Serum albumin"),
    ("hist.ascites", "proc.diagnostic_paracentesis", "Diagnostic paracentesis — cell count, albumin, culture"),
]

ASCITES_ADVANCED = [
    ("dx.cirrhosis_ascites", "img.us_abdomen", "Ultrasound — portal vein and splenomegaly"),
    ("dx.malignant_ascites", "proc.ascitic_cytology", "Ascitic fluid cytology"),
    ("dx.tuberculous_peritonitis", "proc.laparoscopy", "Laparoscopy with peritoneal biopsies if TB suspected"),
    ("dx.sbp", "lab.ascitic_culture", "Ascitic fluid culture and PMN count"),
]

ASCITES_MANAGEMENT = [
    (
        "dx.cirrhosis_ascites",
        "Ascites secondary to portal hypertension in cirrhosis.",
        "Salt restriction; diuretics; diagnostic paracentesis; treat underlying liver disease.",
        "MELD; Child-Pugh.",
        "SBP, hepatorenal syndrome, refractory ascites.",
        "Hepatology follow-up; large-volume paracentesis with albumin if tense.",
        "kl.ascites.cirrhosis",
    ),
    (
        "dx.sbp",
        "Spontaneous bacterial peritonitis in cirrhotic ascites.",
        "Urgent diagnostic paracentesis; IV antibiotics; albumin infusion; monitor renal function.",
        "Ascitic PMN count >250/mm³ diagnostic.",
        "Sepsis, hepatorenal syndrome.",
        "Secondary prophylaxis after episode.",
        "kl.ascites.sbp",
    ),
]

# --- Pancreatitis ---

PANCREATITIS_DIAGNOSES = [
    ("dx.gallstone_pancreatitis", "Gallstone pancreatitis", "gi", "kl.pancreatitis.gallstone"),
    ("dx.alcoholic_pancreatitis", "Alcoholic pancreatitis", "gi", "kl.pancreatitis.alcoholic"),
    ("dx.chronic_pancreatitis", "Chronic pancreatitis", "gi", "kl.pancreatitis.chronic"),
    ("dx.pancreatic_cancer", "Pancreatic cancer", "gi", "kl.pancreatic_cancer.overview"),
    ("dx.hypertriglyceridemia_pancreatitis", "Hypertriglyceridaemia pancreatitis", "gi", "kl.pancreatitis.hypertrig"),
]

PANCREATITIS_QUESTIONS = [
    ("q.panc.epigastric", "Severe epigastric pain?", "presenting", "boolean", None, False, None, "supports"),
    ("q.panc.radiation_back", "Pain radiating to the back?", "presenting", "boolean", None, False,
     "Classic pancreatitis pattern", "supports"),
    ("q.panc.onset", "Sudden onset reaching maximum within hours?", "presenting", "boolean", None, False, None, "supports"),
    ("q.panc.vomiting", "Persistent vomiting?", "presenting", "boolean", None, False, None, "supports"),
    ("q.panc.alcohol", "Heavy alcohol binge preceding pain?", "presenting", "boolean", None, False, None, "risk_factor"),
    ("q.panc.gallstones", "Known gallstones or biliary colic?", "presenting", "boolean", None, False, None, "risk_factor"),
    ("q.panc.jaundice", "Associated jaundice?", "presenting", "boolean", None, False,
     "Common bile duct obstruction or head mass", "supports"),
    ("q.panc.weight_loss", "Unintentional weight loss before presentation?", "alarm", "boolean", None, True,
     "Chronic pancreatitis or malignancy", "alarm"),
    ("q.panc.steatorrhea", "Steatorrhoea?", "presenting", "boolean", None, False,
     "Chronic pancreatitis / insufficiency", "supports"),
    ("q.panc.diabetes", "New or worsening diabetes?", "presenting", "boolean", None, False,
     "Chronic pancreatitis or cancer", "supports"),
    ("q.panc.fever", "Fever?", "alarm", "boolean", None, True,
     "Infected necrosis concern in severe disease", "alarm"),
    ("q.panc.hypotension", "Hypotension or tachycardia?", "alarm", "boolean", None, True,
     "Severe acute pancreatitis", "alarm"),
]

PANCREATITIS_PRIORS = [
    ("hist.pancreatitis", "dx.pancreatitis", 1.5),
    ("hist.pancreatitis", "dx.gallstone_pancreatitis", 1.2),
    ("hist.pancreatitis", "dx.alcoholic_pancreatitis", 1.0),
    ("hist.pancreatitis", "dx.chronic_pancreatitis", 0.6),
    ("hist.pancreatitis", "dx.pancreatic_cancer", 0.4),
    ("hist.pancreatitis", "dx.hypertriglyceridemia_pancreatitis", 0.3),
]

PANCREATITIS_WEIGHT_RULES = [
    ("hist.pancreatitis", "q.panc.radiation_back", "yes", "dx.pancreatitis", 3.0),
    ("hist.pancreatitis", "q.panc.epigastric", "yes", "dx.pancreatitis", 2.5),
    ("hist.pancreatitis", "q.panc.gallstones", "yes", "dx.gallstone_pancreatitis", 3.0),
    ("hist.pancreatitis", "q.panc.alcohol", "yes", "dx.alcoholic_pancreatitis", 3.0),
    ("hist.pancreatitis", "q.panc.steatorrhea", "yes", "dx.chronic_pancreatitis", 2.5),
    ("hist.pancreatitis", "q.panc.weight_loss", "yes", "dx.pancreatic_cancer", 2.5),
    ("hist.pancreatitis", "q.panc.jaundice", "yes", "dx.pancreatic_cancer", 2.0),
    ("hist.pancreatitis", "q.panc.hypotension", "yes", "dx.pancreatitis", 2.0),
]

PANCREATITIS_RULES = [
    ("q.panc.epigastric", 10, "supports", 3.0, None, None, None, targets("dx.pancreatitis"), None),
    ("q.panc.radiation_back", 20, "supports", 3.0, None, None, None, targets("dx.pancreatitis"), None),
    ("q.panc.onset", 30, "supports", 2.0, None, None, None, targets("dx.pancreatitis"), None),
    ("q.panc.vomiting", 40, "supports", 1.5, None, None, None, targets("dx.pancreatitis"), None),
    ("q.panc.gallstones", 50, "risk_factor", 2.5, None, None, None, targets("dx.gallstone_pancreatitis"), None),
    ("q.panc.alcohol", 60, "risk_factor", 2.5, None, None, None, targets("dx.alcoholic_pancreatitis"), None),
    ("q.panc.jaundice", 70, "supports", 2.0, None, None, None, targets("dx.pancreatic_cancer"), None),
    ("q.panc.steatorrhea", 80, "supports", 2.0, None, None, None, targets("dx.chronic_pancreatitis"), None),
    ("q.panc.weight_loss", 90, "alarm", 2.5, None, None, None, targets("dx.pancreatic_cancer", "dx.chronic_pancreatitis"), None),
    ("q.panc.fever", 100, "alarm", 2.5, None, None, None, None, None),
    ("q.panc.hypotension", 110, "alarm", 3.5, None, None, None, targets("dx.pancreatitis"), None),
    ("q.panc.diabetes", 120, "supports", 1.5, None, None, None, targets("dx.chronic_pancreatitis"), None),
] + common_context_rules(900)

PANCREATITIS_BASELINE = [
    ("hist.pancreatitis", "lab.amylase", "Amylase / lipase"),
    ("hist.pancreatitis", "lab.cbc", "CBC — haematocrit as severity marker"),
    ("hist.pancreatitis", "lab.lft", "LFTs — biliary obstruction"),
    ("hist.pancreatitis", "lab.urea", "Urea — renal perfusion marker"),
    ("hist.pancreatitis", "lab.calcium", "Serum calcium"),
]

PANCREATITIS_ADVANCED = [
    ("dx.pancreatitis", "img.ct_abdomen", "Contrast-enhanced CT if severe or uncertain"),
    ("dx.gallstone_pancreatitis", "img.us_abdomen", "Gallbladder ultrasound"),
    ("dx.gallstone_pancreatitis", "proc.ercp", "ERCP if cholangitis or persistent CBD stone"),
    ("dx.chronic_pancreatitis", "img.mrcp", "MRCP or EUS for chronic pancreatitis"),
    ("dx.pancreatic_cancer", "img.ct_pancreas", "CT pancreas protocol"),
]

PANCREATITIS_MANAGEMENT = [
    (
        "dx.pancreatitis",
        "Acute pancreatitis — inflammatory injury of the pancreas.",
        "Aggressive IV fluids early; analgesia; monitor for organ failure; ERCP if cholangitis.",
        "BISAP; APACHE II; Marshall score for organ failure.",
        "Persistent organ failure, infected necrosis, abdominal compartment syndrome.",
        "Repeat imaging if clinical deterioration; specialist centre if severe.",
        "kl.pancreatitis.acute",
    ),
    (
        "dx.chronic_pancreatitis",
        "Chronic pancreatitis — progressive fibroinflammatory disease.",
        "Alcohol abstinence; pancreatic enzyme replacement; pain management; monitor for diabetes and cancer.",
        "No single activity score — track pain and exocrine function.",
        "Unexplained weight loss, new jaundice — exclude cancer.",
        "Hepatopancreatobiliary clinic follow-up.",
        "kl.pancreatitis.chronic",
    ),
]

# --- Biliary pain ---

BILIARY_DIAGNOSES = [
    ("dx.biliary_colic", "Biliary colic", "hepatology", "kl.biliary.colic"),
    ("dx.cholecystitis", "Acute cholecystitis", "hepatology", "kl.biliary.cholecystitis"),
    ("dx.choledocholithiasis", "Choledocholithiasis", "hepatology", "kl.biliary.choledocholithiasis"),
    ("dx.cholangitis", "Acute cholangitis", "hepatology", "kl.biliary.cholangitis"),
    ("dx.sphincter_oddi_dysfunction", "Sphincter of Oddi dysfunction", "hepatology", "kl.biliary.sod"),
    ("dx.ampullary_cancer", "Ampullary carcinoma", "hepatology", "kl.biliary.ampullary"),
]

BILIARY_QUESTIONS = [
    ("q.bil.ruq_pain", "Right upper quadrant pain?", "presenting", "boolean", None, False, None, "supports"),
    ("q.bil.colicky", "Colicky pain lasting minutes to hours?", "presenting", "boolean", None, False,
     "Biliary colic pattern", "supports"),
    ("q.bil.post_fatty", "Pain after fatty meals?", "presenting", "boolean", None, False, None, "supports"),
    ("q.bil.fever", "Fever with pain?", "alarm", "boolean", None, True,
     "Cholangitis or cholecystitis", "alarm"),
    ("q.bil.jaundice", "Jaundice?", "alarm", "boolean", None, True,
     "Choledocholithiasis or cholangitis", "alarm"),
    ("q.bil.duration_constant", "Constant pain >6 hours?", "presenting", "boolean", None, False,
     "Acute cholecystitis more likely than simple colic", "supports"),
    ("q.bil.murphy", "Murphy sign positive on examination?", "presenting", "boolean", None, False,
     "Acute cholecystitis", "supports"),
    ("q.bil.prior_stones", "Known gallstones?", "presenting", "boolean", None, False, None, "risk_factor"),
    ("q.bil.post_chole", "Previous cholecystectomy?", "presenting", "boolean", None, False,
     "SOD or retained stone", "risk_factor"),
    ("q.bil.weight_loss", "Weight loss?", "alarm", "boolean", None, True,
     "Malignancy", "alarm"),
    ("q.bil.pale_stool", "Pale stools or dark urine?", "presenting", "boolean", None, False,
     "Obstructive pattern", "supports"),
    ("q.bil.rigors", "Rigors?", "alarm", "boolean", None, True,
     "Charcot triad — cholangitis", "alarm"),
]

BILIARY_PRIORS = [
    ("hist.biliary_pain", "dx.biliary_colic", 1.2),
    ("hist.biliary_pain", "dx.cholecystitis", 0.9),
    ("hist.biliary_pain", "dx.cholelithiasis", 1.0),
    ("hist.biliary_pain", "dx.choledocholithiasis", 0.7),
    ("hist.biliary_pain", "dx.cholangitis", 0.5),
    ("hist.biliary_pain", "dx.sphincter_oddi_dysfunction", 0.3),
    ("hist.biliary_pain", "dx.ampullary_cancer", 0.3),
]

BILIARY_WEIGHT_RULES = [
    ("hist.biliary_pain", "q.bil.ruq_pain", "yes", "dx.biliary_colic", 2.0),
    ("hist.biliary_pain", "q.bil.post_fatty", "yes", "dx.biliary_colic", 2.5),
    ("hist.biliary_pain", "q.bil.colicky", "yes", "dx.biliary_colic", 2.0),
    ("hist.biliary_pain", "q.bil.duration_constant", "yes", "dx.cholecystitis", 3.0),
    ("hist.biliary_pain", "q.bil.murphy", "yes", "dx.cholecystitis", 3.0),
    ("hist.biliary_pain", "q.bil.fever", "yes", "dx.cholangitis", 2.5),
    ("hist.biliary_pain", "q.bil.fever", "yes", "dx.cholecystitis", 2.0),
    ("hist.biliary_pain", "q.bil.jaundice", "yes", "dx.choledocholithiasis", 3.0),
    ("hist.biliary_pain", "q.bil.rigors", "yes", "dx.cholangitis", 3.5),
    ("hist.biliary_pain", "q.bil.prior_stones", "yes", "dx.cholelithiasis", 2.5),
    ("hist.biliary_pain", "q.bil.post_chole", "yes", "dx.sphincter_oddi_dysfunction", 2.5),
    ("hist.biliary_pain", "q.bil.weight_loss", "yes", "dx.ampullary_cancer", 2.5),
]

BILIARY_RULES = [
    ("q.bil.ruq_pain", 10, "supports", 3.0, None, None, None, targets("dx.biliary_colic", "dx.cholecystitis"), None),
    ("q.bil.colicky", 20, "supports", 2.0, None, None, None, targets("dx.biliary_colic"), None),
    ("q.bil.post_fatty", 30, "supports", 2.5, None, None, None, targets("dx.biliary_colic"), None),
    ("q.bil.duration_constant", 40, "supports", 2.5, None, None, None, targets("dx.cholecystitis"), None),
    ("q.bil.murphy", 50, "supports", 3.0, None, None, None, targets("dx.cholecystitis"), None),
    ("q.bil.fever", 60, "alarm", 3.0, None, None, None, targets("dx.cholangitis", "dx.cholecystitis"), None),
    ("q.bil.rigors", 70, "alarm", 3.5, None, None, None, targets("dx.cholangitis"), None),
    ("q.bil.jaundice", 80, "alarm", 3.0, None, None, None, targets("dx.choledocholithiasis", "dx.cholangitis"), None),
    ("q.bil.pale_stool", 90, "supports", 2.0, None, None, None, targets("dx.choledocholithiasis"), None),
    ("q.bil.prior_stones", 100, "risk_factor", 2.0, None, None, None, targets("dx.cholelithiasis"), None),
    ("q.bil.post_chole", 110, "risk_factor", 2.0, None, None, None, targets("dx.sphincter_oddi_dysfunction"), None),
    ("q.bil.weight_loss", 120, "alarm", 2.5, None, None, None, targets("dx.ampullary_cancer"), None),
] + common_context_rules(900)

BILIARY_BASELINE = [
    ("hist.biliary_pain", "lab.lft", "LFTs — cholestatic pattern"),
    ("hist.biliary_pain", "lab.cbc", "CBC — leucocytosis if cholecystitis"),
    ("hist.biliary_pain", "lab.crp", "CRP"),
    ("hist.biliary_pain", "img.us_abdomen", "Gallbladder ultrasound"),
]

BILIARY_ADVANCED = [
    ("dx.choledocholithiasis", "img.mrcp", "MRCP for common bile duct stones"),
    ("dx.cholangitis", "proc.ercp", "Urgent ERCP for cholangitis"),
    ("dx.cholecystitis", "proc.cholecystectomy", "Cholecystectomy after optimisation"),
    ("dx.ampullary_cancer", "proc.egd", "Endoscopy with ampullary assessment"),
]

BILIARY_MANAGEMENT = [
    (
        "dx.cholangitis",
        "Acute cholangitis — biliary sepsis from obstruction.",
        "IV antibiotics; urgent biliary drainage (ERCP); resuscitation.",
        "Tokyo Guidelines severity grading.",
        "Septic shock, failure to drain, abscess.",
        "Repeat ERCP if drainage incomplete.",
        "kl.biliary.cholangitis",
    ),
    (
        "dx.cholecystitis",
        "Acute inflammation of the gallbladder.",
        "NPO; IV antibiotics; early cholecystectomy when feasible.",
        "Tokyo Guidelines.",
        "Emphysematous cholecystitis, perforation, sepsis.",
        "Surgical follow-up; ERCP if CBD stone.",
        "kl.biliary.cholecystitis",
    ),
]

# --- Chronic liver disease ---

CLD_DIAGNOSES = [
    ("dx.cirrhosis", "Cirrhosis", "hepatology", "kl.cld.cirrhosis"),
    ("dx.nash", "Non-alcoholic steatohepatitis / NAFLD", "hepatology", "kl.cld.nash"),
    ("dx.alcoholic_liver_disease", "Alcoholic liver disease", "hepatology", "kl.cld.ald"),
    ("dx.chronic_viral_hepatitis", "Chronic viral hepatitis B or C", "hepatology", "kl.cld.chronic_viral"),
    ("dx.autoimmune_hepatitis", "Autoimmune hepatitis", "hepatology", "kl.cld.aih"),
    ("dx.hemochromatosis", "Hereditary haemochromatosis", "hepatology", "kl.cld.hemochromatosis"),
    ("dx.hepatocellular_carcinoma", "Hepatocellular carcinoma", "hepatology", "kl.cld.hcc"),
]

CLD_QUESTIONS = [
    ("q.cld.known_diagnosis", "Previously diagnosed chronic liver disease?", "presenting", "boolean", None, False, None, "contextual"),
    ("q.cld.alcohol", "Current or past heavy alcohol use?", "presenting", "boolean", None, False, None, "risk_factor"),
    ("q.cld.metabolic", "Obesity, diabetes, or metabolic syndrome?", "presenting", "boolean", None, False,
     "NAFLD/NASH", "risk_factor"),
    ("q.cld.jaundice", "Jaundice?", "alarm", "boolean", None, True,
     "Decompensation", "alarm"),
    ("q.cld.ascites", "Ascites or leg swelling?", "alarm", "boolean", None, True,
     "Decompensated cirrhosis", "alarm"),
    ("q.cld.encephalopathy", "Confusion or sleep reversal?", "alarm", "boolean", None, True,
     "Hepatic encephalopathy", "alarm"),
    ("q.cld.gi_bleed", "GI bleeding or varices?", "alarm", "boolean", None, True, None, "alarm"),
    ("q.cld.fatigue", "Fatigue?", "presenting", "boolean", None, False, None, "supports"),
    ("q.cld.pruritus", "Pruritus?", "presenting", "boolean", None, False,
     "Cholestatic liver disease", "supports"),
    ("q.cld.joint_autoimmune", "Autoimmune features — joint pains, rash, amenorrhoea?", "presenting", "boolean", None, False,
     "Autoimmune hepatitis", "supports"),
    ("q.cld.ivdu", "IV drug use or blood transfusion before 1992?", "presenting", "boolean", None, False,
     "Chronic viral hepatitis", "risk_factor"),
    ("q.cld.family_iron", "Family history of iron overload?", "presenting", "boolean", None, False,
     "Haemochromatosis", "risk_factor"),
    ("q.cld.weight_loss", "Unintentional weight loss?", "alarm", "boolean", None, True,
     "HCC alarm", "alarm"),
]

CLD_PRIORS = [
    ("hist.chronic_liver_disease", "dx.cirrhosis", 1.0),
    ("hist.chronic_liver_disease", "dx.nash", 1.0),
    ("hist.chronic_liver_disease", "dx.alcoholic_liver_disease", 0.9),
    ("hist.chronic_liver_disease", "dx.chronic_viral_hepatitis", 0.8),
    ("hist.chronic_liver_disease", "dx.autoimmune_hepatitis", 0.4),
    ("hist.chronic_liver_disease", "dx.hemochromatosis", 0.3),
    ("hist.chronic_liver_disease", "dx.hepatocellular_carcinoma", 0.4),
]

CLD_WEIGHT_RULES = [
    ("hist.chronic_liver_disease", "q.cld.alcohol", "yes", "dx.alcoholic_liver_disease", 3.0),
    ("hist.chronic_liver_disease", "q.cld.metabolic", "yes", "dx.nash", 3.0),
    ("hist.chronic_liver_disease", "q.cld.ivdu", "yes", "dx.chronic_viral_hepatitis", 2.5),
    ("hist.chronic_liver_disease", "q.cld.joint_autoimmune", "yes", "dx.autoimmune_hepatitis", 3.0),
    ("hist.chronic_liver_disease", "q.cld.family_iron", "yes", "dx.hemochromatosis", 3.0),
    ("hist.chronic_liver_disease", "q.cld.ascites", "yes", "dx.cirrhosis", 3.0),
    ("hist.chronic_liver_disease", "q.cld.encephalopathy", "yes", "dx.cirrhosis", 3.0),
    ("hist.chronic_liver_disease", "q.cld.gi_bleed", "yes", "dx.cirrhosis", 2.5),
    ("hist.chronic_liver_disease", "q.cld.weight_loss", "yes", "dx.hepatocellular_carcinoma", 2.5),
    ("hist.chronic_liver_disease", "q.cld.jaundice", "yes", "dx.cirrhosis", 2.0),
]

CLD_RULES = [
    ("q.cld.known_diagnosis", 10, "contextual", 2.0, None, None, None, None, None),
    ("q.cld.alcohol", 20, "risk_factor", 2.5, None, None, None, targets("dx.alcoholic_liver_disease"), None),
    ("q.cld.metabolic", 30, "risk_factor", 2.5, None, None, None, targets("dx.nash"), None),
    ("q.cld.ivdu", 40, "risk_factor", 2.0, None, None, None, targets("dx.chronic_viral_hepatitis"), None),
    ("q.cld.joint_autoimmune", 50, "supports", 2.5, None, None, None, targets("dx.autoimmune_hepatitis"), None),
    ("q.cld.family_iron", 60, "risk_factor", 2.0, None, None, None, targets("dx.hemochromatosis"), None),
    ("q.cld.jaundice", 70, "alarm", 2.5, None, None, None, targets("dx.cirrhosis"), None),
    ("q.cld.ascites", 80, "alarm", 3.0, None, None, None, targets("dx.cirrhosis"), "Decompensation"),
    ("q.cld.encephalopathy", 90, "alarm", 3.5, None, None, None, targets("dx.cirrhosis"), None),
    ("q.cld.gi_bleed", 100, "alarm", 3.0, None, None, None, targets("dx.cirrhosis"), None),
    ("q.cld.weight_loss", 110, "alarm", 2.5, None, None, None, targets("dx.hepatocellular_carcinoma"), None),
    ("q.cld.fatigue", 120, "supports", 1.0, None, None, None, None, None),
    ("q.cld.pruritus", 130, "supports", 1.5, None, None, None, None, None),
] + common_context_rules(900)

CLD_BASELINE = [
    ("hist.chronic_liver_disease", "lab.lft", "LFTs — injury pattern"),
    ("hist.chronic_liver_disease", "lab.inr", "INR"),
    ("hist.chronic_liver_disease", "lab.albumin", "Albumin"),
    ("hist.chronic_liver_disease", "lab.platelets", "Platelet count — portal hypertension"),
    ("hist.chronic_liver_disease", "lab.viral_hepatitis_serology", "Hepatitis B and C serology"),
    ("hist.chronic_liver_disease", "img.us_liver", "Liver ultrasound with Doppler"),
]

CLD_ADVANCED = [
    ("dx.cirrhosis", "img.fibroscan", "Transient elastography — fibrosis stage"),
    ("dx.hepatocellular_carcinoma", "img.ct_liver", "Multiphase CT or MRI liver"),
    ("dx.autoimmune_hepatitis", "lab.autoimmune_serology", "ANA, ASMA, IgG"),
    ("dx.hemochromatosis", "lab.ferritin_transferrin", "Iron studies and HFE genotyping"),
    ("dx.chronic_viral_hepatitis", "lab.hbv_dna", "HBV DNA or HCV RNA quantification"),
]

CLD_MANAGEMENT = [
    (
        "dx.cirrhosis",
        "Cirrhosis — advanced hepatic fibrosis with portal hypertension.",
        "Treat underlying cause; screen for HCC and varices; manage complications.",
        "Child-Pugh; MELD; Baveno criteria for varices.",
        "Decompensation: ascites, encephalopathy, variceal bleed, HCC.",
        "Hepatology lifelong follow-up; transplant assessment if indicated.",
        "kl.cld.cirrhosis",
    ),
    (
        "dx.nash",
        "Non-alcoholic fatty liver disease with steatohepatitis.",
        "Weight loss; treat metabolic risk factors; avoid hepatotoxins; monitor fibrosis.",
        "NAFLD activity score on biopsy; FIB-4 non-invasive.",
        "Cirrhosis, HCC in advanced disease.",
        "Hepatology if advanced fibrosis or cirrhosis.",
        "kl.cld.nash",
    ),
    (
        "dx.hepatocellular_carcinoma",
        "Primary liver cancer — usually in cirrhotic liver.",
        "Surveillance ultrasound; diagnosis with multiphase imaging; MDT staging and treatment.",
        "BCLC staging.",
        "Portal vein invasion, decompensation limiting therapy.",
        "Oncology and transplant MDT.",
        "kl.cld.hcc",
    ),
]

HEPATOBILIARY_BUNDLES = [
    {
        "complaint_code": "hist.jaundice",
        "diagnoses": JAUND_DIAGNOSES,
        "questions": JAUND_QUESTIONS,
        "rules": JAUND_RULES,
        "priors": JAUND_PRIORS,
        "weight_rules": JAUND_WEIGHT_RULES,
        "baseline_investigations": JAUND_BASELINE,
        "advanced_investigations": JAUND_ADVANCED,
        "management": JAUND_MANAGEMENT,
    },
    {
        "complaint_code": "hist.ascites",
        "diagnoses": ASCITES_DIAGNOSES,
        "questions": ASCITES_QUESTIONS,
        "rules": ASCITES_RULES,
        "priors": ASCITES_PRIORS,
        "weight_rules": ASCITES_WEIGHT_RULES,
        "baseline_investigations": ASCITES_BASELINE,
        "advanced_investigations": ASCITES_ADVANCED,
        "management": ASCITES_MANAGEMENT,
    },
    {
        "complaint_code": "hist.pancreatitis",
        "diagnoses": PANCREATITIS_DIAGNOSES,
        "questions": PANCREATITIS_QUESTIONS,
        "rules": PANCREATITIS_RULES,
        "priors": PANCREATITIS_PRIORS,
        "weight_rules": PANCREATITIS_WEIGHT_RULES,
        "baseline_investigations": PANCREATITIS_BASELINE,
        "advanced_investigations": PANCREATITIS_ADVANCED,
        "management": PANCREATITIS_MANAGEMENT,
    },
    {
        "complaint_code": "hist.biliary_pain",
        "diagnoses": BILIARY_DIAGNOSES,
        "questions": BILIARY_QUESTIONS,
        "rules": BILIARY_RULES,
        "priors": BILIARY_PRIORS,
        "weight_rules": BILIARY_WEIGHT_RULES,
        "baseline_investigations": BILIARY_BASELINE,
        "advanced_investigations": BILIARY_ADVANCED,
        "management": BILIARY_MANAGEMENT,
    },
    {
        "complaint_code": "hist.chronic_liver_disease",
        "diagnoses": CLD_DIAGNOSES,
        "questions": CLD_QUESTIONS,
        "rules": CLD_RULES,
        "priors": CLD_PRIORS,
        "weight_rules": CLD_WEIGHT_RULES,
        "baseline_investigations": CLD_BASELINE,
        "advanced_investigations": CLD_ADVANCED,
        "management": CLD_MANAGEMENT,
    },
]
