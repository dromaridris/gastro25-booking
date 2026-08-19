"""Colonoscopy v2 structured report — vocabulary seed data."""

COLONOSCOPY_V2_VOCABULARY_SEED = {
    "colonoscopy_indication_category": [
        ("screening", "Screening", 10),
        ("surveillance", "Surveillance", 20),
        ("symptoms", "Symptoms (bleeding, change in bowel habit, pain)", 30),
        ("polyp", "Polyp follow-up / polypectomy", 40),
        ("ibd", "IBD surveillance", 50),
        ("anaemia", "Iron deficiency anaemia", 60),
        ("other", "Other / specify in detail", 99),
    ],
    "colonoscopy_scope_type": [
        ("standard_colonoscope", "Standard colonoscope", 10),
        ("paediatric_colonoscope", "Paediatric colonoscope", 20),
        ("variable_stiffness", "Variable stiffness colonoscope", 30),
    ],
    "bbps_score": [
        ("0", "0 — Unprepared", 10),
        ("1", "1 — Portion of mucosa seen", 20),
        ("2", "2 — Minor residual staining", 30),
        ("3", "3 — Entire mucosa well seen", 40),
    ],
    "bowel_prep_regimen": [
        ("peg", "PEG-based prep", 10),
        ("sodium_picosulfate", "Sodium picosulfate", 20),
        ("enema", "Enema only", 30),
        ("other", "Other", 99),
    ],
    "colonic_finding_type": [
        ("normal", "Normal", 10),
        ("polyp", "Polyp", 20),
        ("mass", "Mass / lesion", 30),
        ("inflammation", "Inflammation / colitis", 40),
        ("diverticulosis", "Diverticulosis", 50),
        ("angiodysplasia", "Angiodysplasia", 60),
        ("stricture", "Stricture", 70),
        ("other", "Other", 99),
    ],
    "colonoscopy_intervention_type": [
        ("biopsy", "Biopsy", 10),
        ("polypectomy", "Polypectomy", 20),
        ("emr", "EMR", 30),
        ("esd", "ESD", 40),
        ("apc", "APC", 50),
        ("injection_therapy", "Injection therapy", 60),
        ("hemostasis", "Hemostasis", 70),
        ("dilatation", "Colonic dilatation", 80),
        ("foreign_body_removal", "Foreign body removal", 90),
        ("clip", "Clip placement", 100),
        ("stent", "Stent placement", 110),
        ("other", "Other", 99),
    ],
}
