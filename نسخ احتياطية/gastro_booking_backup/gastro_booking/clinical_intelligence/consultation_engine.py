"""Consultation Engine — glue across all CI engines → documentation summary."""

from __future__ import annotations

from typing import Any

from clinical_intelligence import (
    ai_assist,
    education_engine,
    exam_engine,
    history_engine,
    interpretation_engine,
    investigation_engine,
    management_engine,
    procedure_engine,
    reasoning_engine,
    research_engine,
    scoring_engine,
)
from clinical_intelligence import evidence_service
from clinical_intelligence.modules import gi_overlay


def run_consultation(
    complaint_code: str,
    *,
    answers: list[dict],
    findings: list[dict],
    ix_results: list[dict] | None = None,
    patient_label: str | None = None,
    urgency_flag: str | None = None,
    include_ai: bool = True,
) -> dict[str, Any]:
    hist = history_engine.next_questions(complaint_code, answers, limit=5)
    hist_rows = history_engine.history_summary(complaint_code, answers)
    plan = exam_engine.exam_plan(complaint_code)
    exam_sum = exam_engine.exam_status_summary(plan, findings)
    reasoning = reasoning_engine.evaluate_patterns(complaint_code, answers, findings)
    scoring = scoring_engine.score_encounter(
        complaint_code, answers, findings, reasoning=reasoning
    )

    ans_map = {a["question_id"]: a.get("answer_text") for a in answers if not a.get("skipped")}
    exam_map = exam_sum.get("by_code") or {}
    matched = set(reasoning.get("matched_pattern_ids") or [])
    dx_codes = {d["code"] for d in (reasoning.get("diagnoses") or [])}
    present_signs = {
        f["sign_code"] for f in findings if f.get("status") == "present" and f.get("sign_code")
    }

    ix = investigation_engine.suggest_investigations(
        complaint_code, answers=ans_map, exam=exam_map, matched_patterns=matched
    )
    ix = gi_overlay.enrich_investigations_for_gi(ix)
    mgmt = management_engine.suggest_management(
        complaint_code, matched_patterns=matched, answers=ans_map, exam=exam_map
    )
    procedures = procedure_engine.suggest_procedures(
        complaint_code, answers=ans_map, exam=exam_map, matched_patterns=matched
    )

    ix_result_rows = ix_results or []
    interp_input = [
        {"investigation_code": r["investigation_code"], "result": r["result_label"]}
        for r in ix_result_rows
    ]
    interpretation = interpretation_engine.interpret_results(complaint_code, interp_input)

    education = education_engine.teaching_points(
        complaint_code,
        matched_patterns=matched,
        present_signs=present_signs,
        diagnosis_codes=dx_codes,
    )
    research = research_engine.analyze_gaps(
        complaint_code,
        scoring=scoring,
        urgency_flag=urgency_flag,
        answered_count=len(ans_map),
    )
    version = evidence_service.knowledge_version_info()

    summary_lines = []
    if patient_label:
        summary_lines.append(f"Patient: {patient_label}")
    summary_lines.append(f"Chief complaint pack: {complaint_code}")
    summary_lines.append(f"Knowledge version: {version.get('knowledge_version')}")
    if scoring.get("available"):
        band = (scoring.get("band") or {}).get("label")
        summary_lines.append(f"Pattern score: {scoring.get('total_score')} ({band})")
    if hist_rows:
        summary_lines.append("")
        summary_lines.append("History highlights:")
        for row in hist_rows[:20]:
            flag = " [RF]" if row.get("is_red_flag") else ""
            summary_lines.append(f"- {row['prompt']}{flag}: {row.get('answer_text')}")
    if exam_sum.get("present"):
        summary_lines.append("")
        summary_lines.append("Exam — present findings:")
        for f in exam_sum["present"]:
            note = f" ({f['note']})" if f.get("note") else ""
            summary_lines.append(f"- {f.get('sign_code')}{note}")
    if reasoning.get("diagnoses"):
        summary_lines.append("")
        summary_lines.append("Data-driven suspects (not final diagnoses):")
        for d in reasoning["diagnoses"]:
            links = ", ".join(d.get("linked_findings") or [])
            summary_lines.append(f"- {d['label']} (conf {d['confidence']:.2f}): {links}")
    elif not reasoning.get("dx_unlocked"):
        summary_lines.append("")
        summary_lines.append(
            f"Diagnoses withheld until ≥{reasoning.get('min_history_answers_for_dx')} history answers."
        )
    if interpretation.get("entries"):
        summary_lines.append("")
        summary_lines.append("Investigation interpretation flags:")
        for item in interpretation["entries"]:
            if not item.get("ok"):
                continue
            for interp in item.get("interpretations") or []:
                summary_lines.append(
                    f"- {item['investigation_code']}={item['result']}: {interp.get('message')}"
                )
    if ix.get("entries"):
        summary_lines.append("")
        summary_lines.append("Suggested investigations:")
        for item in ix["entries"][:10]:
            summary_lines.append(f"- [{item['urgency']}] {item['label']} ({item['code']})")
    if procedures.get("entries"):
        summary_lines.append("")
        summary_lines.append("Procedure considerations:")
        for p in procedures["entries"][:6]:
            summary_lines.append(f"- [{p.get('urgency')}] {p['label']}")
    if mgmt.get("actions"):
        summary_lines.append("")
        summary_lines.append("Management / disposition (no prescriptions):")
        for a in mgmt["actions"]:
            ref = f" → {a['referral']}" if a.get("referral") else ""
            summary_lines.append(f"- [{a['urgency']}] {a['label']}{ref}")

    documentation_text = "\n".join(summary_lines)
    ai = None
    if include_ai:
        ai = ai_assist.assist_consultation(
            complaint_code=complaint_code,
            documentation_text=documentation_text,
            answers=answers,
            allowed_next_questions=hist.get("next") or reasoning.get("next_questions"),
        )

    return {
        "complaint_code": complaint_code,
        "knowledge_version": version,
        "history": hist,
        "history_answers": hist_rows,
        "exam_plan": plan,
        "exam_summary": exam_sum,
        "reasoning": reasoning,
        "scoring": scoring,
        "investigations": ix,
        "interpretation": interpretation,
        "procedures": procedures,
        "management": mgmt,
        "education": education,
        "research": research,
        "ai_assist": ai,
        "documentation_text": documentation_text,
        "phase_complete": {
            "history": bool(hist.get("complete")),
            "exam": bool(exam_sum.get("documented")),
            "reasoning": bool(reasoning.get("available")),
            "scoring": bool(scoring.get("available")),
            "interpretation": bool(interpretation.get("available")),
            "procedures": bool(procedures.get("available")),
            "education": bool(education.get("available")),
            "research": bool(research.get("available")),
        },
    }
