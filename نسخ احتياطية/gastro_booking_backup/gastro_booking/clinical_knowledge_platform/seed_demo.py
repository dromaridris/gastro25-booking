"""Demo knowledge seed — Domain Gastroenterology as Domain Pack #1 content only.

No specialty logic in engine; this file is knowledge data.
"""

from __future__ import annotations

import sqlite3

from clinical_knowledge_platform import repository as repo


def seed_demo_gastroenterology(db: sqlite3.Connection, *, force: bool = False) -> dict:
    """Populate ~8 diseases + supporting graph. Idempotent via upserts."""
    existing = repo.get_domain(db, "domain.gastroenterology")
    if existing and not force and repo.list_entities(db, domain_code="domain.gastroenterology"):
        pub = repo.latest_published_release(db)
        return {"seeded": False, "reason": "already_present", "release": pub}

    repo.upsert_domain(
        db,
        code="domain.gastroenterology",
        label="Gastroenterology",
        scope_note="First Clinical Domain Pack (demo). Peer domains plug in the same schema.",
        body={"role": "demonstration_domain_pack_1"},
    )

    # Also declare a stub peer domain to prove specialty neutrality
    repo.upsert_domain(
        db,
        code="domain.cardiology",
        label="Cardiology",
        scope_note="Stub domain — empty except one symptom affinity demo entity optional.",
        body={"role": "stub_peer_domain"},
    )

    D = "domain.gastroenterology"

    def ent(code, etype, label, **kwargs):
        return repo.upsert_entity(db, code=code, entity_type=etype, label=label, domain_code=kwargs.pop("domain_code", D), **kwargs)

    def rel(rt, src, tgt, strength=None, **kw):
        return repo.upsert_relationship(db, rel_type=rt, source_code=src, target_code=tgt, strength=strength, **kw)

    # --- Symptoms ---
    for code, label, syns in [
        ("SX_abdominal_pain", "Abdominal pain", ["Belly pain", "Stomach pain"]),
        ("SX_hematemesis", "Hematemesis", ["Vomiting blood", "Blood in vomitus"]),
        ("SX_melena", "Melena", ["Black tarry stools"]),
        ("SX_jaundice", "Jaundice", ["Yellow eyes", "Icterus"]),
        ("SX_diarrhea", "Diarrhea", ["Loose stools"]),
        ("SX_heartburn", "Heartburn", ["Pyrosis"]),
        ("SX_dysphagia", "Dysphagia", ["Difficulty swallowing"]),
        ("SX_vomiting", "Vomiting", ["Emesis"]),
    ]:
        ent(code, "symptom", label, synonyms=syns)

    # Cardiology stub symptom (proves multi-domain)
    ent("SX_chest_pain", "symptom", "Chest pain", synonyms=["Thoracic pain"], domain_code="domain.cardiology")

    # --- History sections & questions ---
    for code, label in [
        ("HS_pain_characteristics", "Pain characteristics"),
        ("HS_associated_symptoms", "Associated symptoms"),
        ("HS_alarm_features", "Alarm / red flags"),
        ("HS_risk_factors", "Risk factors & exposures"),
        ("HS_bleed_characterization", "Bleed characterization"),
    ]:
        ent(code, "history_section", label)

    questions = [
        ("HQ_pain_onset", "When did the pain start?", "HS_pain_characteristics"),
        ("HQ_pain_location", "Where is the pain located?", "HS_pain_characteristics"),
        ("HQ_pain_radiation", "Does the pain radiate?", "HS_pain_characteristics"),
        ("HQ_pain_severity", "How severe is the pain (0–10)?", "HS_pain_characteristics"),
        ("HQ_fever", "Have you had fever?", "HS_associated_symptoms"),
        ("HQ_vomiting_assoc", "Have you had vomiting?", "HS_associated_symptoms"),
        ("HQ_jaundice_assoc", "Have you noticed yellow eyes or skin?", "HS_associated_symptoms"),
        ("HQ_weight_loss", "Have you had unintentional weight loss?", "HS_alarm_features"),
        ("HQ_hematemesis_rf", "Have you vomited blood?", "HS_alarm_features"),
        ("HQ_melena_rf", "Have you passed black tarry stools?", "HS_alarm_features"),
        ("HQ_nsaid", "Do you take NSAIDs or aspirin regularly?", "HS_risk_factors"),
        ("HQ_alcohol", "Do you drink alcohol regularly?", "HS_risk_factors"),
        ("HQ_known_liver", "Have you been told you have liver disease?", "HS_risk_factors"),
        ("HQ_bleed_volume", "About how much blood was there?", "HS_bleed_characterization"),
        ("HQ_bleed_color", "What colour was the blood?", "HS_bleed_characterization"),
        ("HQ_dysphagia_solids", "Is dysphagia to solids, liquids, or both?", "HS_pain_characteristics"),
        ("HQ_heartburn_posture", "Is heartburn worse lying down?", "HS_pain_characteristics"),
        ("HQ_stool_frequency", "How many stools per day?", "HS_associated_symptoms"),
        ("HQ_bloody_diarrhea", "Is there blood in the stool with diarrhea?", "HS_alarm_features"),
        ("HQ_ruq_pred", "Is pain mainly in the right upper abdomen?", "HS_pain_characteristics"),
        ("HQ_epigastric_pred", "Is pain mainly epigastric?", "HS_pain_characteristics"),
        ("HQ_back_radiation", "Does pain go through to the back?", "HS_pain_characteristics"),
    ]
    for qcode, prompt, section in questions:
        ent(qcode, "history_question", prompt, body={"prompt": prompt, "answer_type": "text"})
        rel("contains_question", section, qcode)

    # Symptom → sections
    for sx, sections in [
        ("SX_abdominal_pain", ["HS_pain_characteristics", "HS_associated_symptoms", "HS_alarm_features", "HS_risk_factors"]),
        ("SX_hematemesis", ["HS_bleed_characterization", "HS_alarm_features", "HS_risk_factors", "HS_associated_symptoms"]),
        ("SX_melena", ["HS_bleed_characterization", "HS_alarm_features", "HS_risk_factors"]),
        ("SX_jaundice", ["HS_associated_symptoms", "HS_alarm_features", "HS_risk_factors"]),
        ("SX_diarrhea", ["HS_associated_symptoms", "HS_alarm_features", "HS_risk_factors"]),
        ("SX_heartburn", ["HS_pain_characteristics", "HS_alarm_features", "HS_risk_factors"]),
        ("SX_dysphagia", ["HS_pain_characteristics", "HS_alarm_features", "HS_risk_factors"]),
        ("SX_vomiting", ["HS_associated_symptoms", "HS_alarm_features", "HS_risk_factors"]),
    ]:
        for i, hs in enumerate(sections):
            rel("priority_section_for", sx, hs, context={"order": i})

    # --- Signs ---
    for code, label in [
        ("SG_murphy", "Murphy sign"),
        ("SG_peritoneal", "Peritoneal signs"),
        ("SG_jaundice_sign", "Icteric sclera"),
        ("SG_ascites", "Ascites"),
        ("SG_tachycardia", "Tachycardia"),
        ("SG_hypotension", "Hypotension"),
    ]:
        ent(code, "sign", label)

    # --- Investigations & findings ---
    for code, label in [
        ("IX_lipase", "Serum lipase"),
        ("IX_lfts", "Liver function tests"),
        ("IX_cbc", "Complete blood count"),
        ("IX_us_abdomen", "Abdominal ultrasound"),
        ("IX_egd", "Upper endoscopy (EGD)"),
        ("IX_ct_abdomen", "CT abdomen"),
    ]:
        ent(code, "investigation", label)

    for code, label in [
        ("FD_lipase_high", "Elevated lipase"),
        ("FD_cholestatic_lft", "Cholestatic LFT pattern"),
        ("FD_anemia", "Anemia"),
        ("FD_us_cholelithiasis", "Cholelithiasis on ultrasound"),
        ("FD_us_cholecystitis", "Sonographic cholecystitis features"),
        ("FD_egd_ulcer", "Peptic ulcer on EGD"),
        ("FD_egd_varices", "Esophageal varices on EGD"),
    ]:
        ent(code, "investigation_finding", label)

    rel("produces", "IX_lipase", "FD_lipase_high")
    rel("produces", "IX_lfts", "FD_cholestatic_lft")
    rel("produces", "IX_cbc", "FD_anemia")
    rel("produces", "IX_us_abdomen", "FD_us_cholelithiasis")
    rel("produces", "IX_us_abdomen", "FD_us_cholecystitis")
    rel("produces", "IX_egd", "FD_egd_ulcer")
    rel("produces", "IX_egd", "FD_egd_varices")

    # --- Risk factors / drugs ---
    ent("RF_nsaid", "risk_factor", "NSAID / aspirin use")
    ent("RF_alcohol", "risk_factor", "Heavy alcohol use")
    ent("RF_cirrhosis", "risk_factor", "Known cirrhosis")
    ent("DR_nsaid", "drug", "NSAID")
    ent("DR_anticoagulant", "drug", "Anticoagulant", body={"dose_reminder": "Confirm indication, INR/anti-Xa context, and bleed risk before continuing."})

    # --- Pathways ---
    ent("PW_gi_bleed_unstable", "pathway", "Unstable GI bleeding pathway", body={"urgency": "emergency"})
    ent("PW_biliary_sepsis", "pathway", "Ascending cholangitis / biliary sepsis pathway", body={"urgency": "emergency"})
    ent("PW_acute_abdomen", "pathway", "Acute abdomen / peritonitis pathway", body={"urgency": "emergency"})

    # --- Diseases (8) ---
    diseases = [
        ("DX_acute_cholecystitis", "Acute cholecystitis"),
        ("DX_acute_pancreatitis", "Acute pancreatitis"),
        ("DX_cholangitis", "Acute cholangitis"),
        ("DX_peptic_ulcer", "Peptic ulcer disease"),
        ("DX_variceal_bleed", "Variceal bleeding"),
        ("DX_gerd", "Gastroesophageal reflux disease"),
        ("DX_infectious_diarrhea", "Acute infectious diarrhea"),
        ("DX_esophageal_stricture", "Esophageal stricture"),
    ]
    for code, label in diseases:
        ent(code, "disease", label, body={"definition": label})

    rel("contraindicates", "DR_nsaid", "DX_variceal_bleed", strength="strong")
    rel("associated_with", "DR_nsaid", "DR_anticoagulant", strength="weak")

    # Symptom → disease suggests
    for sx, dxs in [
        ("SX_abdominal_pain", [("DX_acute_cholecystitis", "moderate"), ("DX_acute_pancreatitis", "moderate"), ("DX_cholangitis", "weak"), ("DX_peptic_ulcer", "moderate")]),
        ("SX_hematemesis", [("DX_peptic_ulcer", "strong"), ("DX_variceal_bleed", "strong")]),
        ("SX_melena", [("DX_peptic_ulcer", "strong"), ("DX_variceal_bleed", "moderate")]),
        ("SX_jaundice", [("DX_cholangitis", "strong"), ("DX_acute_cholecystitis", "weak")]),
        ("SX_diarrhea", [("DX_infectious_diarrhea", "strong")]),
        ("SX_heartburn", [("DX_gerd", "strong"), ("DX_peptic_ulcer", "weak")]),
        ("SX_dysphagia", [("DX_esophageal_stricture", "strong"), ("DX_gerd", "weak")]),
        ("SX_vomiting", [("DX_acute_pancreatitis", "weak"), ("DX_peptic_ulcer", "weak")]),
    ]:
        for dx, strength in dxs:
            rel("suggests", sx, dx, strength=strength)

    # Question evidence effects (stored as relationships from question → disease with context answer)
    # Engine matches when evidence finding_code equals question and polarity present
    rel("supports", "HQ_ruq_pred", "DX_acute_cholecystitis", strength="moderate")
    rel("supports", "HQ_ruq_pred", "DX_cholangitis", strength="weak")
    rel("supports", "HQ_epigastric_pred", "DX_peptic_ulcer", strength="moderate")
    rel("supports", "HQ_epigastric_pred", "DX_acute_pancreatitis", strength="moderate")
    rel("supports", "HQ_back_radiation", "DX_acute_pancreatitis", strength="strong")
    rel("supports", "HQ_fever", "DX_cholangitis", strength="moderate")
    rel("supports", "HQ_fever", "DX_acute_cholecystitis", strength="weak")
    rel("supports", "HQ_fever", "DX_infectious_diarrhea", strength="weak")
    rel("supports", "HQ_nsaid", "DX_peptic_ulcer", strength="strong")
    rel("supports", "HQ_alcohol", "DX_acute_pancreatitis", strength="moderate")
    rel("supports", "HQ_alcohol", "DX_variceal_bleed", strength="weak")
    rel("supports", "HQ_known_liver", "DX_variceal_bleed", strength="strong")
    rel("supports", "HQ_hematemesis_rf", "DX_peptic_ulcer", strength="moderate")
    rel("supports", "HQ_hematemesis_rf", "DX_variceal_bleed", strength="moderate")
    rel("supports", "HQ_melena_rf", "DX_peptic_ulcer", strength="moderate")
    rel("supports", "HQ_jaundice_assoc", "DX_cholangitis", strength="strong")
    rel("supports", "HQ_heartburn_posture", "DX_gerd", strength="moderate")
    rel("supports", "HQ_dysphagia_solids", "DX_esophageal_stricture", strength="moderate")
    rel("supports", "HQ_bloody_diarrhea", "DX_infectious_diarrhea", strength="weak")
    rel("argues_against", "HQ_heartburn_posture", "DX_variceal_bleed", strength="against")

    # Signs
    rel("strongly_supports", "SG_murphy", "DX_acute_cholecystitis", strength="strong")
    rel("supports", "SG_jaundice_sign", "DX_cholangitis", strength="moderate")
    rel("supports", "SG_ascites", "DX_variceal_bleed", strength="moderate")
    rel("strongly_supports", "SG_peritoneal", "DX_peptic_ulcer", strength="moderate", context={"note": "perforation concern"})
    rel("activates", "SG_peritoneal", "PW_acute_abdomen")
    rel("activates", "SG_hypotension", "PW_gi_bleed_unstable")
    rel("activates", "SG_tachycardia", "PW_gi_bleed_unstable", context={"with": "bleed_presentation"})

    # Findings
    rel("strongly_supports", "FD_lipase_high", "DX_acute_pancreatitis", strength="very_strong")
    rel("confirms", "FD_lipase_high", "DX_acute_pancreatitis", strength="very_strong")
    rel("supports", "FD_us_cholecystitis", "DX_acute_cholecystitis", strength="strong")
    rel("supports", "FD_us_cholelithiasis", "DX_acute_cholecystitis", strength="weak")
    rel("supports", "FD_cholestatic_lft", "DX_cholangitis", strength="moderate")
    rel("supports", "FD_egd_ulcer", "DX_peptic_ulcer", strength="very_strong")
    rel("confirms", "FD_egd_ulcer", "DX_peptic_ulcer", strength="very_strong")
    rel("supports", "FD_egd_varices", "DX_variceal_bleed", strength="very_strong")
    rel("confirms", "FD_egd_varices", "DX_variceal_bleed", strength="very_strong")
    rel("supports", "FD_anemia", "DX_peptic_ulcer", strength="weak")
    rel("supports", "FD_anemia", "DX_variceal_bleed", strength="weak")

    # Risk factors
    rel("supports", "RF_nsaid", "DX_peptic_ulcer", strength="moderate")
    rel("supports", "RF_alcohol", "DX_acute_pancreatitis", strength="moderate")
    rel("supports", "RF_cirrhosis", "DX_variceal_bleed", strength="strong")

    # Investigations
    for dx, ixs in [
        ("DX_acute_cholecystitis", ["IX_us_abdomen", "IX_cbc", "IX_lfts"]),
        ("DX_acute_pancreatitis", ["IX_lipase", "IX_cbc", "IX_ct_abdomen"]),
        ("DX_cholangitis", ["IX_lfts", "IX_cbc", "IX_us_abdomen"]),
        ("DX_peptic_ulcer", ["IX_cbc", "IX_egd"]),
        ("DX_variceal_bleed", ["IX_cbc", "IX_egd", "IX_lfts"]),
        ("DX_gerd", ["IX_egd"]),
        ("DX_infectious_diarrhea", ["IX_cbc"]),
        ("DX_esophageal_stricture", ["IX_egd"]),
    ]:
        for ix in ixs:
            rel("investigated_by", dx, ix)

    # Management stubs
    for code, label in [
        ("MX_npo_fluids", "NPO and IV fluids"),
        ("MX_ppi", "Proton pump inhibitor therapy"),
        ("MX_urgent_egd", "Urgent upper endoscopy"),
        ("MX_abx_biliary", "IV antibiotics for biliary infection"),
        ("MX_cholecystectomy_ref", "Surgical referral for cholecystectomy"),
    ]:
        ent(code, "management_action", label)

    rel("managed_by", "DX_acute_pancreatitis", "MX_npo_fluids")
    rel("managed_by", "DX_peptic_ulcer", "MX_ppi")
    rel("managed_by", "DX_peptic_ulcer", "MX_urgent_egd")
    rel("managed_by", "DX_variceal_bleed", "MX_urgent_egd")
    rel("managed_by", "DX_cholangitis", "MX_abx_biliary")
    rel("managed_by", "DX_acute_cholecystitis", "MX_cholecystectomy_ref")
    rel("managed_by", "PW_gi_bleed_unstable", "MX_urgent_egd")
    rel("managed_by", "PW_biliary_sepsis", "MX_abx_biliary")

    # Fever+jaundice+pain → cholangitis pathway (knowledge declares activation from findings constellation via individual edges)
    rel("activates", "HQ_fever", "PW_biliary_sepsis", context={"requires_all": ["HQ_jaundice_assoc"]})
    rel("activates", "FD_cholestatic_lft", "PW_biliary_sepsis")

    # Discriminators
    rel("discriminates", "HQ_ruq_pred", "DX_acute_cholecystitis", context={"vs": ["DX_peptic_ulcer", "DX_acute_pancreatitis"]})
    rel("discriminates", "HQ_back_radiation", "DX_acute_pancreatitis", context={"vs": ["DX_peptic_ulcer"]})
    rel("discriminates", "HQ_known_liver", "DX_variceal_bleed", context={"vs": ["DX_peptic_ulcer"]})

    # Complications
    ent("DX_ulcer_perforation", "disease", "Perforated peptic ulcer")
    rel("complication_of", "DX_ulcer_perforation", "DX_peptic_ulcer")
    rel("activates", "SG_peritoneal", "PW_acute_abdomen")

    # Guidelines
    repo.upsert_guideline_work(
        db,
        code="GW_demo_society_gi_2024",
        society="DEMO-GI-SOCIETY",
        title="Demo GI Practice Assertions 2024",
        year=2024,
        scope_note="Synthetic assertions for platform demo — not clinical guidance.",
    )
    repo.upsert_guideline_assertion(
        db,
        code="GA_demo_unstable_bleed_egd",
        work_code="GW_demo_society_gi_2024",
        statement="Unstable upper GI bleeding warrants urgent endoscopic evaluation after resuscitation.",
        strength="strong",
        applies_to=["PW_gi_bleed_unstable", "MX_urgent_egd"],
    )
    repo.upsert_guideline_assertion(
        db,
        code="GA_demo_lipase_pancreatitis",
        work_code="GW_demo_society_gi_2024",
        statement="Markedly elevated lipase supports diagnosis of acute pancreatitis in compatible clinical context.",
        strength="strong",
        applies_to=["FD_lipase_high", "DX_acute_pancreatitis"],
    )
    # Also store assertions as entities for graph bound_by targets if needed
    ent("GA_demo_unstable_bleed_egd", "guideline_assertion", "Unstable bleed → urgent EGD assertion")
    ent("GA_demo_lipase_pancreatitis", "guideline_assertion", "Lipase supports pancreatitis assertion")
    rel("bound_by", "PW_gi_bleed_unstable", "GA_demo_unstable_bleed_egd")
    rel("bound_by", "FD_lipase_high", "GA_demo_lipase_pancreatitis")

    # Follow-up / education stubs
    ent("FU_pancreatitis", "follow_up_scheme", "Pancreatitis follow-up", body={"interval": "as clinically indicated"})
    ent("ED_gerd_lifestyle", "education", "GERD lifestyle measures")
    rel("managed_by", "DX_acute_pancreatitis", "FU_pancreatitis")
    rel("managed_by", "DX_gerd", "ED_gerd_lifestyle")

    # Criteria / severity stubs
    ent("CR_pancreatitis_working", "diagnostic_criteria", "Working criteria for acute pancreatitis", body={"note": "compatible pain + enzyme elevation"})
    ent("SV_bleed_hemodynamic", "severity_classification", "Hemodynamic instability with bleed")
    rel("confirms", "CR_pancreatitis_working", "DX_acute_pancreatitis")

    existing_rel = repo.get_release_by_code(db, "KB-DEMO-GI-1")
    if existing_rel:
        published = repo.publish_release(db, existing_rel["id"])
    else:
        rid = repo.create_release(
            db,
            code="KB-DEMO-GI-1",
            label="Demo Knowledge Release — Gastroenterology Domain Pack #1",
            notes="Specialty-agnostic schema; GI is first domain content only.",
        )
        published = repo.publish_release(db, rid)
    db.commit()
    return {"seeded": True, "release": published, "domain": "domain.gastroenterology"}
