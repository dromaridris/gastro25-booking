"""Smoke: phases 7–8 freeze + lab propagation."""
from __future__ import annotations

import os
import sqlite3
import tempfile

from gi_platform.legacy_history_freeze import (
    FREEZE_MESSAGE,
    legacy_history_writes_allowed,
    legacy_history_writes_frozen,
)


def test_freeze():
    os.environ.pop("GASTRO_ALLOW_LEGACY_HISTORY_WRITES", None)
    assert legacy_history_writes_frozen() is True
    assert legacy_history_writes_allowed() is False
    os.environ["GASTRO_ALLOW_LEGACY_HISTORY_WRITES"] = "1"
    assert legacy_history_writes_allowed() is True
    del os.environ["GASTRO_ALLOW_LEGACY_HISTORY_WRITES"]
    assert legacy_history_writes_frozen() is True
    print("freeze: OK", FREEZE_MESSAGE[:48], "...")


def test_lab_propagation():
    from gi_platform import lab_propagation, lab_service
    from gi_platform.schema import init_gi_schema_db
    from clinical_intelligence.schema import init_clinical_intelligence_schema
    from ward.schema import init_ward_schema

    path = tempfile.mktemp(suffix=".db")
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    init_ward_schema(db)
    init_gi_schema_db(db)
    init_clinical_intelligence_schema(db)

    db.execute(
        "INSERT INTO ward_patient (id, patient_name, mrn) VALUES (1, ?, ?)",
        ("Test Pt", "MRN999"),
    )
    db.execute(
        """
        INSERT INTO ci_encounter
            (id, complaint_code, patient_label, ward_patient_id, status, phase)
        VALUES (1, 'hematemesis', 'Test Pt', 1, 'open', 'history')
        """
    )
    db.execute(
        """
        INSERT INTO ci_ix_result (encounter_id, investigation_code, result_label, note)
        VALUES (1, 'cbc', 'anemia', 'clinician')
        """
    )
    db.commit()

    rid = lab_service.enter_lab_result(
        db,
        test_code="lab.hemoglobin",
        test_name="Hemoglobin",
        result_value="9.2",
        result_unit="g/dL",
        ward_patient_id=1,
        recorded_by=1,
    )
    labs = lab_propagation.list_labs_for_patient(db, ward_patient_id=1)
    assert labs and str(labs[0]["result_value"]) == "9.2", labs
    row = db.execute("SELECT mrn FROM gi_lab_result WHERE id=?", (rid,)).fetchone()
    assert row["mrn"] == "MRN999", row["mrn"]

    ward_ix = db.execute(
        "SELECT * FROM ci_ix_result WHERE investigation_code LIKE 'ward:%'"
    ).fetchall()
    clin = db.execute(
        "SELECT * FROM ci_ix_result WHERE investigation_code='cbc'"
    ).fetchone()
    assert clin["result_label"] == "anemia"
    assert ward_ix, "expected ward: ix rows"
    print("lab prop: OK rid=", rid, "ward_ix=", len(ward_ix), "clinician preserved")
    db.close()
    os.remove(path)


def test_imports():
    from gi_routes.history_templates import register_history_template_routes  # noqa: F401
    from gi_routes.history_ai_training import register_history_ai_training_routes  # noqa: F401
    from gi_routes.laboratory import register_laboratory_routes  # noqa: F401
    from gi_platform.lab_propagation import after_lab_result_saved  # noqa: F401
    import gi_routes
    src = open(gi_routes.__file__, encoding="utf-8").read()
    assert "GI_IMPORT" in src or "reference-only" in src
    assert "from gi_import" not in src
    print("imports: OK")


if __name__ == "__main__":
    test_freeze()
    test_lab_propagation()
    test_imports()
    print("ALL SMOKE OK")
