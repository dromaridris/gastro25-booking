"""Gastroenterology laboratory master catalogue — categorized, searchable."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LabTest:
    code: str
    name: str
    category: str
    unit: str = ''
    ref_range: str = ''
    aliases: tuple[str, ...] = ()


def _t(category: str, slug: str, name: str, unit: str = '', ref: str = '') -> LabTest:
    return LabTest(code=f'lab.{slug}', name=name, category=category, unit=unit, ref_range=ref)


def _build_catalog() -> list[LabTest]:
    c = 'cbc'
    cbc = [
        _t(c, 'hemoglobin', 'Hemoglobin (Hb)', 'g/dL', '12–16'),
        _t(c, 'hematocrit', 'Hematocrit (Hct/PCV)', '%', '36–48'),
        _t(c, 'rbc', 'Red Blood Cell Count (RBC)', '×10¹²/L', '4.2–5.4'),
        _t(c, 'mcv', 'Mean Corpuscular Volume (MCV)', 'fL', '80–100'),
        _t(c, 'mch', 'Mean Corpuscular Hemoglobin (MCH)', 'pg', '27–33'),
        _t(c, 'mchc', 'Mean Corpuscular Hemoglobin Concentration (MCHC)', 'g/dL', '32–36'),
        _t(c, 'rdw', 'Red Cell Distribution Width (RDW)', '%', '11.5–14.5'),
        _t(c, 'wbc', 'White Blood Cell Count (WBC)', '×10⁹/L', '4–11'),
        _t(c, 'neutrophils_pct', 'Neutrophils (%)', '%', '40–75'),
        _t(c, 'lymphocytes_pct', 'Lymphocytes (%)', '%', '20–45'),
        _t(c, 'monocytes_pct', 'Monocytes (%)', '%', '2–10'),
        _t(c, 'eosinophils_pct', 'Eosinophils (%)', '%', '1–6'),
        _t(c, 'basophils_pct', 'Basophils (%)', '%', '0–2'),
        _t(c, 'anc', 'Absolute Neutrophil Count (ANC)', '×10⁹/L', '2–7'),
        _t(c, 'alc', 'Absolute Lymphocyte Count (ALC)', '×10⁹/L', '1–4'),
        _t(c, 'amc', 'Absolute Monocyte Count', '×10⁹/L', '0.2–0.8'),
        _t(c, 'aec', 'Absolute Eosinophil Count', '×10⁹/L', '0.04–0.4'),
        _t(c, 'abc', 'Absolute Basophil Count', '×10⁹/L', '0–0.1'),
        _t(c, 'platelets', 'Platelet Count (PLT)', '×10⁹/L', '150–400'),
        _t(c, 'mpv', 'Mean Platelet Volume (MPV)', 'fL', '7.5–11.5'),
        _t(c, 'pdw', 'Platelet Distribution Width (PDW)', '%', '9–17'),
        _t(c, 'pct', 'Plateletcrit (PCT)', '%', '0.17–0.35'),
    ]
    c = 'inflammatory'
    inflammatory = [
        _t(c, 'esr', 'ESR', 'mm/hr', '0–20'),
        _t(c, 'crp', 'CRP', 'mg/L', '<5'),
        _t(c, 'procalcitonin', 'Procalcitonin', 'ng/mL', '<0.5'),
    ]
    c = 'renal'
    renal = [
        _t(c, 'urea', 'Urea', 'mmol/L', '2.5–7.8'),
        _t(c, 'creatinine', 'Creatinine', 'µmol/L', '60–110'),
        _t(c, 'egfr', 'eGFR', 'mL/min/1.73m²', '>60'),
        _t(c, 'uric_acid', 'Uric acid', 'µmol/L', '200–420'),
    ]
    c = 'electrolytes'
    electrolytes = [
        _t(c, 'sodium', 'Sodium', 'mmol/L', '135–145'),
        _t(c, 'potassium', 'Potassium', 'mmol/L', '3.5–5.0'),
        _t(c, 'chloride', 'Chloride', 'mmol/L', '98–107'),
        _t(c, 'bicarbonate', 'Bicarbonate', 'mmol/L', '22–29'),
        _t(c, 'calcium', 'Calcium', 'mmol/L', '2.2–2.6'),
        _t(c, 'magnesium', 'Magnesium', 'mmol/L', '0.7–1.0'),
        _t(c, 'phosphate', 'Phosphate', 'mmol/L', '0.8–1.5'),
    ]
    c = 'glucose'
    glucose = [
        _t(c, 'rbs', 'Random Blood Sugar', 'mmol/L', '3.9–7.8'),
        _t(c, 'fbs', 'Fasting Blood Sugar', 'mmol/L', '3.9–5.6'),
        _t(c, 'hba1c', 'HbA1c', '%', '4–6'),
        _t(c, 'fasting_insulin', 'Fasting Insulin', 'mIU/L', '2–25'),
        _t(c, 'homa_ir', 'HOMA-IR', '', '<2.5'),
    ]
    c = 'liver'
    liver = [
        _t(c, 'alt', 'ALT', 'U/L', '7–56'),
        _t(c, 'ast', 'AST', 'U/L', '10–40'),
        _t(c, 'alp', 'ALP', 'U/L', '44–147'),
        _t(c, 'ggt', 'GGT', 'U/L', '9–48'),
        _t(c, 'total_bilirubin', 'Total Bilirubin', 'µmol/L', '3–21'),
        _t(c, 'direct_bilirubin', 'Direct Bilirubin', 'µmol/L', '0–8'),
        _t(c, 'indirect_bilirubin', 'Indirect Bilirubin', 'µmol/L', ''),
        _t(c, 'albumin', 'Albumin', 'g/L', '35–50'),
        _t(c, 'total_protein', 'Total Protein', 'g/L', '60–80'),
        _t(c, 'globulin', 'Globulin', 'g/L', '20–35'),
        _t(c, 'ag_ratio', 'A/G Ratio', '', '1.0–2.0'),
        _t(c, 'ldh', 'LDH', 'U/L', '140–280'),
        _t(c, 'ammonia', 'Serum Ammonia', 'µmol/L', '11–35'),
    ]
    c = 'coagulation'
    coagulation = [
        _t(c, 'pt', 'PT', 'sec', '11–13.5'),
        _t(c, 'inr', 'INR', '', '0.9–1.1'),
        _t(c, 'aptt', 'aPTT', 'sec', '25–35'),
        _t(c, 'fibrinogen', 'Fibrinogen', 'g/L', '2–4'),
        _t(c, 'factor_v', 'Factor V', '%', '50–150'),
        _t(c, 'd_dimer', 'D-Dimer', 'µg/mL', '<0.5'),
    ]
    c = 'viral_hepatitis'
    viral_hepatitis = [
        _t(c, 'hbsag', 'HBsAg', '', 'Negative'),
        _t(c, 'anti_hbs', 'Anti-HBs', '', 'Negative'),
        _t(c, 'anti_hbc_igm', 'Anti-HBc IgM', '', 'Negative'),
        _t(c, 'anti_hbc_total', 'Anti-HBc Total', '', 'Negative'),
        _t(c, 'hbeag', 'HBeAg', '', 'Negative'),
        _t(c, 'anti_hbe', 'Anti-HBe', '', 'Negative'),
        _t(c, 'hbv_dna', 'HBV DNA', 'IU/mL', 'Undetectable'),
        _t(c, 'anti_hcv', 'Anti-HCV', '', 'Negative'),
        _t(c, 'hcv_rna', 'HCV RNA', 'IU/mL', 'Undetectable'),
        _t(c, 'hcv_genotype', 'HCV Genotype', '', ''),
        _t(c, 'hav_igm', 'HAV IgM', '', 'Negative'),
        _t(c, 'hav_igg', 'HAV IgG', '', 'Negative'),
        _t(c, 'hev_igm', 'HEV IgM', '', 'Negative'),
        _t(c, 'hev_igg', 'HEV IgG', '', 'Negative'),
        _t(c, 'hev_pcr', 'HEV PCR', '', 'Negative'),
        _t(c, 'anti_hdv', 'Anti-HDV', '', 'Negative'),
        _t(c, 'hdv_rna', 'HDV RNA', 'IU/mL', 'Undetectable'),
    ]
    c = 'hiv_viral'
    hiv_viral = [
        _t(c, 'hiv_screen', 'HIV Screen', '', 'Negative'),
        _t(c, 'cmv_pcr', 'CMV PCR', '', 'Negative'),
        _t(c, 'ebv_pcr', 'EBV PCR', '', 'Negative'),
        _t(c, 'hsv_pcr', 'HSV PCR', '', 'Negative'),
    ]
    c = 'autoimmune'
    autoimmune = [
        _t(c, 'ana', 'ANA', '', 'Negative'),
        _t(c, 'asma', 'ASMA', '', 'Negative'),
        _t(c, 'ama', 'AMA', '', 'Negative'),
        _t(c, 'anti_lkm', 'Anti-LKM', '', 'Negative'),
        _t(c, 'anti_sla', 'Anti-SLA', '', 'Negative'),
        _t(c, 'panca', 'pANCA', '', 'Negative'),
        _t(c, 'canca', 'cANCA', '', 'Negative'),
    ]
    c = 'immunology'
    immunology = [
        _t(c, 'igg', 'IgG', 'g/L', '7–16'),
        _t(c, 'igm', 'IgM', 'g/L', '0.4–2.3'),
        _t(c, 'iga', 'IgA', 'g/L', '0.7–4.0'),
        _t(c, 'igg4', 'IgG4', 'g/L', '0.03–2.0'),
    ]
    c = 'iron'
    iron = [
        _t(c, 'ferritin', 'Ferritin', 'µg/L', '30–400'),
        _t(c, 'iron', 'Iron', 'µmol/L', '10–30'),
        _t(c, 'tibc', 'TIBC', 'µmol/L', '45–72'),
        _t(c, 'transferrin_sat', 'Transferrin Saturation', '%', '20–50'),
        _t(c, 'hfe_mutation', 'HFE Mutation', '', 'Negative'),
    ]
    c = 'wilson'
    wilson = [
        _t(c, 'ceruloplasmin', 'Ceruloplasmin', 'g/L', '0.2–0.6'),
        _t(c, 'serum_copper', 'Serum Copper', 'µmol/L', '11–22'),
        _t(c, 'urinary_copper_24h', '24-hour Urinary Copper', 'µmol/24h', '<0.6'),
    ]
    c = 'a1at'
    a1at = [
        _t(c, 'a1at_level', 'Alpha-1 Antitrypsin Level', 'g/L', '0.9–2.0'),
        _t(c, 'a1at_phenotype', 'Alpha-1 Antitrypsin Phenotype', '', ''),
        _t(c, 'a1at_genotype', 'Alpha-1 Antitrypsin Genotype', '', ''),
    ]
    c = 'metabolic'
    metabolic = [
        _t(c, 'triglycerides', 'Triglycerides', 'mmol/L', '<1.7'),
        _t(c, 'total_cholesterol', 'Total Cholesterol', 'mmol/L', '<5.2'),
        _t(c, 'ldl', 'LDL', 'mmol/L', '<3.0'),
        _t(c, 'hdl', 'HDL', 'mmol/L', '>1.0'),
    ]
    c = 'tumor_markers'
    tumor_markers = [
        _t(c, 'afp', 'AFP', 'IU/mL', '<10'),
        _t(c, 'ca19_9', 'CA19-9', 'U/mL', '<37'),
        _t(c, 'cea', 'CEA', 'µg/L', '<5'),
        _t(c, 'ca125', 'CA125', 'U/mL', '<35'),
        _t(c, 'ca72_4', 'CA72-4', 'U/mL', '<6.9'),
    ]
    c = 'pancreatic'
    pancreatic = [
        _t(c, 'amylase', 'Serum Amylase', 'U/L', '28–100'),
        _t(c, 'lipase', 'Serum Lipase', 'U/L', '13–60'),
        _t(c, 'fecal_elastase', 'Fecal Elastase', 'µg/g', '>200'),
    ]
    c = 'nutrition'
    nutrition = [
        _t(c, 'vitamin_a', 'Vitamin A', 'µmol/L', '1.05–2.8'),
        _t(c, 'vitamin_d', 'Vitamin D', 'nmol/L', '50–125'),
        _t(c, 'vitamin_e', 'Vitamin E', 'µmol/L', '12–46'),
        _t(c, 'vitamin_k', 'Vitamin K', 'nmol/L', '0.15–1.0'),
        _t(c, 'vitamin_b12', 'Vitamin B12', 'pmol/L', '133–675'),
        _t(c, 'folate', 'Folate', 'nmol/L', '>7'),
        _t(c, 'zinc', 'Zinc', 'µmol/L', '10–18'),
        _t(c, 'prealbumin', 'Prealbumin', 'mg/dL', '20–40'),
        _t(c, 'must_score', 'MUST Score', '', ''),
        _t(c, 'nrs2002', 'NRS-2002', '', ''),
    ]
    c = 'stool'
    stool = [
        _t(c, 'fecal_calprotectin', 'Fecal Calprotectin', 'µg/g', '<50'),
        _t(c, 'fecal_lactoferrin', 'Fecal Lactoferrin', 'µg/mL', 'Negative'),
        _t(c, 'stool_occult_blood', 'Stool Occult Blood', '', 'Negative'),
        _t(c, 'fit', 'FIT', 'µg Hb/g', '<10'),
        _t(c, 'stool_re', 'Stool R/E', '', ''),
        _t(c, 'stool_culture', 'Stool Culture', '', 'Negative'),
        _t(c, 'stool_ova_parasites', 'Stool Ova & Parasites', '', 'Negative'),
        _t(c, 'giardia_antigen', 'Giardia Antigen', '', 'Negative'),
        _t(c, 'cdiff_pcr', 'Clostridioides difficile PCR', '', 'Negative'),
    ]
    c = 'celiac'
    celiac = [
        _t(c, 'ttg_iga', 'Anti-tTG IgA', '', 'Negative'),
        _t(c, 'total_iga', 'Total IgA', 'g/L', '0.7–4.0'),
        _t(c, 'ema', 'EMA', '', 'Negative'),
        _t(c, 'dgp', 'DGP Antibodies', '', 'Negative'),
    ]
    c = 'microbiology'
    microbiology = [
        _t(c, 'blood_culture', 'Blood Culture', '', 'Negative'),
        _t(c, 'urine_culture', 'Urine Culture', '', 'Negative'),
    ]
    c = 'ascitic_fluid'
    ascitic_fluid = [
        _t(c, 'ascites_cell_count', 'Ascitic Fluid Cell Count', '/mm³', ''),
        _t(c, 'ascites_diff', 'Ascitic Fluid Differential', '', ''),
        _t(c, 'ascites_albumin', 'Ascitic Fluid Albumin', 'g/L', ''),
        _t(c, 'ascites_protein', 'Ascitic Fluid Total Protein', 'g/L', ''),
        _t(c, 'saag', 'SAAG', 'g/L', '>1.1'),
        _t(c, 'ascites_gram', 'Ascitic Fluid Gram Stain', '', 'Negative'),
        _t(c, 'ascites_culture', 'Ascitic Fluid Culture', '', 'Negative'),
        _t(c, 'ascites_cytology', 'Ascitic Fluid Cytology', '', 'Negative'),
        _t(c, 'ascites_ada', 'Ascitic Fluid ADA', 'U/L', ''),
        _t(c, 'ascites_amylase', 'Ascitic Fluid Amylase', 'U/L', ''),
        _t(c, 'ascites_triglycerides', 'Ascitic Fluid Triglycerides', 'mmol/L', ''),
    ]
    c = 'pleural_fluid'
    pleural_fluid = [
        _t(c, 'pleural_cell_count', 'Pleural Fluid Cell Count', '/mm³', ''),
        _t(c, 'pleural_protein', 'Pleural Fluid Protein', 'g/L', ''),
        _t(c, 'pleural_ldh', 'Pleural Fluid LDH', 'U/L', ''),
    ]
    c = 'blood_bank'
    blood_bank = [
        _t(c, 'blood_group', 'Blood Group', '', ''),
        _t(c, 'crossmatch', 'Crossmatch', '', 'Compatible'),
    ]
    c = 'pregnancy'
    pregnancy = [
        _t(c, 'beta_hcg', 'β-hCG', 'IU/L', ''),
    ]
    c = 'drug_metabolism'
    drug_metabolism = [
        _t(c, 'tpmt', 'TPMT', '', ''),
        _t(c, 'nudt15', 'NUDT15', '', ''),
        _t(c, 'g6pd', 'G6PD', '', 'Normal'),
    ]
    c = 'tb_screening'
    tb_screening = [
        _t(c, 'quantiferon', 'QuantiFERON TB Gold', '', 'Negative'),
    ]
    c = 'miscellaneous'
    miscellaneous = [
        _t(c, 'ace', 'ACE', 'U/L', '8–52'),
        _t(c, 'abg', 'ABG', '', ''),
    ]
    return (
        cbc + inflammatory + renal + electrolytes + glucose + liver + coagulation
        + viral_hepatitis + hiv_viral + autoimmune + immunology + iron + wilson + a1at
        + metabolic + tumor_markers + pancreatic + nutrition + stool + celiac
        + microbiology + ascitic_fluid + pleural_fluid + blood_bank + pregnancy
        + drug_metabolism + tb_screening + miscellaneous
    )


LAB_CATALOG: list[LabTest] = _build_catalog()
LAB_BY_CODE: dict[str, LabTest] = {t.code: t for t in LAB_CATALOG}

LAB_CATEGORY_LABELS: dict[str, str] = {
    'cbc': 'Complete Blood Count',
    'inflammatory': 'Inflammatory Markers',
    'renal': 'Renal Function',
    'electrolytes': 'Electrolytes',
    'glucose': 'Glucose & Metabolic',
    'liver': 'Liver Function Tests',
    'coagulation': 'Coagulation',
    'viral_hepatitis': 'Viral Hepatitis',
    'hiv_viral': 'HIV & Other Viral Infections',
    'autoimmune': 'Autoimmune Liver Disease',
    'immunology': 'Immunology',
    'iron': 'Iron Studies',
    'wilson': 'Wilson Disease',
    'a1at': 'Alpha-1 Antitrypsin',
    'metabolic': 'Metabolic Syndrome',
    'tumor_markers': 'Tumor Markers',
    'pancreatic': 'Pancreatic Investigations',
    'nutrition': 'Nutritional Assessment',
    'stool': 'Stool Investigations',
    'celiac': 'Celiac Disease',
    'microbiology': 'Infection / Microbiology',
    'ascitic_fluid': 'Ascitic Fluid',
    'pleural_fluid': 'Pleural Fluid',
    'blood_bank': 'Blood Bank',
    'pregnancy': 'Pregnancy',
    'drug_metabolism': 'Drug Metabolism',
    'tb_screening': 'Tuberculosis Screening',
    'miscellaneous': 'Miscellaneous',
}


def categories_with_tests() -> list[dict]:
    by_cat: dict[str, list[LabTest]] = {}
    for test in LAB_CATALOG:
        by_cat.setdefault(test.category, []).append(test)
    out = []
    for cat_id, label in LAB_CATEGORY_LABELS.items():
        tests = sorted(by_cat.get(cat_id, []), key=lambda t: t.name)
        if tests:
            out.append({'id': cat_id, 'label': label, 'tests': tests})
    return out


def search_tests(q: str = '', *, category: str = '', limit: int = 200) -> list[LabTest]:
    q = (q or '').strip().lower()
    results = []
    for test in LAB_CATALOG:
        if category and test.category != category:
            continue
        if q and q not in test.name.lower() and q not in test.code.lower():
            continue
        results.append(test)
        if len(results) >= limit:
            break
    return results


# --- Panels ---------------------------------------------------------------
# A panel groups several individual catalog tests that are conventionally
# ordered/resulted together as one composite test (e.g. a "CBC" report has
# ~20 individual parameters). Ordering still creates one lab item as usual;
# the *result-entry* screen recognises the panel (by code or by matching the
# order's free-text name, so it also works for AI-suggested orders that were
# never explicitly picked from the catalog) and opens every member field at
# once instead of a single generic "Result" box. Each filled field is still
# saved as its own gi_lab_result row, so every parameter (Hb, WBC, ANC...)
# trends independently on the Investogram.
PANELS: dict[str, dict] = {
    'cbc': {
        'code': 'panel.cbc',
        'label': 'Complete Blood Count (CBC)',
        # Matched case-insensitively against an order's item_name/item_code
        # so a generic AI-suggested "CBC" order still triggers the panel.
        'match': ['cbc', 'complete blood count', 'full blood count', 'fbc', 'lab.cbc', 'panel.cbc'],
        'codes': [
            'lab.hemoglobin', 'lab.hematocrit', 'lab.rbc', 'lab.mcv', 'lab.mch', 'lab.mchc',
            'lab.rdw', 'lab.wbc', 'lab.neutrophils_pct', 'lab.lymphocytes_pct', 'lab.monocytes_pct',
            'lab.eosinophils_pct', 'lab.basophils_pct', 'lab.anc', 'lab.alc', 'lab.amc', 'lab.aec',
            'lab.abc', 'lab.platelets', 'lab.mpv', 'lab.pdw', 'lab.pct',
        ],
    },
    'lft': {
        'code': 'panel.lft',
        'label': 'Liver Function Tests (LFTs)',
        'match': ['lft', 'lfts', 'liver function', 'liver function test', 'liver function tests', 'lab.lft', 'panel.lft'],
        'codes': [
            'lab.alt', 'lab.ast', 'lab.alp', 'lab.ggt', 'lab.total_bilirubin', 'lab.direct_bilirubin',
            'lab.indirect_bilirubin', 'lab.albumin', 'lab.total_protein', 'lab.globulin', 'lab.ag_ratio',
        ],
    },
    'ue': {
        'code': 'panel.ue',
        'label': 'Urea & Electrolytes (U&E)',
        'match': ['u&e', 'u & e', 'ue', 'urea and electrolytes', 'urea & electrolytes', 'renal profile', 'lab.ue', 'panel.ue'],
        'codes': [
            'lab.urea', 'lab.creatinine', 'lab.egfr', 'lab.sodium', 'lab.potassium',
            'lab.chloride', 'lab.bicarbonate',
        ],
    },
    'coag': {
        'code': 'panel.coag',
        'label': 'Coagulation Screen',
        'match': ['coag', 'coagulation', 'coagulation screen', 'clotting screen', 'clotting profile', 'lab.coag', 'panel.coag'],
        'codes': ['lab.pt', 'lab.inr', 'lab.aptt', 'lab.fibrinogen'],
    },
}


def find_panel(name_or_code: str) -> dict | None:
    """Match a pending order's item_name/item_code against a known panel."""
    q = (name_or_code or '').strip().lower()
    if not q:
        return None
    for panel in PANELS.values():
        if any(q == m or m in q for m in panel['match']):
            return panel
    return None


def panel_fields(panel_key: str) -> list[LabTest]:
    panel = PANELS.get(panel_key)
    if not panel:
        return []
    return [t for code in panel['codes'] if (t := LAB_BY_CODE.get(code))]


def panels_for_template() -> list[dict]:
    """JSON-serialisable panel definitions for the result-entry UI."""
    out = []
    for key, panel in PANELS.items():
        out.append({
            'key': key,
            'label': panel['label'],
            'match': panel['match'],
            'fields': [
                {'code': t.code, 'name': t.name, 'unit': t.unit, 'ref_range': t.ref_range}
                for t in panel_fields(key)
            ],
        })
    return out


def get_test(code: str) -> LabTest | None:
    return LAB_BY_CODE.get(code)
