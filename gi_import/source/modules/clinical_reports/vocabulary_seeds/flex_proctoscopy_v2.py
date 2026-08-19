"""Flex sig and proctoscopy v2 — additional vocabulary seeds."""

FLEX_SIG_V2_VOCABULARY_SEED = {
    "flex_sig_scope_type": [
        ("flexible_sigmoidoscope", "Flexible sigmoidoscope", 10),
        ("standard_colonoscope", "Standard colonoscope (limited)", 20),
    ],
    "flex_sig_scope_limit": [
        ("rectum", "Rectum", 10),
        ("sigmoid", "Sigmoid colon", 20),
        ("descending", "Descending colon", 30),
    ],
}

PROCTOSCOPY_V2_VOCABULARY_SEED = {
    "proctoscopy_indication_category": [
        ("rectal_bleeding", "Rectal bleeding", 10),
        ("anal_pain", "Anal pain", 20),
        ("surveillance", "Surveillance", 30),
        ("other", "Other / specify in detail", 99),
    ],
    "proctoscopy_scope_type": [
        ("rigid_proctoscope", "Rigid proctoscope", 10),
        ("flexible_proctoscope", "Flexible proctoscope / anoscope", 20),
    ],
    "proctoscopy_intervention_type": [
        ("biopsy", "Biopsy", 10),
        ("hemostasis", "Hemostasis", 20),
        ("band_ligation", "Band ligation", 30),
        ("dilatation", "Dilatation", 40),
        ("other", "Other", 99),
    ],
}
