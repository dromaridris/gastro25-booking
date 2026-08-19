"""Smoke tests for Clinical Intelligence — consult path + new engines."""

from __future__ import annotations

import os
import sqlite3
import sys
import tempfile

ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from clinical_intelligence.schema import init_clinical_intelligence_schema
from clinical_intelligence import (
    consultation_engine,
    encounter_service,
    evidence_service,
    history_engine,
    interpretation_engine,
    knowledge_importer,
    procedure_engine,
    scoring_engine,
)


def _seed_encounter(db):
    enc = encounter_service.create_encounter(
        db, complaint_code="CC_abdominal_pain", created_by=1, patient_label="smoke"
    )
    sample = {
        "Q000001": "Belly pain",
        "Q000003": "Sudden",
        "Q000042": "RUQ",
        "Q000043": "Worse after meals",
        "Q000017": "yes",
        "Q000021": "yes",
        "Q000026": "yes",
        "Q000033": "no",
        "Q000034": "no",
        "Q000035": "no",
        "Q000045": "no",
    }
    for qid, ans in sample.items():
        encounter_service.save_answer(db, enc["id"], question_id=qid, answer_text=ans)
    encounter_service.save_finding(
        db, enc["id"], sign_code="SG_murphy_sign", status="present", system_key="abdomen_palpation"
    )
    encounter_service.save_finding(
        db, enc["id"], sign_code="SG_peritoneal_signs", status="absent", system_key="abdomen_palpation"
    )
    encounter_service.save_ix_result(
        db, enc["id"], investigation_code="IX_liver_panel", result_label="cholestatic_pattern"
    )
    encounter_service.save_ix_result(
        db, enc["id"], investigation_code="IX_abdominal_ultrasound", result_label="cholecystitis_features"
    )
    return enc


def main() -> int:
    # Knowledge validate
    tree = knowledge_importer.validate_tree()
    assert tree["ok"], tree

    version = evidence_service.knowledge_version_info()
    assert version.get("knowledge_version"), version

    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    try:
        db = sqlite3.connect(path)
        db.row_factory = sqlite3.Row
        init_clinical_intelligence_schema(db)

        enc = _seed_encounter(db)
        queue = history_engine.build_question_queue("CC_abdominal_pain")
        assert len(queue) >= 40

        answers = encounter_service.list_answers(db, enc["id"])
        findings = encounter_service.list_findings(db, enc["id"])
        ix_results = encounter_service.list_ix_results(db, enc["id"])

        result = consultation_engine.run_consultation(
            "CC_abdominal_pain",
            answers=answers,
            findings=findings,
            ix_results=ix_results,
            patient_label="smoke",
            include_ai=True,
        )
        assert result["reasoning"]["available"]
        assert result["scoring"]["available"]
        assert result["scoring"]["total_score"] > 0
        codes = {d["code"] for d in result["reasoning"]["diagnoses"]}
        assert "DX_biliary_colic_or_cholecystitis_suspect" in codes, codes
        assert result["interpretation"]["available"]
        flags = result["interpretation"]["flags"]
        assert "biliary_obstruction_concern" in flags or "biliary_imaging_positive" in flags, flags
        assert result["procedures"]["available"]
        proc_codes = {p["procedure_code"] for p in result["procedures"]["entries"]}
        assert "PR_cholecystectomy" in proc_codes or "PR_egd" in proc_codes, proc_codes
        assert result["education"]["available"]
        assert result["education"]["modules"]
        assert result["research"]["available"]
        assert result["ai_assist"] is not None
        assert result["ai_assist"]["diagnostic_authority"] is False
        assert result["documentation_text"]

        # Direct interpretation engine
        interp = interpretation_engine.interpret_results(
            "CC_abdominal_pain",
            {"IX_cbc": "leukocytosis"},
        )
        assert interp["entries"][0]["ok"]
        assert interp["entries"][0]["interpretations"]

        # Scoring standalone
        sc = scoring_engine.score_encounter("CC_abdominal_pain", answers, findings)
        assert sc["available"]

        # Procedure engine
        procs = procedure_engine.suggest_procedures(
            "CC_abdominal_pain",
            answers={a["question_id"]: a["answer_text"] for a in answers},
            exam={f["sign_code"]: f["status"] for f in findings},
            matched_patterns=set(result["reasoning"]["matched_pattern_ids"]),
        )
        assert procs["entries"]

        evidence_service.reload_knowledge(db=db, reason="smoke")
        events = evidence_service.list_knowledge_events(db)
        assert events

        print("OK consult+engines")
        print("  dx", sorted(codes))
        print("  score", sc["total_score"], sc["band"])
        print("  interp flags", flags)
        print("  procedures", sorted(proc_codes))
        print("  edu modules", len(result["education"]["modules"]))
        print("  ai mode", result["ai_assist"]["mode"])
        print("  knowledge", version["knowledge_version"])
        return 0
    finally:
        try:
            os.remove(path)
        except OSError:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
