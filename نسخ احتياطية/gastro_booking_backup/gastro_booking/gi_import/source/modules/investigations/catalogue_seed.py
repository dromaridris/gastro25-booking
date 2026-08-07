"""Initial investigation catalogue seed (Sprint 4A-LAB)."""

from decimal import Decimal

from app.extensions import db
from app.modules.investigations.models import (
    ITEM_TYPE_IMAGING,
    ITEM_TYPE_LAB,
    InvestigationCatalogueItem,
    InvestigationPanel,
    InvestigationPanelMember,
    VALUE_TYPE_NUMERIC,
    VALUE_TYPE_TEXT,
)

LAB_TESTS = [
    ("lab.bilirubin_total", "Total bilirubin", "lft", "µmol/L", Decimal("3"), Decimal("21")),
    ("lab.bilirubin_direct", "Direct bilirubin", "lft", "µmol/L", Decimal("0"), Decimal("8")),
    ("lab.ast", "AST", "lft", "U/L", Decimal("5"), Decimal("40")),
    ("lab.alt", "ALT", "lft", "U/L", Decimal("5"), Decimal("40")),
    ("lab.alp", "ALP", "lft", "U/L", Decimal("30"), Decimal("120")),
    ("lab.ggt", "GGT", "lft", "U/L", Decimal("5"), Decimal("50")),
    ("lab.albumin", "Albumin", "lft", "g/L", Decimal("35"), Decimal("50")),
    ("lab.creatinine", "Creatinine", "rft", "µmol/L", Decimal("60"), Decimal("110")),
    ("lab.urea", "Urea", "rft", "mmol/L", Decimal("2.5"), Decimal("7.5")),
    ("lab.sodium", "Sodium", "rft", "mmol/L", Decimal("135"), Decimal("145")),
    ("lab.potassium", "Potassium", "rft", "mmol/L", Decimal("3.5"), Decimal("5.0")),
    ("lab.inr", "INR", "coagulation", None, Decimal("0.8"), Decimal("1.2")),
    ("lab.pt", "PT", "coagulation", "s", Decimal("11"), Decimal("15")),
    ("lab.hb", "Haemoglobin", "cbc", "g/L", Decimal("120"), Decimal("160")),
    ("lab.wbc", "WBC", "cbc", "×10⁹/L", Decimal("4"), Decimal("11")),
    ("lab.platelets", "Platelets", "cbc", "×10⁹/L", Decimal("150"), Decimal("400")),
    ("lab.crp", "CRP", "inflammatory", "mg/L", Decimal("0"), Decimal("5")),
    ("lab.esr", "ESR", "inflammatory", "mm/hr", Decimal("0"), Decimal("20")),
    ("lab.amylase", "Amylase", "pancreas", "U/L", Decimal("25"), Decimal("125")),
    ("lab.lipase", "Lipase", "pancreas", "U/L", Decimal("10"), Decimal("60")),
    ("lab.afp", "AFP", "tumour_marker", "µg/L", None, None),
    ("lab.ca19_9", "CA 19-9", "tumour_marker", "U/mL", None, None),
]

IMAGING = [
    ("img.abdominal_us", "Abdominal ultrasound", "imaging_us"),
    ("img.liver_us", "Liver ultrasound", "imaging_us"),
    ("img.echocardiography", "Echocardiography", "imaging_us"),
    ("img.esophageal_manometry", "Oesophageal manometry (motility)", "imaging_motility"),
    ("img.ct_abdomen", "CT abdomen", "imaging_ct"),
    ("img.ct_pancreas", "CT pancreas protocol", "imaging_ct"),
    ("img.mrcp", "MRCP", "imaging_mr"),
    ("img.mri_liver", "MRI liver", "imaging_mr"),
    ("img.plain_cxr", "Plain chest X-ray", "imaging_xr"),
]

PANELS = {
    "panel.baseline_lft": (
        "Baseline LFT",
        "Standard liver function tests",
        ["lab.bilirubin_total", "lab.ast", "lab.alt", "lab.alp", "lab.ggt", "lab.albumin"],
    ),
    "panel.baseline_rft": (
        "Baseline RFT",
        "Renal function and electrolytes",
        ["lab.creatinine", "lab.urea", "lab.sodium", "lab.potassium"],
    ),
    "panel.coagulation": ("Coagulation", "INR and PT", ["lab.inr", "lab.pt"]),
    "panel.cbc": ("Full blood count", "Hb, WBC, platelets", ["lab.hb", "lab.wbc", "lab.platelets"]),
    "panel.pancreatitis": ("Pancreatitis panel", "Amylase and lipase", ["lab.amylase", "lab.lipase"]),
}


def seed_investigation_catalogue_if_empty() -> int:
    if InvestigationCatalogueItem.query.first() is not None:
        return ensure_missing_catalogue_items()

    code_to_item: dict[str, InvestigationCatalogueItem] = {}
    sort = 10
    for code, name, category, unit, low, high in LAB_TESTS:
        item = InvestigationCatalogueItem(
            item_type=ITEM_TYPE_LAB,
            code=code,
            name=name,
            category=category,
            default_unit=unit,
            reference_range_low=low,
            reference_range_high=high,
            value_type=VALUE_TYPE_NUMERIC if low is not None or high is not None else VALUE_TYPE_TEXT,
            sort_order=sort,
        )
        db.session.add(item)
        code_to_item[code] = item
        sort += 10

    sort = 10
    for code, name, category in IMAGING:
        item = InvestigationCatalogueItem(
            item_type=ITEM_TYPE_IMAGING,
            code=code,
            name=name,
            category=category,
            value_type=VALUE_TYPE_TEXT,
            sort_order=sort,
        )
        db.session.add(item)
        code_to_item[code] = item
        sort += 10

    db.session.flush()

    for panel_code, (panel_name, desc, member_codes) in PANELS.items():
        panel = InvestigationPanel(code=panel_code, name=panel_name, description=desc)
        db.session.add(panel)
        db.session.flush()
        for idx, member_code in enumerate(member_codes):
            db.session.add(
                InvestigationPanelMember(
                    panel_id=panel.id,
                    catalogue_item_id=code_to_item[member_code].id,
                    sort_order=(idx + 1) * 10,
                )
            )

    db.session.commit()
    return len(code_to_item) + len(PANELS)


def ensure_missing_catalogue_items() -> int:
    """Add catalogue rows introduced after initial seed (idempotent)."""
    created = 0
    sort = InvestigationCatalogueItem.query.count() * 10 + 10
    for code, name, category in IMAGING:
        if InvestigationCatalogueItem.query.filter_by(code=code).first():
            continue
        db.session.add(
            InvestigationCatalogueItem(
                item_type=ITEM_TYPE_IMAGING,
                code=code,
                name=name,
                category=category,
                value_type=VALUE_TYPE_TEXT,
                sort_order=sort,
            )
        )
        created += 1
        sort += 10
    if created:
        db.session.commit()
    return created
