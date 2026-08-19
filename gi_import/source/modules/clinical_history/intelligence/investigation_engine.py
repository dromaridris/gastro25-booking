"""Investigation engine — differential + existing results aware recommendations."""

from __future__ import annotations

from app.modules.clinical_history.intelligence.catalog_provider import get_catalog_provider
from app.modules.clinical_history.intelligence.differential_engine import top_diagnoses
from app.modules.clinical_history.models import (
    HistorySession,
    InvestigationSuggestionRecord,
    SUGGESTION_TIER_ADVANCED,
    SUGGESTION_TIER_BASELINE,
)
from app.modules.investigations.models import LabResultSet, LabResultValue


# Maps investigation suggestion codes to lab test codes in 4A-LAB catalogue
_INVESTIGATION_TO_LAB = {
    "lab.cbc": "lab.cbc",
    "lab.lft": "lab.alt",
    "lab.crp": "lab.crp",
    "lab.calprotectin": "lab.calprotectin",
    "lab.coagulation": "lab.inr",
    "lab.urea": "lab.urea",
    "lab.amylase": "lab.amylase",
}


def _patient_lab_codes(patient_id: int) -> dict[str, str]:
    """Return latest lab test_code -> abnormal_flag for patient."""
    rows = (
        LabResultValue.query.join(LabResultSet, LabResultValue.result_set_id == LabResultSet.id)
        .filter(LabResultSet.patient_id == patient_id, LabResultValue.is_archived.is_(False))
        .order_by(LabResultValue.created_at.desc())
        .all()
    )
    seen: dict[str, str] = {}
    for row in rows:
        if row.test_code not in seen:
            seen[row.test_code] = row.abnormal_flag or "unknown"
    return seen


def _should_skip_baseline(investigation_code: str, patient_id: int) -> tuple[bool, str | None]:
    lab_code = _INVESTIGATION_TO_LAB.get(investigation_code)
    if not lab_code:
        return False, None
    flags = _patient_lab_codes(patient_id)
    if lab_code not in flags:
        return False, None
    flag = flags[lab_code]
    if flag == "normal":
        return True, f"Recent {lab_code} already normal — reconsider if clinically indicated."
    return False, f"Recent {lab_code} was {flag} — interpret in clinical context."


def baseline_suggestions(complaint_code: str, patient_id: int) -> list[dict]:
    provider = get_catalog_provider()
    rules = provider.investigation_rules(complaint_code=complaint_code, tier=SUGGESTION_TIER_BASELINE)
    out = []
    for r in rules:
        skip, note = _should_skip_baseline(r.investigation_code, patient_id)
        item = {
            "investigation_code": r.investigation_code,
            "tier": r.tier,
            "reason_text": r.reason_text,
            "linked_diagnosis_code": None,
            "skip_suggested": skip,
            "context_note": note,
        }
        if not skip:
            out.append(item)
        elif note:
            out.append(item)
    return out


def advanced_suggestions(
    complaint_code: str,
    session_id: int,
    patient_id: int,
    confirmed_diagnosis: str | None = None,
) -> list[dict]:
    provider = get_catalog_provider()
    dx_codes = [confirmed_diagnosis] if confirmed_diagnosis else top_diagnoses(complaint_code, session_id, limit=5)
    if not dx_codes:
        return []

    lab_flags = _patient_lab_codes(patient_id)
    out = []
    seen = set()
    for dx in dx_codes:
        if not dx:
            continue
        rules = provider.investigation_rules(diagnosis_code=dx, tier=SUGGESTION_TIER_ADVANCED)
        for r in rules:
            if r.investigation_code in seen:
                continue
            seen.add(r.investigation_code)

            reason = r.reason_text
            # Escalate when baseline labs support the diagnosis
            calpro = lab_flags.get("lab.calprotectin")
            if r.investigation_code == "proc.colonoscopy" and calpro == "high":
                reason = (reason or "") + " Elevated faecal calprotectin supports inflammatory workup."

            skip, note = _should_skip_baseline(r.investigation_code, patient_id)
            out.append({
                "investigation_code": r.investigation_code,
                "tier": r.tier,
                "reason_text": reason,
                "linked_diagnosis_code": dx,
                "skip_suggested": skip,
                "context_note": note,
            })
    return out


def all_suggestions_for_session(session: HistorySession) -> list[dict]:
    if not session.chief_complaint_code:
        return []
    baseline = baseline_suggestions(session.chief_complaint_code, session.patient_id)
    advanced = advanced_suggestions(
        session.chief_complaint_code,
        session.id,
        session.patient_id,
        confirmed_diagnosis=session.confirmed_diagnosis_code,
    )
    return baseline + advanced


def sync_suggestion_records(session: HistorySession) -> list[InvestigationSuggestionRecord]:
    suggestions = all_suggestions_for_session(session)
    existing = {
        r.investigation_code: r
        for r in InvestigationSuggestionRecord.query.filter_by(session_id=session.id, is_archived=False).all()
    }
    from app.extensions import db

    for s in suggestions:
        if s["investigation_code"] not in existing:
            db.session.add(InvestigationSuggestionRecord(
                session_id=session.id,
                investigation_code=s["investigation_code"],
                tier=s["tier"],
                reason_text=s.get("reason_text"),
                department_id=session.department_id,
            ))
    db.session.commit()
    return InvestigationSuggestionRecord.query.filter_by(session_id=session.id, is_archived=False).all()
