"""Initial medication formulary seed (Sprint 4B-MED)."""

from app.extensions import db
from app.modules.medications.models import MedicationCatalogueItem

MEDICATIONS = [
    ("med.omeprazole", "Omeprazole", "Omeprazole", "ppi", "oral", "tablet"),
    ("med.pantoprazole", "Pantoprazole", "Pantoprazole", "ppi", "oral", "tablet"),
    ("med.lansoprazole", "Lansoprazole", "Lansoprazole", "ppi", "oral", "capsule"),
    ("med.mesalazine", "Mesalazine", "Mesalazine", "aminosalicylate", "oral", "tablet"),
    ("med.sulfasalazine", "Sulfasalazine", "Sulfasalazine", "aminosalicylate", "oral", "tablet"),
    ("med.azathioprine", "Azathioprine", "Azathioprine", "immunomodulator", "oral", "tablet"),
    ("med.mercaptopurine", "Mercaptopurine", "Mercaptopurine", "immunomodulator", "oral", "tablet"),
    ("med.methotrexate", "Methotrexate", "Methotrexate", "immunomodulator", "oral", "tablet"),
    ("med.prednisolone", "Prednisolone", "Prednisolone", "steroid", "oral", "tablet"),
    ("med.budesonide", "Budesonide", "Budesonide", "steroid", "oral", "capsule"),
    ("med.ursodeoxycholic_acid", "Ursodeoxycholic acid", "UDCA", "hepatology", "oral", "capsule"),
    ("med.lactulose", "Lactulose", "Lactulose", "laxative", "oral", "solution"),
    ("med.rifaximin", "Rifaximin", "Rifaximin", "antibiotic", "oral", "tablet"),
    ("med.ciprofloxacin", "Ciprofloxacin", "Ciprofloxacin", "antibiotic", "oral", "tablet"),
    ("med.metronidazole", "Metronidazole", "Metronidazole", "antibiotic", "oral", "tablet"),
    ("med.spironolactone", "Spironolactone", "Spironolactone", "diuretic", "oral", "tablet"),
    ("med.furosemide", "Furosemide", "Furosemide", "diuretic", "oral", "tablet"),
    ("med.carvedilol", "Carvedilol", "Carvedilol", "beta_blocker", "oral", "tablet"),
    ("med.propranolol", "Propranolol", "Propranolol", "beta_blocker", "oral", "tablet"),
    ("med.terlipressin", "Terlipressin", "Terlipressin", "vasopressor", "iv", "infusion"),
    ("med.albumin_infusion", "Human albumin solution", "Albumin", "hepatology", "iv", "infusion"),
    ("med.paracetamol", "Paracetamol", "Paracetamol", "analgesic", "oral", "tablet"),
]


def seed_medication_catalogue_if_empty() -> int:
    if MedicationCatalogueItem.query.first() is not None:
        return 0

    sort = 10
    for code, name, generic, category, route, form in MEDICATIONS:
        db.session.add(
            MedicationCatalogueItem(
                code=code,
                name=name,
                generic_name=generic,
                category=category,
                default_route=route,
                default_form=form,
                sort_order=sort,
            )
        )
        sort += 10
    db.session.commit()
    return len(MEDICATIONS)
