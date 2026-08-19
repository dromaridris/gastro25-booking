"""
Standard endoscopy report template definitions — Sprint 3B.

Two reusable templates only: Upper GI Endoscopy and Colonoscopy.
Template selection reads ProcedureType.report_template_key (stable
catalogue category) — never the display name.
"""

from app.modules.procedures.models import (
    ALL_REPORT_TEMPLATE_KEYS,
    REPORT_TEMPLATE_KEY_COLONOSCOPY,
    REPORT_TEMPLATE_KEY_UPPER_GI,
)
from app.modules.reports.models import (
    SECTION_CLINICAL_INDICATION,
    SECTION_COMPLICATIONS,
    SECTION_FINDINGS,
    SECTION_IMPRESSION,
    SECTION_PROCEDURE_DESCRIPTION,
    SECTION_RECOMMENDATIONS,
)

TEMPLATE_COLONOSCOPY = REPORT_TEMPLATE_KEY_COLONOSCOPY
TEMPLATE_UPPER_GI = REPORT_TEMPLATE_KEY_UPPER_GI

ALL_TEMPLATE_KEYS = list(ALL_REPORT_TEMPLATE_KEYS)

TEMPLATE_LABELS = {
    TEMPLATE_COLONOSCOPY: "Colonoscopy Report",
    TEMPLATE_UPPER_GI: "Upper GI Endoscopy Report",
}

FINDINGS_MARKER_COLONOSCOPY = "--- COLONOSCOPY FINDINGS ---"
FINDINGS_MARKER_UPPER_GI = "--- UPPER GI FINDINGS ---"
FINDINGS_MARKER_END = "--- END ---"


def resolve_template_key(procedure_type) -> str | None:
    """Return template key from ProcedureType.report_template_key, else None."""
    if procedure_type is None:
        return None
    key = getattr(procedure_type, "report_template_key", None)
    if key in ALL_TEMPLATE_KEYS:
        return key
    return None


def scaffold_for(template_key: str, section_key: str) -> str:
    scaffolds = _SCAFFOLDS.get(template_key, {})
    return scaffolds.get(section_key, "")


_SCAFFOLDS = {
    TEMPLATE_COLONOSCOPY: {
        SECTION_CLINICAL_INDICATION: (
            "Indication for colonoscopy:\n"
            "(e.g. screening, surveillance, symptoms, polyp follow-up)\n"
        ),
        SECTION_PROCEDURE_DESCRIPTION: (
            "Under sedation, a colonoscope was inserted via the anus and advanced to "
            "the caecum / terminal ileum.\n"
            "Caecum intubation: \n"
            "Withdrawal time (minutes): \n"
            "Bowel preparation regimen: \n"
        ),
        SECTION_FINDINGS: (
            f"{FINDINGS_MARKER_COLONOSCOPY}\n"
            "Caecum reached: \n"
            "Terminal ileum intubated: \n"
            "BBPS: Right — / Transverse — / Left —\n"
            "Withdrawal time (minutes): \n"
            "\nPolyp findings:\n\n"
            "Mucosal findings:\n\n"
            "Other findings:\n"
            f"{FINDINGS_MARKER_END}\n"
        ),
        SECTION_IMPRESSION: "Impression:\n",
        SECTION_RECOMMENDATIONS: (
            "Recommendations / follow-up:\n"
            "(e.g. surveillance interval, histology pending, repeat procedure)\n"
        ),
        SECTION_COMPLICATIONS: "Immediate complications: None.\n",
    },
    TEMPLATE_UPPER_GI: {
        SECTION_CLINICAL_INDICATION: (
            "Indication for upper GI endoscopy:\n"
            "(e.g. dyspepsia, GI bleeding, dysphagia, anaemia, Barrett surveillance)\n"
        ),
        SECTION_PROCEDURE_DESCRIPTION: (
            "Under sedation, a gastroscope was inserted orally and advanced to the "
            "duodenum (D2).\n"
            "D2 reached: \n"
            "Retroflexion in stomach performed: \n"
        ),
        SECTION_FINDINGS: (
            f"{FINDINGS_MARKER_UPPER_GI}\n"
            "Oesophagus:\n\n"
            "Stomach:\n\n"
            "Duodenum:\n\n"
            "D2 reached: \n"
            "\nOther findings:\n"
            f"{FINDINGS_MARKER_END}\n"
        ),
        SECTION_IMPRESSION: "Impression:\n",
        SECTION_RECOMMENDATIONS: (
            "Recommendations / follow-up:\n"
            "(e.g. PPI therapy, H. pylori testing, repeat endoscopy)\n"
        ),
        SECTION_COMPLICATIONS: "Immediate complications: None.\n",
    },
}
