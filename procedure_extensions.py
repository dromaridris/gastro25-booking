"""Additional endoscopy procedure types for booking — extends PROCEDURE_LABELS without modifying ERCP core."""

from __future__ import annotations

# Already in app.py PROCEDURE_LABELS (standard / ERCP / special):
# upper_gi, colonoscopy, peg_tube, ercp, dilatation, polypectomy

# Advanced endoscopy — restricted to CAN_BOOK_ERCP roles (Admin, Specialist, Nurse Manager, Consultant, HOD).
# Covers GI catalogue procedures not in the standard booking list above.
ADVANCED_PROCEDURE_LABELS = {
    'sigmoidoscopy': 'Flexible Sigmoidoscopy',
    'proctoscopy': 'Proctoscopy',
    'eus': 'EUS (Endoscopic Ultrasound)',
    'capsule_endoscopy': 'Capsule Endoscopy',
    'enteroscopy': 'Enteroscopy (DBE / SBE)',
    'balloon_dilatation': 'Balloon Dilatation',
    'esophageal_dilatation': 'Esophageal Dilatation',
    'variceal_band_ligation': 'Variceal Band Ligation (EVL)',
    'sclerotherapy': 'Sclerotherapy',
    'emr': 'EMR (Endoscopic Mucosal Resection)',
    'esd': 'ESD (Endoscopic Submucosal Dissection)',
    'stent_placement': 'Endoscopic Stent Placement',
    'liver_biopsy': 'Liver Biopsy (EUS / TJLB)',
    'fibroscan': 'FibroScan (Transient Elastography)',
}

ADVANCED_PROCEDURES = tuple(ADVANCED_PROCEDURE_LABELS.keys())

# Backward-compatible aliases used by migration bootstrap / registry.
EXTENDED_PROCEDURE_LABELS = ADVANCED_PROCEDURE_LABELS
EXTENDED_SPECIAL_PROCEDURES = ()  # deprecated — advanced uses ADVANCED_PROCEDURES + ERCP-tier roles


def merge_procedure_labels(base_labels: dict) -> dict:
    merged = dict(base_labels)
    merged.update(ADVANCED_PROCEDURE_LABELS)
    return merged


def booking_procedure_groups(all_labels: dict) -> dict:
    """Split labels for the New Booking modal optgroups."""
    standard_keys = ('upper_gi', 'colonoscopy', 'peg_tube')
    special_keys = ('dilatation', 'polypectomy')
    return {
        'standard': [(k, all_labels[k]) for k in standard_keys if k in all_labels],
        'special': [(k, all_labels[k]) for k in special_keys if k in all_labels],
        'advanced': [(k, all_labels[k]) for k in ADVANCED_PROCEDURES if k in all_labels],
    }
