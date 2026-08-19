"""Bridge notes between legacy ward history (gi_*) and Clinical Intelligence (ci_*).

Physician surface of record: Ward Clinical Workflow (unified encounter).
CI remains available for knowledge training / research — not a competing care path.
"""

from __future__ import annotations

import json
from datetime import datetime

# Best-effort map from legacy catalogue complaint codes → CI CC_* packs.
# Disease/syndrome legacy labels map to the closest Bates *symptom* pack.
LEGACY_COMPLAINT_TO_CI: dict[str, str] = {
    # GI
    "hist.abdominal_pain": "CC_abdominal_pain",
    "hist.epigastric_pain": "CC_abdominal_pain",
    "hist.biliary_pain": "CC_abdominal_pain",
    "hist.pancreatitis": "CC_abdominal_pain",
    "hist.abdominal_distension": "CC_abdominal_distention",
    "hist.abdominal_distention": "CC_abdominal_distention",
    "hist.ascites": "CC_abdominal_distention",
    "hist.bloating": "CC_abdominal_distention",
    "hist.heartburn": "CC_heartburn",
    "hist.gerd": "CC_heartburn",
    "hist.reflux": "CC_heartburn",
    "hist.dyspepsia": "CC_heartburn",
    "hist.dysphagia": "CC_dysphagia",
    "hist.odynophagia": "CC_dysphagia",
    "hist.vomiting": "CC_vomiting",
    "hist.nausea": "CC_vomiting",
    "hist.anorexia": "CC_anorexia",
    "hist.early_satiety": "CC_anorexia",
    "hist.weight_loss": "CC_weight_loss",
    "hist.weight_gain": "CC_weight_gain",
    "hist.diarrhea": "CC_diarrhea",
    "hist.loose_stools": "CC_diarrhea",
    "hist.constipation": "CC_constipation",
    "hist.jaundice": "CC_jaundice",
    "hist.pruritus": "CC_pruritus",
    "hist.itching": "CC_pruritus",
    "hist.food_intolerance": "CC_food_intolerance",
    "hist.anal_pain": "CC_anal_pain",
    "hist.fecal_incontinence": "CC_fecal_incontinence",
    # Bleeding symptoms (never keep UGIB/LGIB as CI complaint)
    "hist.upper_gi_bleeding": "CC_hematemesis",
    "hist.lower_gi_bleeding": "CC_hematochezia",
    "hist.hematemesis": "CC_hematemesis",
    "hist.melena": "CC_melena",
    "hist.hematochezia": "CC_hematochezia",
    "hist.rectal_bleeding": "CC_hematochezia",
    # Cardio-resp / constitutional
    "hist.chest_pain": "CC_chest_pain",
    "hist.dyspnea": "CC_dyspnea",
    "hist.shortness_of_breath": "CC_dyspnea",
    "hist.cough": "CC_cough",
    "hist.hemoptysis": "CC_hemoptysis",
    "hist.palpitations": "CC_palpitations",
    "hist.edema": "CC_edema",
    "hist.leg_swelling": "CC_edema",
    "hist.syncope": "CC_syncope",
    "hist.dizziness": "CC_dizziness",
    "hist.vertigo": "CC_dizziness",
    "hist.headache": "CC_headache",
    "hist.fever": "CC_fever",
    "hist.fatigue": "CC_fatigue",
    "hist.back_pain": "CC_back_pain",
    # GU (Bates abdomen)
    "hist.flank_pain": "CC_flank_pain",
    "hist.dysuria": "CC_dysuria",
    "hist.hematuria": "CC_hematuria",
    "hist.uti": "CC_dysuria",
}


def map_legacy_complaint_to_ci(complaint_code: str | None) -> str | None:
    """Return a CI complaint_code if a reasonable mapping exists."""
    code = (complaint_code or "").strip()
    if not code:
        return None
    if code.startswith("CC_"):
        return code
    mapped = LEGACY_COMPLAINT_TO_CI.get(code)
    if mapped:
        return mapped
    # hist.foo_bar → try CC_foo_bar
    slug = code
    if slug.startswith("hist."):
        slug = slug[5:]
    slug = slug.replace("-", "_").lower()
    candidate = f"CC_{slug}"
    return candidate


def resolve_ci_complaint(complaint_code: str | None, *, has_template) -> str | None:
    """Map legacy code and verify a history template exists (has_template callable)."""
    candidate = map_legacy_complaint_to_ci(complaint_code)
    if candidate and has_template(candidate):
        return candidate
    return None


def build_export_highlights(documentation_text: str, *, encounter_id: int, complaint_code: str) -> str:
    """Format CI documentation for ward narrative / note (one-way, clinician-triggered)."""
    stamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    header = (
        f"--- Clinical Intelligence export (encounter #{encounter_id}, {complaint_code}) — {stamp} ---\n"
        "Source: structured Bates CI path (answers remain in ci_* only; not dual-written).\n\n"
    )
    body = (documentation_text or "").strip()
    if not body:
        body = "(No consultation documentation text available yet — open Consult first.)"
    return header + body + "\n--- end CI export ---"


def export_ci_summary_to_ward(
    db,
    *,
    encounter: dict,
    documentation_text: str,
    target: str = "hpi",
    user_id: int | None = None,
) -> dict:
    """
    Explicit one-way export of CI consultation text into ward chart.

    target:
      - 'hpi': merge into gi_history_narrative HPI section (+ full narrative)
      - 'note': ward clinical note only
      - 'both': HPI section + clinical note
    """
    from gi_platform import history_service
    from ward import services as ward_services

    ward_patient_id = encounter.get("ward_patient_id")
    if not ward_patient_id:
        raise ValueError(
            "This CI encounter is not linked to a ward patient. "
            "Start from ward Clinical workflow → Clinical Intelligence."
        )
    wp = ward_services.get_ward_patient(db, ward_patient_id)
    if not wp:
        raise ValueError("Linked ward patient not found.")

    export_text = build_export_highlights(
        documentation_text,
        encounter_id=encounter["id"],
        complaint_code=encounter.get("complaint_code") or "",
    )
    target = (target or "hpi").strip().lower()
    if target not in ("hpi", "note", "both"):
        target = "hpi"

    session_id = None
    if target in ("hpi", "both"):
        sessions = history_service.list_sessions_for_patient(db, ward_patient_id)
        if sessions:
            session_id = sessions[0]["id"]
        else:
            session_id = history_service.create_session(
                db,
                ward_patient_id=ward_patient_id,
                mrn=(wp["mrn"] or "") if wp["mrn"] else "",
                chief_complaint=encounter.get("complaint_code") or "",
                complaint_code="",
                created_by=user_id,
            )

        narrative = history_service.get_narrative(db, session_id)
        sections = {}
        if narrative and narrative["sections_json"]:
            try:
                sections = json.loads(narrative["sections_json"]) or {}
            except (TypeError, json.JSONDecodeError):
                sections = {}

        existing_hpi = (sections.get("hpi") or "").strip()
        if existing_hpi:
            sections["hpi"] = existing_hpi + "\n\n" + export_text
        else:
            sections["hpi"] = export_text
        prev_ci = (sections.get("ci_export") or "").strip()
        sections["ci_export"] = (prev_ci + "\n\n" + export_text).strip() if prev_ci else export_text

        from gi_platform.narrative_engine import sections_to_history_text

        full_text = sections_to_history_text(
            sections,
            patient_name=wp["patient_name"] or "",
            mrn=wp["mrn"] or "",
        )
        history_service.save_narrative(db, session_id, full_text, sections)

    if target in ("note", "both"):
        ward_services.add_clinical_note(
            db,
            ward_patient_id=ward_patient_id,
            note_type="ci_export",
            body=export_text,
            user_id=user_id,
        )

    return {
        "ward_patient_id": ward_patient_id,
        "session_id": session_id,
        "target": target,
        "chars": len(export_text),
    }
