"""Configurable competency standards — Sprint 7A seed data."""

from app.modules.workforce.constants import (
    COMPETENCY_COLONOSCOPY,
    COMPETENCY_ERCP,
    COMPETENCY_EUS,
    COMPETENCY_UPPER_GI,
    STATUS_COMPETENT,
    STATUS_IN_PROGRESS,
    STATUS_NOT_STARTED,
)

# (code, name, specialty, required_count, sort_order)
COMPETENCY_STANDARDS_SEED = [
    # General endoscopy
    ("skill.general.biopsy", "Biopsy", COMPETENCY_UPPER_GI, 20, 10),
    ("skill.general.polypectomy", "Polypectomy", COMPETENCY_COLONOSCOPY, 30, 20),
    ("skill.general.emr", "EMR", COMPETENCY_COLONOSCOPY, 10, 30),
    ("skill.general.tattooing", "Tattooing", COMPETENCY_COLONOSCOPY, 5, 40),
    ("skill.general.hemostasis", "Hemostasis", COMPETENCY_UPPER_GI, 15, 50),
    ("skill.general.peg", "PEG insertion", COMPETENCY_UPPER_GI, 5, 60),
    ("skill.general.dilatation", "Dilatation", COMPETENCY_UPPER_GI, 10, 70),
    # ERCP
    ("skill.ercp.cannulation", "Biliary cannulation", COMPETENCY_ERCP, 50, 110),
    ("skill.ercp.sphincterotomy", "Sphincterotomy", COMPETENCY_ERCP, 30, 120),
    ("skill.ercp.balloon_sphincteroplasty", "Balloon sphincteroplasty", COMPETENCY_ERCP, 15, 130),
    ("skill.ercp.stone_extraction", "Stone extraction", COMPETENCY_ERCP, 25, 140),
    ("skill.ercp.plastic_stent", "Plastic stent placement", COMPETENCY_ERCP, 20, 150),
    ("skill.ercp.metal_stent", "Metal stent placement", COMPETENCY_ERCP, 10, 160),
    ("skill.ercp.stricture_dilatation", "Stricture dilatation", COMPETENCY_ERCP, 15, 170),
    ("skill.ercp.brush_cytology", "Brush cytology", COMPETENCY_ERCP, 10, 180),
    ("skill.ercp.pancreatic_stent", "Pancreatic stent", COMPETENCY_ERCP, 15, 190),
    # EUS
    ("skill.eus.fna", "EUS-FNA", COMPETENCY_EUS, 25, 210),
    ("skill.eus.fnb", "EUS-FNB", COMPETENCY_EUS, 20, 220),
    ("skill.eus.drainage", "EUS-guided drainage", COMPETENCY_EUS, 10, 230),
    ("skill.eus.celiac_block", "Celiac plexus block", COMPETENCY_EUS, 5, 240),
]


def competency_status(completed: int, required: int) -> str:
    if completed <= 0:
        return STATUS_NOT_STARTED
    if completed >= required:
        return STATUS_COMPETENT
    return STATUS_IN_PROGRESS
