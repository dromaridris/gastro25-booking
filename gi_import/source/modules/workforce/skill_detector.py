"""Structured procedural skill detection from report payloads — Sprint 7A."""

from __future__ import annotations

from dataclasses import dataclass

from app.modules.clinical_reports.models import ClinicalReportDocument
from app.modules.reports.models import Report, ReportSection

# Template key → intervention repeatable field paths in payload v2 fields
INTERVENTION_FIELD_PATHS: dict[str, list[str]] = {
    "ercp": ["ercp.therapy.interventions"],
    "colonoscopy_v2": ["colonoscopy_v2.interventions.interventions"],
    "upper_gi_v2": ["upper_gi_v2.interventions.interventions"],
    "flex_sig_v2": ["flex_sig_v2.interventions.interventions"],
    "proctoscopy_v2": ["proctoscopy_v2.interventions.interventions"],
    "enteroscopy": ["enteroscopy.therapy.interventions"],
    "eus": [],
}

# Raw intervention / field codes → canonical competency skill codes
INTERVENTION_TO_SKILL: dict[str, str] = {
    "biopsy": "skill.general.biopsy",
    "polypectomy": "skill.general.polypectomy",
    "emr": "skill.general.emr",
    "esd": "skill.general.emr",
    "tattoo": "skill.general.tattooing",
    "hemostasis": "skill.general.hemostasis",
    "peg": "skill.general.peg",
    "peg_replacement": "skill.general.peg",
    "dilatation": "skill.general.dilatation",
    "sphincterotomy": "skill.ercp.sphincterotomy",
    "stone_extraction": "skill.ercp.stone_extraction",
    "balloon_dilation": "skill.ercp.balloon_sphincteroplasty",
    "biliary_stent": "skill.ercp.plastic_stent",
    "pancreatic_stent": "skill.ercp.pancreatic_stent",
    "brush_cytology": "skill.ercp.brush_cytology",
    "fna": "skill.eus.fna",
    "fnb": "skill.eus.fnb",
    "cyst_drainage": "skill.eus.drainage",
    "celiac_block": "skill.eus.celiac_block",
}

# Legacy generic report section keyword scan (Sprint 3A/3B text reports)
KEYWORD_SKILL_MAP: dict[str, list[str]] = {
    "skill.general.biopsy": ["biopsy", "biopsies", "biopsied"],
    "skill.general.polypectomy": ["polypectomy", "polyp removed", "snare polypectomy", "cold snare", "hot snare"],
    "skill.general.emr": ["emr", "endoscopic mucosal resection"],
    "skill.general.tattooing": ["tattoo", "tattooing", "india ink"],
    "skill.general.hemostasis": ["hemostasis", "haemostasis", "injection therapy", "haemoclip", "hemoclip"],
    "skill.general.peg": ["peg insertion", "peg placed", "percutaneous endoscopic gastrostomy"],
    "skill.general.dilatation": ["dilatation", "dilation", "balloon dilat"],
    "skill.ercp.cannulation": ["biliary cannulation", "cannulation successful", "deep cannulation"],
    "skill.ercp.sphincterotomy": ["sphincterotomy", "papillotomy"],
    "skill.ercp.stone_extraction": ["stone extraction", "cbd stone", "choledocholithiasis"],
    "skill.ercp.plastic_stent": ["plastic stent", "biliary stent placed"],
    "skill.ercp.metal_stent": ["metal stent", "sems", "self-expanding metal stent"],
    "skill.ercp.brush_cytology": ["brush cytology", "brushings obtained"],
    "skill.ercp.pancreatic_stent": ["pancreatic stent", "pd stent"],
    "skill.eus.fna": ["eus-fna", "fna performed", "fine needle aspiration"],
    "skill.eus.fnb": ["eus-fnb", "fnb performed", "fine needle biopsy"],
    "skill.eus.drainage": ["cyst drainage", "eus-guided drainage"],
    "skill.eus.celiac_block": ["celiac plexus", "celiac block"],
}


@dataclass(frozen=True)
class DetectedSkill:
    skill_code: str
    label: str
    source: str  # structured | keyword


def _yes(value) -> bool:
    return str(value or "").strip().lower() in {"yes", "true", "1"}


def _map_intervention(code: str, details: str = "") -> str | None:
    code_l = (code or "").strip().lower()
    details_l = (details or "").lower()
    if code_l == "biliary_stent":
        if "metal" in details_l or "sems" in details_l:
            return "skill.ercp.metal_stent"
        return "skill.ercp.plastic_stent"
    if code_l == "fna":
        if "fnb" in details_l or "core" in details_l:
            return "skill.eus.fnb"
        return "skill.eus.fna"
    return INTERVENTION_TO_SKILL.get(code_l)


def _rows_from_field(fields: dict, path: str) -> list[dict]:
    value = fields.get(path)
    if isinstance(value, list):
        return [r for r in value if isinstance(r, dict)]
    return []


def detect_skills_from_document(document: ClinicalReportDocument) -> list[DetectedSkill]:
    """Extract skills from structured clinical report payload."""
    payload = document.get_payload()
    fields = payload.get("fields", {}) if isinstance(payload, dict) else {}
    template = document.template_key or ""
    found: dict[str, DetectedSkill] = {}

    for path in INTERVENTION_FIELD_PATHS.get(template, []):
        for row in _rows_from_field(fields, path):
            itype = row.get("intervention_type") or row.get("type")
            success = row.get("success")
            if success and not _yes(success):
                continue
            skill = _map_intervention(str(itype or ""), str(row.get("details") or ""))
            if skill:
                found[skill] = DetectedSkill(skill_code=skill, label=skill, source="structured")

    if template == "ercp":
        if _yes(fields.get("ercp.access.cannulation_success")):
            found["skill.ercp.cannulation"] = DetectedSkill(
                skill_code="skill.ercp.cannulation", label="Biliary cannulation", source="structured"
            )
        if _yes(fields.get("ercp.access.precut_performed")):
            found["skill.ercp.sphincterotomy"] = DetectedSkill(
                skill_code="skill.ercp.sphincterotomy", label="Precut sphincterotomy", source="structured"
            )

    if template == "eus":
        if _yes(fields.get("eus.sampling.fna_performed")):
            needle = str(fields.get("eus.sampling.needle_type") or "").lower()
            if "fnb" in needle or "core" in needle or "procore" in needle:
                found["skill.eus.fnb"] = DetectedSkill(skill_code="skill.eus.fnb", label="EUS-FNB", source="structured")
            else:
                found["skill.eus.fna"] = DetectedSkill(skill_code="skill.eus.fna", label="EUS-FNA", source="structured")

    return list(found.values())


def detect_skills_from_generic_report(report: Report) -> list[DetectedSkill]:
    """Keyword scan of generic / legacy template report sections."""
    text_parts: list[str] = []
    for section in ReportSection.query.filter_by(report_id=report.id, is_archived=False).all():
        text_parts.append(section.content or "")
    blob = " ".join(text_parts).lower()
    if not blob.strip():
        return []

    found: dict[str, DetectedSkill] = {}
    for skill_code, keywords in KEYWORD_SKILL_MAP.items():
        if any(kw in blob for kw in keywords):
            found[skill_code] = DetectedSkill(skill_code=skill_code, label=skill_code, source="keyword")
    return list(found.values())


def detect_skills_for_report(report: Report) -> list[DetectedSkill]:
    """Unified skill detection — clinical structured reports first, then generic fallback."""
    document = ClinicalReportDocument.query.filter_by(report_id=report.id, is_archived=False).first()
    if document is not None:
        skills = detect_skills_from_document(document)
        if skills:
            return skills
    return detect_skills_from_generic_report(report)
