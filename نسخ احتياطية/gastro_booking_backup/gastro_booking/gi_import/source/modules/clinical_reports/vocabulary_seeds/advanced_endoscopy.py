"""EUS, capsule, and enteroscopy — vocabulary seeds (Sprint 4E–4G)."""

EUS_VOCABULARY_SEED = {
    "eus_indication_category": [
        ("pancreatic_mass", "Pancreatic mass / lesion", 10),
        ("biliary_stricture", "Biliary stricture", 20),
        ("submucosal_lesion", "Submucosal lesion", 30),
        ("staging", "Cancer staging", 40),
        ("cystic_lesion", "Cystic lesion", 50),
        ("other", "Other / specify in detail", 99),
    ],
    "eus_scope_type": [
        ("linear", "Linear echoendoscope", 10),
        ("radial", "Radial echoendoscope", 20),
    ],
    "eus_frequency": [
        ("5mhz", "5 MHz", 10),
        ("7_5mhz", "7.5 MHz", 20),
        ("10mhz", "10 MHz", 30),
        ("12mhz", "12 MHz", 40),
    ],
    "eus_target_organ": [
        ("pancreas", "Pancreas", 10),
        ("bile_duct", "Bile duct", 20),
        ("mediastinum", "Mediastinum", 30),
        ("rectum", "Rectum", 40),
        ("other", "Other", 99),
    ],
    "eus_echo_layer": [
        ("mucosa", "Mucosa", 10),
        ("submucosa", "Submucosa", 20),
        ("muscularis", "Muscularis propria", 30),
        ("serosa", "Serosa / adventitia", 40),
        ("extramural", "Extramural", 50),
    ],
    "eus_needle_type": [
        ("fna_22g", "FNA 22G", 10),
        ("fnb_22g", "FNB 22G", 20),
        ("fnb_25g", "FNB 25G", 30),
        ("core_biopsy", "Core biopsy needle", 40),
    ],
    "eus_cytology_adequacy": [
        ("adequate", "Adequate", 10),
        ("inadequate", "Inadequate", 20),
        ("pending", "Pending", 30),
    ],
    "eus_t_stage": [
        ("tx", "Tx", 10),
        ("t0", "T0", 20),
        ("t1", "T1", 30),
        ("t2", "T2", 40),
        ("t3", "T3", 50),
        ("t4", "T4", 60),
        ("not_applicable", "Not applicable", 99),
    ],
    "eus_finding_type": [
        ("normal", "Normal", 10),
        ("mass", "Mass", 20),
        ("cyst", "Cyst", 30),
        ("chronic_pancreatitis", "Chronic pancreatitis", 40),
        ("stone", "Stone", 50),
        ("lymphadenopathy", "Lymphadenopathy", 60),
        ("other", "Other", 99),
    ],
    "eus_intervention_type": [
        ("fna", "FNA / FNB", 10),
        ("cyst_drainage", "Cyst drainage", 20),
        ("celiac_block", "Celiac plexus block", 30),
        ("other", "Other", 99),
    ],
}

CAPSULE_VOCABULARY_SEED = {
    "capsule_indication_category": [
        ("obscure_bleeding", "Obscure GI bleeding", 10),
        ("crohn_surveillance", "Crohn disease surveillance", 20),
        ("polyposis", "Polyposis syndrome", 30),
        ("malabsorption", "Malabsorption / diarrhoea", 40),
        ("other", "Other / specify in detail", 99),
    ],
    "capsule_completion_status": [
        ("complete", "Complete study", 10),
        ("incomplete_gastric", "Incomplete — retained in stomach", 20),
        ("incomplete_small_bowel", "Incomplete — small bowel not fully visualized", 30),
    ],
    "capsule_type": [
        ("standard", "Standard video capsule", 10),
        ("patency", "Patency capsule (prior)", 20),
        ("panenteric", "Pan-enteric capsule", 30),
    ],
    "capsule_retention_risk": [
        ("low", "Low", 10),
        ("moderate", "Moderate", 20),
        ("high", "High", 30),
    ],
    "capsule_finding_type": [
        ("normal", "Normal", 10),
        ("erosion", "Erosion / ulceration", 20),
        ("angioectasia", "Angioectasia", 30),
        ("mass", "Mass / polyp", 40),
        ("stricture", "Stricture", 50),
        ("blood", "Active bleeding", 60),
        ("other", "Other", 99),
    ],
}

ENTEROSCOPY_VOCABULARY_SEED = {
    "enteroscopy_indication_category": [
        ("obscure_bleeding", "Obscure GI bleeding", 10),
        ("stricture", "Stricture", 20),
        ("tumor", "Tumor / mass", 30),
        ("polyposis", "Polyposis", 40),
        ("other", "Other / specify in detail", 99),
    ],
    "enteroscopy_approach": [
        ("oral", "Oral", 10),
        ("anal", "Anal", 20),
        ("combined", "Combined (oral + anal)", 30),
    ],
    "enteroscopy_device_type": [
        ("double_balloon", "Double-balloon enteroscopy", 10),
        ("single_balloon", "Single-balloon enteroscopy", 20),
        ("spiral", "Spiral enteroscopy", 30),
        ("motorized", "Motorized enteroscopy", 40),
    ],
    "enteroscopy_max_depth": [
        ("proximal_jejunum", "Proximal jejunum", 10),
        ("mid_jejunum", "Mid jejunum", 20),
        ("distal_jejunum", "Distal jejunum", 30),
        ("proximal_ileum", "Proximal ileum", 40),
        ("mid_ileum", "Mid ileum", 50),
        ("terminal_ileum", "Terminal ileum", 60),
    ],
    "enteroscopy_finding_type": [
        ("normal", "Normal", 10),
        ("erosion", "Erosion / ulceration", 20),
        ("angioectasia", "Angioectasia", 30),
        ("mass", "Mass", 40),
        ("stricture", "Stricture", 50),
        ("other", "Other", 99),
    ],
    "enteroscopy_intervention_type": [
        ("biopsy", "Biopsy", 10),
        ("hemostasis", "Hemostasis", 20),
        ("dilatation", "Stricture dilatation", 30),
        ("tattoo", "Tattoo", 40),
        ("polypectomy", "Polypectomy", 50),
        ("other", "Other", 99),
    ],
}
