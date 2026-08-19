"""Luminal GI complaint intelligence bundles."""

from app.modules.clinical_history.catalogue_bundle_common import common_context_rules, targets

ABDP_DIAGNOSES = [
    ("dx.appendicitis", "Acute appendicitis", "gi", "kl.abdp.appendicitis"),
    ("dx.gastric_cancer", "Gastric cancer", "gi", "kl.gastric_cancer.overview"),
    ("dx.mesenteric_ischaemia", "Mesenteric ischaemia", "gi", "kl.abdp.mesenteric_ischaemia"),
    ("dx.functional_abdominal_pain", "Functional abdominal pain", "gi", "kl.abdp.functional"),
    ("dx.peptic_ulcer_disease", "Peptic ulcer disease (non-bleeding)", "gi", "kl.peptic_ulcer.overview"),
]

ABDP_QUESTIONS = [
    ("q.abdp.site", "Primary site of pain", "presenting", "choice",
     ["epigastric", "right_upper_quadrant", "right_lower_quadrant", "left_lower_quadrant", "periumbilical", "diffuse"], False,
     "Site narrows organ-based differentials", "supports"),
    ("q.abdp.onset", "Onset", "presenting", "choice", ["sudden", "gradual"], False, None, "contextual"),
    ("q.abdp.character", "Character of pain", "presenting", "choice",
     ["burning", "colicky", "constant", "intermittent"], False, None, "supports"),
    ("q.abdp.radiation", "Radiation to back or right shoulder?", "presenting", "boolean", None, False,
     "Pancreatic and biliary patterns", "supports"),
    ("q.abdp.post_prandial", "Relation to meals", "presenting", "choice",
     ["worse_after_meals", "better_after_meals", "no_relation"], False, None, "supports"),
    ("q.abdp.nausea", "Associated nausea or vomiting?", "presenting", "boolean", None, False, None, "supports"),
    ("q.abdp.fever", "Fever?", "exclusion", "boolean", None, True,
     "Inflammatory or infectious cause", "alarm"),
    ("q.abdp.weight_loss", "Unintentional weight loss?", "exclusion", "boolean", None, True,
     "Malignancy or IBD", "alarm"),
    ("q.abdp.nocturnal", "Pain waking from sleep?", "exclusion", "boolean", None, True,
     "Red flag — organic disease", "alarm"),
    ("q.abdp.blood_stool", "Blood in stool?", "exclusion", "boolean", None, True,
     "IBD or colorectal pathology", "alarm"),
    ("q.abdp.family_ibd", "Family history of IBD or colorectal cancer?", "exclusion", "boolean", None, True,
     None, "risk_factor"),
    ("q.abdp.jaundice", "Associated jaundice?", "alarm", "boolean", None, True,
     "Biliary obstruction or hepatitis", "alarm"),
    ("q.abdp.early_satiety", "Early satiety or vomiting?", "alarm", "boolean", None, True,
     "Gastric outlet or malignancy", "alarm"),
    ("q.abdp.rigidity", "Abdominal rigidity or guarding on examination?", "alarm", "boolean", None, True,
     "Surgical abdomen until proven otherwise", "alarm"),
    ("q.abdp.age_over_55", "Age 55 years or older with new symptoms?", "risk", "boolean", None, False,
     "Higher cancer pre-test probability", "risk_factor"),
]

ABDP_PRIORS = [
    ("hist.abdominal_pain", "dx.gerd", 1.0),
    ("hist.abdominal_pain", "dx.ibs", 0.9),
    ("hist.abdominal_pain", "dx.ibd", 0.7),
    ("hist.abdominal_pain", "dx.cholelithiasis", 0.8),
    ("hist.abdominal_pain", "dx.pancreatitis", 0.6),
    ("hist.abdominal_pain", "dx.appendicitis", 0.5),
    ("hist.abdominal_pain", "dx.colorectal_cancer", 0.4),
    ("hist.abdominal_pain", "dx.gastric_cancer", 0.3),
    ("hist.abdominal_pain", "dx.peptic_ulcer_disease", 0.7),
    ("hist.abdominal_pain", "dx.functional_abdominal_pain", 0.6),
]

ABDP_WEIGHT_RULES = [
    ("hist.abdominal_pain", "q.abdp.site", "epigastric", "dx.gerd", 2.0),
    ("hist.abdominal_pain", "q.abdp.site", "epigastric", "dx.peptic_ulcer_disease", 1.5),
    ("hist.abdominal_pain", "q.abdp.post_prandial", "worse_after_meals", "dx.gerd", 1.5),
    ("hist.abdominal_pain", "q.abdp.post_prandial", "worse_after_meals", "dx.peptic_ulcer_disease", 1.5),
    ("hist.abdominal_pain", "q.abdp.site", "right_upper_quadrant", "dx.cholelithiasis", 2.5),
    ("hist.abdominal_pain", "q.abdp.radiation", "yes", "dx.pancreatitis", 2.5),
    ("hist.abdominal_pain", "q.abdp.radiation", "yes", "dx.cholelithiasis", 1.0),
    ("hist.abdominal_pain", "q.abdp.site", "right_lower_quadrant", "dx.appendicitis", 3.0),
    ("hist.abdominal_pain", "q.abdp.nocturnal", "yes", "dx.ibd", 2.0),
    ("hist.abdominal_pain", "q.abdp.nocturnal", "no", "dx.ibs", 1.0),
    ("hist.abdominal_pain", "q.abdp.blood_stool", "yes", "dx.ibd", 2.5),
    ("hist.abdominal_pain", "q.abdp.blood_stool", "no", "dx.ibs", 0.5),
    ("hist.abdominal_pain", "q.abdp.weight_loss", "yes", "dx.colorectal_cancer", 2.5),
    ("hist.abdominal_pain", "q.abdp.weight_loss", "yes", "dx.gastric_cancer", 2.0),
    ("hist.abdominal_pain", "q.abdp.fever", "yes", "dx.appendicitis", 2.0),
    ("hist.abdominal_pain", "q.abdp.jaundice", "yes", "dx.cholelithiasis", 2.0),
    ("hist.abdominal_pain", "q.abdp.age_over_55", "yes", "dx.colorectal_cancer", 1.5),
]

ABDP_RULES = [
    ("q.abdp.site", 10, "supports", 3.0, None, None, None, None, "Anatomic anchor for differential"),
    ("q.abdp.onset", 20, "contextual", 1.5, None, None, None, None, None),
    ("q.abdp.character", 30, "supports", 2.0, None, None, None, None, None),
    ("q.abdp.radiation", 40, "supports", 2.5, None, None, None, targets("dx.pancreatitis", "dx.cholelithiasis"), None),
    ("q.abdp.post_prandial", 50, "supports", 2.0, None, None, None, targets("dx.gerd", "dx.peptic_ulcer_disease"), None),
    ("q.abdp.nausea", 60, "supports", 1.5, None, None, None, targets("dx.pancreatitis"), None),
    ("q.abdp.fever", 70, "alarm", 2.5, None, None, None, targets("dx.appendicitis", "dx.ibd"), None),
    ("q.abdp.weight_loss", 80, "alarm", 2.5, None, None, None, targets("dx.colorectal_cancer", "dx.gastric_cancer"), None),
    ("q.abdp.nocturnal", 90, "alarm", 2.5, None, None, None, targets("dx.ibd"), "Against pure functional pain"),
    ("q.abdp.blood_stool", 100, "alarm", 2.5, None, None, None, targets("dx.ibd", "dx.colorectal_cancer"), None),
    ("q.abdp.family_ibd", 110, "risk_factor", 1.5, None, None, None, targets("dx.ibd"), None),
    ("q.abdp.jaundice", 120, "alarm", 3.0, None, None, None, targets("dx.cholelithiasis"), None),
    ("q.abdp.early_satiety", 130, "alarm", 2.5, None, None, None, targets("dx.gastric_cancer"), None),
    ("q.abdp.rigidity", 140, "alarm", 4.0, None, None, None, targets("dx.appendicitis", "dx.mesenteric_ischaemia"), None),
    ("q.abdp.age_over_55", 150, "risk_factor", 2.0, None, None, None, targets("dx.colorectal_cancer"), None),
] + common_context_rules(900)

ABDP_BASELINE = [
    ("hist.abdominal_pain", "lab.cbc", "CBC — anaemia or infection"),
    ("hist.abdominal_pain", "lab.lft", "LFTs if hepatobiliary pain"),
    ("hist.abdominal_pain", "lab.amylase", "Amylase / lipase if epigastric or radiation to back"),
    ("hist.abdominal_pain", "lab.crp", "CRP if inflammatory cause suspected"),
    ("hist.abdominal_pain", "img.us_abdomen", "Abdominal ultrasound for RUQ pain"),
]

ABDP_ADVANCED = [
    ("dx.ibd", "proc.colonoscopy", "Colonoscopy with biopsies"),
    ("dx.colorectal_cancer", "proc.colonoscopy", "Colonoscopy with biopsies"),
    ("dx.gerd", "proc.egd", "Endoscopy if alarm features or refractory symptoms"),
    ("dx.pancreatitis", "img.ct_abdomen", "Contrast CT if severe or uncertain"),
    ("dx.cholelithiasis", "img.mrcp", "MRCP for biliary tree anatomy"),
    ("dx.gastric_cancer", "proc.egd", "Upper GI endoscopy with biopsies"),
]

ABDP_MANAGEMENT = [
    (
        "dx.ibs",
        "Irritable bowel syndrome — diagnosis of exclusion.",
        "Apply Rome IV criteria; minimal investigations if low alarm features; diet and lifestyle first line.",
        "Consider IBS-SSS for severity tracking.",
        "New alarm features: weight loss, bleeding, nocturnal symptoms, anaemia.",
        "Primary care or gastroenterology review if refractory.",
        "kl.ibs.overview",
    ),
    (
        "dx.appendicitis",
        "Acute appendicitis — surgical emergency.",
        "NPO; IV fluids; antibiotics; surgical review; imaging if diagnosis uncertain.",
        "Alvarado score may aid decision-making.",
        "Peritonitis, sepsis, perforation.",
        "Operative management; post-operative follow-up.",
        "kl.abdp.appendicitis",
    ),
]

# --- Dysphagia ---

DYSPH_DIAGNOSES = [
    ("dx.eosinophilic_esophagitis", "Eosinophilic oesophagitis", "gi", "kl.dysphagia.eoe"),
    ("dx.peptic_stricture", "Peptic oesophageal stricture", "gi", "kl.dysphagia.peptic_stricture"),
    ("dx.esophageal_cancer", "Oesophageal cancer", "gi", "kl.esophageal_cancer.overview"),
    ("dx.schatzki_ring", "Schatzki ring", "gi", "kl.dysphagia.schatzki"),
    ("dx.motility_disorder", "Oesophageal motility disorder", "gi", "kl.dysphagia.motility"),
    ("dx.opharyngeal_dysphagia", "Oropharyngeal dysphagia", "gi", "kl.dysphagia.oropharyngeal"),
]

DYSPH_QUESTIONS = [
    ("q.dysph.solids_liquids", "Difficulty with solids, liquids, or both?", "presenting", "choice",
     ["solids_only", "solids_and_liquids", "liquids_only"], False, "Mechanical vs motility pattern", "supports"),
    ("q.dysph.progressive", "Progressively worsening dysphagia?", "alarm", "boolean", None, True,
     "Alarm — structural lesion until excluded", "alarm"),
    ("q.dysph.weight_loss", "Unintentional weight loss?", "alarm", "boolean", None, True,
     "Malignancy alarm", "alarm"),
    ("q.dysph.odynophagia", "Painful swallowing (odynophagia)?", "presenting", "boolean", None, False,
     "Oesophagitis, infection, malignancy", "supports"),
    ("q.dysph.regurgitation", "Regurgitation of undigested food?", "presenting", "boolean", None, False,
     "Achalasia pattern", "supports"),
    ("q.dysph.intermittent", "Intermittent symptoms with periods of normal swallowing?", "presenting", "boolean", None, False,
     "EoE and Schatzki ring", "supports"),
    ("q.dysph.heartburn", "Heartburn or acid reflux?", "presenting", "boolean", None, False,
     "Peptic stricture and reflux overlap", "supports"),
    ("q.dysph.food_impaction", "History of food bolus impaction?", "presenting", "boolean", None, False,
     "EoE hallmark", "supports"),
    ("q.dysph.age_over_55", "Age 55 years or older?", "risk", "boolean", None, False,
     "Higher cancer probability", "risk_factor"),
    ("q.dysph.smoking", "Current smoker?", "risk", "boolean", None, False,
     "Squamous and adenocarcinoma risk", "risk_factor"),
    ("q.dysph.alcohol", "Heavy alcohol use?", "risk", "boolean", None, False,
     "Squamous cell carcinoma risk", "risk_factor"),
    ("q.dysph.choking", "Coughing or choking with first swallow?", "presenting", "boolean", None, False,
     "Oropharyngeal dysphagia", "supports"),
    ("q.dysph.neuro", "Neurological disease (stroke, Parkinson's)?", "presenting", "boolean", None, False,
     "Oropharyngeal cause", "risk_factor"),
]

DYSPH_PRIORS = [
    ("hist.dysphagia", "dx.gerd", 0.8),
    ("hist.dysphagia", "dx.achalasia", 0.6),
    ("hist.dysphagia", "dx.eosinophilic_esophagitis", 0.7),
    ("hist.dysphagia", "dx.peptic_stricture", 0.6),
    ("hist.dysphagia", "dx.esophageal_cancer", 0.5),
    ("hist.dysphagia", "dx.schatzki_ring", 0.4),
    ("hist.dysphagia", "dx.motility_disorder", 0.5),
    ("hist.dysphagia", "dx.opharyngeal_dysphagia", 0.4),
]

DYSPH_WEIGHT_RULES = [
    ("hist.dysphagia", "q.dysph.solids_liquids", "solids_only", "dx.peptic_stricture", 2.0),
    ("hist.dysphagia", "q.dysph.solids_liquids", "solids_and_liquids", "dx.achalasia", 2.5),
    ("hist.dysphagia", "q.dysph.solids_liquids", "liquids_only", "dx.opharyngeal_dysphagia", 3.0),
    ("hist.dysphagia", "q.dysph.progressive", "yes", "dx.esophageal_cancer", 3.5),
    ("hist.dysphagia", "q.dysph.weight_loss", "yes", "dx.esophageal_cancer", 3.0),
    ("hist.dysphagia", "q.dysph.regurgitation", "yes", "dx.achalasia", 3.0),
    ("hist.dysphagia", "q.dysph.intermittent", "yes", "dx.eosinophilic_esophagitis", 2.5),
    ("hist.dysphagia", "q.dysph.food_impaction", "yes", "dx.eosinophilic_esophagitis", 3.0),
    ("hist.dysphagia", "q.dysph.heartburn", "yes", "dx.peptic_stricture", 2.0),
    ("hist.dysphagia", "q.dysph.choking", "yes", "dx.opharyngeal_dysphagia", 3.0),
    ("hist.dysphagia", "q.dysph.neuro", "yes", "dx.opharyngeal_dysphagia", 2.5),
    ("hist.dysphagia", "q.dysph.age_over_55", "yes", "dx.esophageal_cancer", 2.0),
]

DYSPH_RULES = [
    ("q.dysph.solids_liquids", 10, "supports", 3.5, None, None, None, None, "Mechanical vs motility framework"),
    ("q.dysph.progressive", 20, "alarm", 4.0, None, None, None, targets("dx.esophageal_cancer"), None),
    ("q.dysph.weight_loss", 30, "alarm", 3.0, None, None, None, targets("dx.esophageal_cancer"), None),
    ("q.dysph.regurgitation", 40, "supports", 2.5, None, None, None, targets("dx.achalasia"), None),
    ("q.dysph.food_impaction", 50, "supports", 3.0, None, None, None, targets("dx.eosinophilic_esophagitis"), None),
    ("q.dysph.intermittent", 60, "supports", 2.0, None, None, None, targets("dx.eosinophilic_esophagitis", "dx.schatzki_ring"), None),
    ("q.dysph.heartburn", 70, "supports", 2.0, None, None, None, targets("dx.peptic_stricture", "dx.gerd"), None),
    ("q.dysph.odynophagia", 80, "supports", 1.5, None, None, None, None, None),
    ("q.dysph.choking", 90, "supports", 2.5, None, None, None, targets("dx.opharyngeal_dysphagia"), None),
    ("q.dysph.neuro", 100, "risk_factor", 2.0, None, None, None, targets("dx.opharyngeal_dysphagia"), None),
    ("q.dysph.age_over_55", 110, "risk_factor", 2.0, None, None, None, targets("dx.esophageal_cancer"), None),
    ("q.dysph.smoking", 120, "risk_factor", 1.5, None, None, None, targets("dx.esophageal_cancer"), None),
    ("q.dysph.alcohol", 130, "risk_factor", 1.5, None, None, None, targets("dx.esophageal_cancer"), None),
] + common_context_rules(900)

DYSPH_BASELINE = [
    ("hist.dysphagia", "lab.cbc", "CBC — anaemia with malignancy"),
    ("hist.dysphagia", "lab.lft", "LFTs if systemic symptoms"),
]

DYSPH_ADVANCED = [
    ("dx.esophageal_cancer", "proc.egd", "Urgent endoscopy with biopsies"),
    ("dx.achalasia", "proc.egd", "Endoscopy plus oesophageal manometry"),
    ("dx.eosinophilic_esophagitis", "proc.egd", "Endoscopy with oesophageal biopsies"),
    ("dx.peptic_stricture", "proc.egd", "Endoscopy — dilatation if stricture"),
    ("dx.motility_disorder", "proc.egd", "Manometry after structural exclusion"),
]

DYSPH_MANAGEMENT = [
    (
        "dx.achalasia",
        "Primary oesophageal motility disorder with impaired LES relaxation.",
        "Confirm with manometry; pneumatic dilatation or POEM; treat reflux complications.",
        "Eckardt score for symptom severity.",
        "Aspiration, significant weight loss, chest pain mimicking cardiac disease.",
        "Long-term follow-up for recurrence and oesophageal cancer surveillance.",
        "kl.achalasia.overview",
    ),
    (
        "dx.eosinophilic_esophagitis",
        "Immune-mediated oesophageal disease — food impaction common in young men.",
        "Topical swallowed steroids; dietary elimination; repeat endoscopy for remission.",
        "EoE activity indices on histology.",
        "Fibrostenotic disease, recurrent impaction.",
        "Allergy and gastroenterology shared care.",
        "kl.dysphagia.eoe",
    ),
]

# --- Dyspepsia ---

DYSPEPSIA_DIAGNOSES = [
    ("dx.functional_dyspepsia", "Functional dyspepsia", "gi", "kl.dyspepsia.functional"),
    ("dx.h_pylori_gastritis", "H. pylori-associated gastritis", "gi", "kl.dyspepsia.h_pylori"),
    ("dx.gastroparesis", "Gastroparesis", "gi", "kl.dyspepsia.gastroparesis"),
    ("dx.gastric_ulcer", "Gastric ulcer (non-bleeding)", "gi", "kl.peptic_ulcer.gastric"),
]

DYSPEPSIA_QUESTIONS = [
    ("q.dyspep.epigastric", "Epigastric pain or burning?", "presenting", "boolean", None, False, None, "supports"),
    ("q.dyspep.postprandial", "Predominantly postprandial fullness or early satiety?", "presenting", "boolean", None, False,
     "Postprandial distress syndrome", "supports"),
    ("q.dyspep.nocturnal", "Symptoms waking from sleep?", "alarm", "boolean", None, True,
     "Alarm — investigate for organic disease", "alarm"),
    ("q.dyspep.weight_loss", "Unintentional weight loss?", "alarm", "boolean", None, True, None, "alarm"),
    ("q.dyspep.dysphagia", "Dysphagia?", "alarm", "boolean", None, True, None, "alarm"),
    ("q.dyspep.anemia", "Iron deficiency anaemia?", "alarm", "boolean", None, True, None, "alarm"),
    ("q.dyspep.vomiting", "Persistent vomiting?", "alarm", "boolean", None, True, None, "alarm"),
    ("q.dyspep.age_over_55", "Age 55 years or older with new dyspepsia?", "risk", "boolean", None, False,
     "Endoscopy threshold lower", "risk_factor"),
    ("q.dyspep.nsaids", "Regular NSAID use?", "presenting", "boolean", None, False, None, "risk_factor"),
    ("q.dyspep.diabetes", "Diabetes mellitus?", "presenting", "boolean", None, False,
     "Gastroparesis risk", "risk_factor"),
    ("q.dyspep.bloating", "Bloating without predominant pain?", "presenting", "boolean", None, False,
     "Functional overlap", "supports"),
    ("q.dyspep.relief_antacid", "Temporary relief with antacids?", "presenting", "boolean", None, False,
     "Acid-related disease", "supports"),
]

DYSPEPSIA_PRIORS = [
    ("hist.dyspepsia", "dx.functional_dyspepsia", 1.2),
    ("hist.dyspepsia", "dx.gerd", 1.0),
    ("hist.dyspepsia", "dx.h_pylori_gastritis", 0.9),
    ("hist.dyspepsia", "dx.gastric_malignancy", 0.4),
    ("hist.dyspepsia", "dx.gastroparesis", 0.5),
    ("hist.dyspepsia", "dx.gastric_ulcer", 0.6),
]

DYSPEPSIA_WEIGHT_RULES = [
    ("hist.dyspepsia", "q.dyspep.relief_antacid", "yes", "dx.gerd", 2.0),
    ("hist.dyspepsia", "q.dyspep.nsaids", "yes", "dx.gastric_ulcer", 2.5),
    ("hist.dyspepsia", "q.dyspep.diabetes", "yes", "dx.gastroparesis", 3.0),
    ("hist.dyspepsia", "q.dyspep.weight_loss", "yes", "dx.gastric_malignancy", 3.0),
    ("hist.dyspepsia", "q.dyspep.anemia", "yes", "dx.gastric_malignancy", 2.5),
    ("hist.dyspepsia", "q.dyspep.nocturnal", "yes", "dx.gastric_malignancy", 2.0),
    ("hist.dyspepsia", "q.dyspep.postprandial", "yes", "dx.functional_dyspepsia", 1.5),
    ("hist.dyspepsia", "q.dyspep.bloating", "yes", "dx.functional_dyspepsia", 1.0),
    ("hist.dyspepsia", "q.dyspep.age_over_55", "yes", "dx.gastric_malignancy", 2.0),
]

DYSPEPSIA_RULES = [
    ("q.dyspep.epigastric", 10, "supports", 2.0, None, None, None, None, None),
    ("q.dyspep.postprandial", 20, "supports", 2.0, None, None, None, targets("dx.functional_dyspepsia"), None),
    ("q.dyspep.relief_antacid", 30, "supports", 2.0, None, None, None, targets("dx.gerd"), None),
    ("q.dyspep.nsaids", 40, "risk_factor", 2.0, None, None, None, targets("dx.gastric_ulcer"), None),
    ("q.dyspep.diabetes", 50, "risk_factor", 2.5, None, None, None, targets("dx.gastroparesis"), None),
    ("q.dyspep.weight_loss", 60, "alarm", 3.0, None, None, None, targets("dx.gastric_malignancy"), None),
    ("q.dyspep.dysphagia", 70, "alarm", 3.0, None, None, None, targets("dx.gastric_malignancy"), None),
    ("q.dyspep.anemia", 80, "alarm", 2.5, None, None, None, targets("dx.gastric_malignancy"), None),
    ("q.dyspep.vomiting", 90, "alarm", 2.5, None, None, None, targets("dx.gastric_malignancy"), None),
    ("q.dyspep.nocturnal", 100, "alarm", 2.0, None, None, None, targets("dx.gastric_malignancy"), None),
    ("q.dyspep.age_over_55", 110, "risk_factor", 2.0, None, None, None, targets("dx.gastric_malignancy"), None),
] + common_context_rules(900)

DYSPEPSIA_BASELINE = [
    ("hist.dyspepsia", "lab.cbc", "CBC — anaemia"),
    ("hist.dyspepsia", "lab.h_pylori", "H. pylori stool antigen or breath test"),
]

DYSPEPSIA_ADVANCED = [
    ("dx.gastric_malignancy", "proc.egd", "Endoscopy with biopsies if alarm features"),
    ("dx.h_pylori_gastritis", "proc.egd", "Endoscopy if refractory after eradication"),
    ("dx.gastroparesis", "img.gastric_emptying", "Gastric emptying study"),
    ("dx.gastric_ulcer", "proc.egd", "Endoscopy for ulcer diagnosis"),
]

DYSPEPSIA_MANAGEMENT = [
    (
        "dx.functional_dyspepsia",
        "Functional dyspepsia — no structural explanation after appropriate investigation.",
        "Test and treat H. pylori; trial PPI; dietary modification; neuromodulators if refractory.",
        "No mandatory score — consider GIS for research.",
        "New alarm features or refractory weight loss.",
        "Step-up therapy; psychology referral if appropriate.",
        "kl.dyspepsia.functional",
    ),
    (
        "dx.h_pylori_gastritis",
        "H. pylori-associated dyspepsia.",
        "Confirm infection; eradication therapy; retest to confirm cure.",
        "No activity score required.",
        "Persistent symptoms after confirmed eradication — endoscopy.",
        "Primary care or gastroenterology follow-up.",
        "kl.dyspepsia.h_pylori",
    ),
]

# --- Vomiting ---

VOMIT_DIAGNOSES = [
    ("dx.gastroenteritis", "Acute gastroenteritis", "gi", "kl.vomiting.gastroenteritis"),
    ("dx.bowel_obstruction", "Bowel obstruction", "gi", "kl.vomiting.obstruction"),
    ("dx.cannabis_hyperemesis", "Cannabis hyperemesis syndrome", "gi", "kl.vomiting.cannabis_hyperemesis"),
    ("dx.cyclic_vomiting", "Cyclic vomiting syndrome", "gi", "kl.vomiting.cvs"),
    ("dx.increased_icp", "Raised intracranial pressure (non-GI)", "gi", "kl.vomiting.icp"),
]

VOMIT_QUESTIONS = [
    ("q.vomit.duration", "Duration of vomiting", "presenting", "choice",
     ["acute_hours", "days", "chronic_weeks"], False, None, "contextual"),
    ("q.vomit.blood", "Blood in vomitus (haematemesis)?", "alarm", "boolean", None, True,
     "Upper GI bleed — separate pathway overlap", "alarm"),
    ("q.vomit.bile", "Bilious vomiting?", "presenting", "boolean", None, False,
     "Distal obstruction if post-pyloric", "supports"),
    ("q.vomit.feculent", "Faeculent vomitus?", "alarm", "boolean", None, True,
     "High-grade small bowel obstruction", "alarm"),
    ("q.vomit.abdominal_distension", "Abdominal distension?", "presenting", "boolean", None, False,
     "Obstruction pattern", "supports"),
    ("q.vomit.pain", "Associated abdominal pain?", "presenting", "boolean", None, False, None, "supports"),
    ("q.vomit.headache", "Severe headache with vomiting?", "alarm", "boolean", None, True,
     "Neurological red flag", "alarm"),
    ("q.vomit.pregnancy", "Possible pregnancy?", "presenting", "boolean", None, False,
     "Hyperemesis gravidarum", "risk_factor"),
    ("q.vomit.cannabis", "Heavy cannabis use?", "presenting", "boolean", None, False,
     "Cannabis hyperemesis syndrome", "risk_factor"),
    ("q.vomit.cyclic_pattern", "Stereotyped episodes with symptom-free intervals?", "presenting", "boolean", None, False,
     "Cyclic vomiting syndrome", "supports"),
    ("q.vomit.diabetes", "Diabetes — missed insulin or DKA symptoms?", "alarm", "boolean", None, True,
     "Metabolic emergency", "alarm"),
    ("q.vomit.recent_surgery", "Recent abdominal surgery?", "presenting", "boolean", None, False,
     "Adhesions and obstruction", "risk_factor"),
]

VOMIT_PRIORS = [
    ("hist.vomiting", "dx.gastroenteritis", 1.2),
    ("hist.vomiting", "dx.gerd", 0.6),
    ("hist.vomiting", "dx.pancreatitis", 0.5),
    ("hist.vomiting", "dx.bowel_obstruction", 0.6),
    ("hist.vomiting", "dx.gastroparesis", 0.5),
    ("hist.vomiting", "dx.cyclic_vomiting", 0.4),
    ("hist.vomiting", "dx.cannabis_hyperemesis", 0.3),
]

VOMIT_WEIGHT_RULES = [
    ("hist.vomiting", "q.vomit.feculent", "yes", "dx.bowel_obstruction", 4.0),
    ("hist.vomiting", "q.vomit.bile", "yes", "dx.bowel_obstruction", 2.0),
    ("hist.vomiting", "q.vomit.abdominal_distension", "yes", "dx.bowel_obstruction", 2.5),
    ("hist.vomiting", "q.vomit.recent_surgery", "yes", "dx.bowel_obstruction", 2.0),
    ("hist.vomiting", "q.vomit.cannabis", "yes", "dx.cannabis_hyperemesis", 3.5),
    ("hist.vomiting", "q.vomit.cyclic_pattern", "yes", "dx.cyclic_vomiting", 3.0),
    ("hist.vomiting", "q.vomit.pain", "yes", "dx.pancreatitis", 2.0),
    ("hist.vomiting", "q.vomit.duration", "acute_hours", "dx.gastroenteritis", 2.0),
    ("hist.vomiting", "q.vomit.diabetes", "yes", "dx.gastroparesis", 1.5),
]

VOMIT_RULES = [
    ("q.vomit.duration", 10, "contextual", 2.0, None, None, None, None, None),
    ("q.vomit.blood", 20, "alarm", 4.0, None, None, None, None, "Consider UGI bleed pathway"),
    ("q.vomit.feculent", 30, "alarm", 4.0, None, None, None, targets("dx.bowel_obstruction"), None),
    ("q.vomit.bile", 40, "supports", 2.0, None, None, None, targets("dx.bowel_obstruction"), None),
    ("q.vomit.abdominal_distension", 50, "supports", 2.5, None, None, None, targets("dx.bowel_obstruction"), None),
    ("q.vomit.pain", 60, "supports", 2.0, None, None, None, targets("dx.pancreatitis"), None),
    ("q.vomit.headache", 70, "alarm", 3.5, None, None, None, targets("dx.increased_icp"), None),
    ("q.vomit.cannabis", 80, "risk_factor", 2.5, None, None, None, targets("dx.cannabis_hyperemesis"), None),
    ("q.vomit.cyclic_pattern", 90, "supports", 2.5, None, None, None, targets("dx.cyclic_vomiting"), None),
    ("q.vomit.pregnancy", 100, "risk_factor", 2.0, None, None, None, None, None),
    ("q.vomit.diabetes", 110, "alarm", 2.5, None, None, None, None, None),
    ("q.vomit.recent_surgery", 120, "risk_factor", 2.0, None, None, None, targets("dx.bowel_obstruction"), None),
] + common_context_rules(900)

VOMIT_BASELINE = [
    ("hist.vomiting", "lab.cbc", "CBC if systemic illness"),
    ("hist.vomiting", "lab.lft", "LFTs if hepatobiliary cause"),
    ("hist.vomiting", "lab.amylase", "Amylase / lipase if epigastric pain"),
    ("hist.vomiting", "lab.urea_electrolytes", "U&E — dehydration and metabolic disturbance"),
]

VOMIT_ADVANCED = [
    ("dx.bowel_obstruction", "img.ct_abdomen", "CT abdomen with contrast"),
    ("dx.pancreatitis", "img.ct_abdomen", "CT if severe pancreatitis suspected"),
    ("dx.bowel_obstruction", "proc.egd", "Endoscopy if proximal obstruction suspected"),
    ("dx.gastroparesis", "img.gastric_emptying", "Gastric emptying study"),
]

VOMIT_MANAGEMENT = [
    (
        "dx.bowel_obstruction",
        "Mechanical bowel obstruction — surgical emergency until excluded.",
        "NPO; NG decompression; IV fluids; surgical review; imaging.",
        "No single score — assess strangulation clinically.",
        "Peritonitis, sepsis, faeculent vomitus.",
        "Surgical management; monitor for recurrence.",
        "kl.vomiting.obstruction",
    ),
]

# --- Constipation ---

CONST_DIAGNOSES = [
    ("dx.ibs_c", "IBS with constipation (IBS-C)", "gi", "kl.constipation.ibs_c"),
    ("dx.opioid_induced_constipation", "Opioid-induced constipation", "gi", "kl.constipation.opioid"),
    ("dx.pelvic_floor_dysfunction", "Pelvic floor dyssynergia", "gi", "kl.constipation.pelvic_floor"),
    ("dx.hypothyroid_constipation", "Hypothyroidism", "gi", "kl.constipation.hypothyroid"),
    ("dx.colorectal_obstruction", "Colorectal obstruction", "gi", "kl.constipation.obstruction"),
]

CONST_QUESTIONS = [
    ("q.const.duration", "Symptom duration", "presenting", "choice",
     ["acute_days", "chronic_months", "lifelong"], False, None, "contextual"),
    ("q.const.blood", "Blood on stool or toilet paper?", "alarm", "boolean", None, True, None, "alarm"),
    ("q.const.weight_loss", "Unintentional weight loss?", "alarm", "boolean", None, True, None, "alarm"),
    ("q.const.narrow_stool", "New narrow-calibre stools?", "alarm", "boolean", None, True,
     "Colorectal cancer alarm", "alarm"),
    ("q.const.abdominal_pain", "Significant abdominal pain with constipation?", "presenting", "boolean", None, False,
     "IBS-C vs obstruction", "supports"),
    ("q.const.bloating", "Bloating relieved by defecation?", "presenting", "boolean", None, False,
     "IBS pattern", "supports"),
    ("q.const.opioids", "Regular opioid use?", "presenting", "boolean", None, False, None, "risk_factor"),
    ("q.const.age_over_50", "Age 50 years or older without screening?", "risk", "boolean", None, False, None, "risk_factor"),
    ("q.const.red_flags_family", "Family history of colorectal cancer?", "risk", "boolean", None, False, None, "risk_factor"),
    ("q.const.straining", "Excessive straining with incomplete evacuation?", "presenting", "boolean", None, False,
     "Pelvic floor dyssynergia", "supports"),
    ("q.const.manual_evacuation", "Digital evacuation required?", "presenting", "boolean", None, False,
     "Dyssynergia or rectocele", "supports"),
    ("q.const.thyroid_symptoms", "Fatigue, cold intolerance, weight gain?", "presenting", "boolean", None, False,
     "Hypothyroidism", "supports"),
]

CONST_PRIORS = [
    ("hist.constipation", "dx.ibs_c", 1.0),
    ("hist.constipation", "dx.opioid_induced_constipation", 0.8),
    ("hist.constipation", "dx.colorectal_cancer", 0.4),
    ("hist.constipation", "dx.pelvic_floor_dysfunction", 0.6),
    ("hist.constipation", "dx.hypothyroid_constipation", 0.4),
    ("hist.constipation", "dx.colorectal_obstruction", 0.3),
]

CONST_WEIGHT_RULES = [
    ("hist.constipation", "q.const.opioids", "yes", "dx.opioid_induced_constipation", 3.5),
    ("hist.constipation", "q.const.bloating", "yes", "dx.ibs_c", 2.0),
    ("hist.constipation", "q.const.straining", "yes", "dx.pelvic_floor_dysfunction", 2.5),
    ("hist.constipation", "q.const.manual_evacuation", "yes", "dx.pelvic_floor_dysfunction", 2.5),
    ("hist.constipation", "q.const.weight_loss", "yes", "dx.colorectal_cancer", 3.0),
    ("hist.constipation", "q.const.narrow_stool", "yes", "dx.colorectal_cancer", 3.0),
    ("hist.constipation", "q.const.blood", "yes", "dx.colorectal_cancer", 2.5),
    ("hist.constipation", "q.const.thyroid_symptoms", "yes", "dx.hypothyroid_constipation", 3.0),
    ("hist.constipation", "q.const.age_over_50", "yes", "dx.colorectal_cancer", 2.0),
]

CONST_RULES = [
    ("q.const.duration", 10, "contextual", 1.5, None, None, None, None, None),
    ("q.const.opioids", 20, "risk_factor", 3.0, None, None, None, targets("dx.opioid_induced_constipation"), None),
    ("q.const.bloating", 30, "supports", 2.0, None, None, None, targets("dx.ibs_c"), None),
    ("q.const.straining", 40, "supports", 2.0, None, None, None, targets("dx.pelvic_floor_dysfunction"), None),
    ("q.const.manual_evacuation", 50, "supports", 2.5, None, None, None, targets("dx.pelvic_floor_dysfunction"), None),
    ("q.const.weight_loss", 60, "alarm", 3.0, None, None, None, targets("dx.colorectal_cancer"), None),
    ("q.const.narrow_stool", 70, "alarm", 3.0, None, None, None, targets("dx.colorectal_cancer"), None),
    ("q.const.blood", 80, "alarm", 2.5, None, None, None, targets("dx.colorectal_cancer"), None),
    ("q.const.abdominal_pain", 90, "supports", 1.5, None, None, None, targets("dx.ibs_c", "dx.colorectal_obstruction"), None),
    ("q.const.thyroid_symptoms", 100, "supports", 2.0, None, None, None, targets("dx.hypothyroid_constipation"), None),
    ("q.const.age_over_50", 110, "risk_factor", 2.0, None, None, None, targets("dx.colorectal_cancer"), None),
    ("q.const.red_flags_family", 120, "risk_factor", 1.5, None, None, None, targets("dx.colorectal_cancer"), None),
] + common_context_rules(900)

CONST_BASELINE = [
    ("hist.constipation", "lab.cbc", "CBC — anaemia"),
    ("hist.constipation", "lab.tsh", "TSH — hypothyroidism"),
    ("hist.constipation", "lab.calcium", "Calcium — hypercalcaemia"),
]

CONST_ADVANCED = [
    ("dx.colorectal_cancer", "proc.colonoscopy", "Colonoscopy if alarm features"),
    ("dx.pelvic_floor_dysfunction", "proc.anorectal_manometry", "Anorectal manometry and balloon expulsion test"),
    ("dx.colorectal_obstruction", "img.ct_abdomen", "CT colonography or colonoscopy"),
]

CONST_MANAGEMENT = [
    (
        "dx.ibs_c",
        "IBS with constipation — functional disorder meeting Rome criteria.",
        "Increase fibre cautiously; osmotic laxatives; prosecretory agents if refractory.",
        "IBS-SSS optional.",
        "New alarm features — re-investigate.",
        "Dietitian and gastroenterology if refractory.",
        "kl.constipation.ibs_c",
    ),
    (
        "dx.opioid_induced_constipation",
        "Constipation caused by opioid analgesia.",
        "Laxative prophylaxis when starting opioids; consider PAMORAs if refractory.",
        "No standard score.",
        "Obstruction symptoms — investigate before aggressive laxation.",
        "Review opioid requirement with prescriber.",
        "kl.constipation.opioid",
    ),
]

# --- Weight loss ---

WL_DIAGNOSES = [
    ("dx.malignancy_weight_loss", "Malignancy-associated weight loss", "gi", "kl.weight_loss.malignancy"),
    ("dx.hyperthyroid_wl", "Hyperthyroidism", "gi", "kl.weight_loss.hyperthyroid"),
    ("dx.malabsorption_wl", "Malabsorption", "gi", "kl.weight_loss.malabsorption"),
    ("dx.depression_anorexia", "Depression / eating disorder", "gi", "kl.weight_loss.depression"),
    ("dx.diabetes_wl", "Uncontrolled diabetes mellitus", "gi", "kl.weight_loss.diabetes"),
]

WL_QUESTIONS = [
    ("q.wl.intentional", "Is the weight loss intentional?", "presenting", "boolean", None, False,
     "Unintentional loss drives workup", "contextual"),
    ("q.wl.amount", "Approximate weight loss", "presenting", "choice",
     ["less_than_5_percent", "5_to_10_percent", "more_than_10_percent"], False, None, "alarm"),
    ("q.wl.duration", "Over what time period?", "presenting", "choice",
     ["weeks", "months", "years"], False, None, "contextual"),
    ("q.wl.anorexia", "Reduced appetite?", "presenting", "boolean", None, False, None, "supports"),
    ("q.wl.abdominal_symptoms", "Abdominal pain, diarrhoea, or dysphagia?", "presenting", "boolean", None, False,
     "GI organic disease", "supports"),
    ("q.wl.night_sweats", "Night sweats or fevers?", "alarm", "boolean", None, True,
     "Malignancy or chronic infection", "alarm"),
    ("q.wl.age_over_65", "Age 65 years or older?", "risk", "boolean", None, False,
     "Higher cancer yield from investigation", "risk_factor"),
    ("q.wl.smoking", "Current smoker?", "risk", "boolean", None, False, None, "risk_factor"),
    ("q.wl.alcohol", "Heavy alcohol use?", "risk", "boolean", None, False,
     "Malignancy and liver disease", "risk_factor"),
    ("q.wl.palpatations", "Palpitations, tremor, heat intolerance?", "presenting", "boolean", None, False,
     "Hyperthyroidism", "supports"),
    ("q.wl.polyuria", "Polyuria and polydipsia?", "presenting", "boolean", None, False,
     "Diabetes", "supports"),
    ("q.wl.low_mood", "Low mood or loss of interest?", "presenting", "boolean", None, False,
     "Depression", "supports"),
    ("q.wl.steatorrhea", "Steatorrhoea or bulky stools?", "presenting", "boolean", None, False,
     "Malabsorption", "supports"),
]

WL_PRIORS = [
    ("hist.weight_loss", "dx.malignancy_weight_loss", 0.8),
    ("hist.weight_loss", "dx.colorectal_cancer", 0.6),
    ("hist.weight_loss", "dx.gastric_malignancy", 0.5),
    ("hist.weight_loss", "dx.ibd", 0.5),
    ("hist.weight_loss", "dx.hyperthyroid_wl", 0.5),
    ("hist.weight_loss", "dx.malabsorption_wl", 0.5),
    ("hist.weight_loss", "dx.depression_anorexia", 0.6),
    ("hist.weight_loss", "dx.diabetes_wl", 0.4),
]

WL_WEIGHT_RULES = [
    ("hist.weight_loss", "q.wl.intentional", "no", "dx.malignancy_weight_loss", 2.0),
    ("hist.weight_loss", "q.wl.amount", "more_than_10_percent", "dx.malignancy_weight_loss", 2.5),
    ("hist.weight_loss", "q.wl.night_sweats", "yes", "dx.malignancy_weight_loss", 2.5),
    ("hist.weight_loss", "q.wl.abdominal_symptoms", "yes", "dx.colorectal_cancer", 2.0),
    ("hist.weight_loss", "q.wl.abdominal_symptoms", "yes", "dx.gastric_malignancy", 1.5),
    ("hist.weight_loss", "q.wl.palpatations", "yes", "dx.hyperthyroid_wl", 3.0),
    ("hist.weight_loss", "q.wl.polyuria", "yes", "dx.diabetes_wl", 3.0),
    ("hist.weight_loss", "q.wl.low_mood", "yes", "dx.depression_anorexia", 2.5),
    ("hist.weight_loss", "q.wl.steatorrhea", "yes", "dx.malabsorption_wl", 3.0),
    ("hist.weight_loss", "q.wl.age_over_65", "yes", "dx.malignancy_weight_loss", 2.0),
]

WL_RULES = [
    ("q.wl.intentional", 10, "contextual", 3.0, None, None, None, None, "Unintentional loss triggers workup"),
    ("q.wl.amount", 20, "alarm", 2.5, "q.wl.intentional", "no", None, targets("dx.malignancy_weight_loss"), None),
    ("q.wl.duration", 30, "contextual", 1.5, "q.wl.intentional", "no", None, None, None),
    ("q.wl.anorexia", 40, "supports", 2.0, "q.wl.intentional", "no", None, None, None),
    ("q.wl.abdominal_symptoms", 50, "supports", 2.5, "q.wl.intentional", "no", None, targets("dx.colorectal_cancer", "dx.gastric_malignancy"), None),
    ("q.wl.night_sweats", 60, "alarm", 2.5, "q.wl.intentional", "no", None, targets("dx.malignancy_weight_loss"), None),
    ("q.wl.palpatations", 70, "supports", 2.5, None, None, None, targets("dx.hyperthyroid_wl"), None),
    ("q.wl.polyuria", 80, "supports", 2.5, None, None, None, targets("dx.diabetes_wl"), None),
    ("q.wl.low_mood", 90, "supports", 2.0, None, None, None, targets("dx.depression_anorexia"), None),
    ("q.wl.steatorrhea", 100, "supports", 2.5, None, None, None, targets("dx.malabsorption_wl"), None),
    ("q.wl.age_over_65", 110, "risk_factor", 2.0, "q.wl.intentional", "no", None, targets("dx.malignancy_weight_loss"), None),
    ("q.wl.smoking", 120, "risk_factor", 1.5, None, None, None, targets("dx.malignancy_weight_loss"), None),
    ("q.wl.alcohol", 130, "risk_factor", 1.5, None, None, None, None, None),
] + common_context_rules(900)

WL_BASELINE = [
    ("hist.weight_loss", "lab.cbc", "CBC — anaemia"),
    ("hist.weight_loss", "lab.crp", "CRP / inflammatory markers"),
    ("hist.weight_loss", "lab.lft", "LFTs"),
    ("hist.weight_loss", "lab.tsh", "TSH"),
    ("hist.weight_loss", "lab.hba1c", "HbA1c — diabetes"),
    ("hist.weight_loss", "lab.chest_xray", "Chest X-ray if thoracic symptoms"),
]

WL_ADVANCED = [
    ("dx.colorectal_cancer", "proc.colonoscopy", "Colonoscopy if GI symptoms or age threshold"),
    ("dx.gastric_malignancy", "proc.egd", "Endoscopy if upper GI symptoms"),
    ("dx.malabsorption_wl", "lab.ttiga", "Coeliac serology and faecal elastase"),
    ("dx.malignancy_weight_loss", "img.ct_chest_abd_pelvis", "CT CAP if malignancy suspected"),
]

WL_MANAGEMENT = [
    (
        "dx.malignancy_weight_loss",
        "Unexplained weight loss with concern for malignancy.",
        "Age-appropriate cancer screening; CT imaging if high suspicion; tissue diagnosis when possible.",
        "No single score — use clinical probability and speed of loss.",
        "Obstruction, perforation, severe anaemia.",
        "Oncology referral after histological confirmation.",
        "kl.weight_loss.malignancy",
    ),
]

LUMINAL_BUNDLES = [
    {
        "complaint_code": "hist.abdominal_pain",
        "diagnoses": ABDP_DIAGNOSES,
        "questions": ABDP_QUESTIONS,
        "rules": ABDP_RULES,
        "priors": ABDP_PRIORS,
        "weight_rules": ABDP_WEIGHT_RULES,
        "baseline_investigations": ABDP_BASELINE,
        "advanced_investigations": ABDP_ADVANCED,
        "management": ABDP_MANAGEMENT,
    },
    {
        "complaint_code": "hist.dysphagia",
        "diagnoses": DYSPH_DIAGNOSES,
        "questions": DYSPH_QUESTIONS,
        "rules": DYSPH_RULES,
        "priors": DYSPH_PRIORS,
        "weight_rules": DYSPH_WEIGHT_RULES,
        "baseline_investigations": DYSPH_BASELINE,
        "advanced_investigations": DYSPH_ADVANCED,
        "management": DYSPH_MANAGEMENT,
    },
    {
        "complaint_code": "hist.dyspepsia",
        "diagnoses": DYSPEPSIA_DIAGNOSES,
        "questions": DYSPEPSIA_QUESTIONS,
        "rules": DYSPEPSIA_RULES,
        "priors": DYSPEPSIA_PRIORS,
        "weight_rules": DYSPEPSIA_WEIGHT_RULES,
        "baseline_investigations": DYSPEPSIA_BASELINE,
        "advanced_investigations": DYSPEPSIA_ADVANCED,
        "management": DYSPEPSIA_MANAGEMENT,
    },
    {
        "complaint_code": "hist.vomiting",
        "diagnoses": VOMIT_DIAGNOSES,
        "questions": VOMIT_QUESTIONS,
        "rules": VOMIT_RULES,
        "priors": VOMIT_PRIORS,
        "weight_rules": VOMIT_WEIGHT_RULES,
        "baseline_investigations": VOMIT_BASELINE,
        "advanced_investigations": VOMIT_ADVANCED,
        "management": VOMIT_MANAGEMENT,
    },
    {
        "complaint_code": "hist.constipation",
        "diagnoses": CONST_DIAGNOSES,
        "questions": CONST_QUESTIONS,
        "rules": CONST_RULES,
        "priors": CONST_PRIORS,
        "weight_rules": CONST_WEIGHT_RULES,
        "baseline_investigations": CONST_BASELINE,
        "advanced_investigations": CONST_ADVANCED,
        "management": CONST_MANAGEMENT,
    },
    {
        "complaint_code": "hist.weight_loss",
        "diagnoses": WL_DIAGNOSES,
        "questions": WL_QUESTIONS,
        "rules": WL_RULES,
        "priors": WL_PRIORS,
        "weight_rules": WL_WEIGHT_RULES,
        "baseline_investigations": WL_BASELINE,
        "advanced_investigations": WL_ADVANCED,
        "management": WL_MANAGEMENT,
    },
]
