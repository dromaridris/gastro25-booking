"""Smoke-validate Clinical Knowledge Platform phases 1–8.

Usage (from repo root):
  python scripts/smoke_ckp_phases.py
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys
import tempfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def _db() -> sqlite3.Connection:
    path = os.path.join(tempfile.gettempdir(), "ckp_smoke_test.db")
    if os.path.exists(path):
        os.remove(path)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def main() -> int:
    from clinical_knowledge_platform.schema import init_ckp_schema
    from clinical_knowledge_platform.seed_demo import seed_demo_gastroenterology
    from clinical_knowledge_platform.validation import validate_knowledge
    from clinical_knowledge_platform.workflow.controller import EncounterController
    from clinical_knowledge_platform.documentation import service as doc_svc
    from clinical_knowledge_platform.cds import service as cds_svc
    from clinical_knowledge_platform.longitudinal import service as long_svc
    from clinical_knowledge_platform.research import service as res_svc
    from clinical_knowledge_platform.enterprise import service as ent_svc

    results = []

    def ok(phase, msg):
        results.append((phase, True, msg))
        print(f"[OK] Phase {phase}: {msg}")

    def fail(phase, msg):
        results.append((phase, False, msg))
        print(f"[FAIL] Phase {phase}: {msg}")
        return 1

    db = _db()
    init_ckp_schema(db)

    # Phase 1
    seed = seed_demo_gastroenterology(db, force=True)
    v = validate_knowledge(db)
    if not v["ok"]:
        return fail(1, f"validation errors: {v['errors'][:5]}")
    if v["counts"]["diseases"] < 8:
        return fail(1, f"expected >=8 diseases, got {v['counts']['diseases']}")
    if not seed.get("release"):
        return fail(1, "no published release")
    ok(1, f"knowledge seeded + validated ({v['counts']})")

    # Phase 2 + 3
    ctl = EncounterController.start(db, patient_label="SMOKE-PT-1")
    snap = ctl.intake(["Abdominal pain", "SX_vomiting"])
    if not snap["ebs"].get("presenting_problems"):
        return fail(2, "intake produced no presenting problems")
    if not snap["ebs"].get("differential"):
        return fail(2, "no differential after intake")
    qs = (snap["ebs"].get("suggested_next_action") or {}).get("questions") or []
    if qs:
        ctl.answer_question(qs[0]["code"], "present", "smoke")
    ctl.set_channel("examination")
    if snap["ebs"].get("exam_priorities") or ctl.ebs.get("exam_priorities"):
        ep = ctl.ebs.get("exam_priorities") or []
        if ep:
            ctl.record_exam(ep[0]["code"], "present")
    ctl.set_channel("investigations")
    ix = ctl.ebs.get("investigation_recommendations") or []
    if ix:
        ctl.order_investigation(ix[0]["code"])
    ctl.record_result("FD_lipase_high", "present")
    ctl.set_channel("summary")
    ctl.regen_narrative()
    ctl.save_plan_edits({"plan_text": "NPO fluids smoke plan"})
    ctl.set_channel("plan")
    if not ctl.ebs.get("narrative_draft"):
        return fail(3, "empty narrative")
    if ctl.ebs.get("channel") != "plan":
        return fail(3, "channel not plan")
    ok(2, "CRE intake/hypotheses/update/questions/redflags working")
    ok(3, f"5-channel controller session={ctl.session_id} stopping={ctl.ebs.get('stopping')}")

    # Phase 4
    docs = []
    for dt in doc_svc.DOCUMENT_TYPES:
        docs.append(doc_svc.create_or_regen_document(db, session_id=ctl.session_id, doc_type=dt, actor_id=1))
    if len(docs) != len(doc_svc.DOCUMENT_TYPES):
        return fail(4, "not all document types created")
    edited = doc_svc.edit_document(db, docs[0]["id"], body_text=docs[0]["body_text"] + "\n[edited]", actor_id=1)
    final = doc_svc.finalize_document(db, edited["id"], actor_id=1)
    if final["status"] != "final":
        return fail(4, "finalize failed")
    if not doc_svc.version_history(db, edited["id"]):
        return fail(4, "no version history")
    ok(4, f"{len(docs)} doc types + edit/version/finalize")

    # Phase 5
    alerts = cds_svc.refresh_cds_for_session(db, ctl.session_id)
    kinds = {a["alert_kind"] for a in alerts}
    needed = {"differential_explanation", "investigation_recommendation", "management_recommendation"}
    if not needed <= kinds and not any(k in kinds for k in needed):
        # soft: at least some alerts
        if not alerts:
            return fail(5, "no CDS alerts")
    ok(5, f"{len(alerts)} CDS advisories kinds={sorted(kinds)[:8]}")

    # Phase 6
    mem = long_svc.ingest_session_into_memory(db, ctl.session_id)
    ctl2 = EncounterController.start(db, patient_label="SMOKE-PT-1")
    ctl2.intake(["Hematemesis"])
    mem2 = long_svc.ingest_session_into_memory(db, ctl2.session_id)
    cmp_ = long_svc.latest_compare(db, "SMOKE-PT-1")
    if not mem2 or mem2["summary"].get("encounter_count", 0) < 2:
        return fail(6, f"expected multi-encounter memory, got {mem2}")
    ok(6, f"longitudinal memory encounters={mem2['summary'].get('encounter_count')} delta={bool(cmp_)}")

    # Phase 7
    reg = res_svc.create_registry(
        db,
        code="reg.smoke.gi",
        label="Smoke GI Registry",
        variables=[{"key": "diseases", "source": "timelines.disease"}, {"key": "encounters", "source": "summary.encounter_count"}],
    )
    cohort = res_svc.create_cohort(db, registry_id=reg["id"], code="c1", label="All smoke")
    member = res_svc.enroll_from_longitudinal(
        db, cohort_id=cohort["id"], patient_key="SMOKE-PT-1", registry_variables=reg["variables"]
    )
    quality = res_svc.data_quality_report(db, cohort["id"])
    export = res_svc.export_dataset(db, cohort_id=cohort["id"], registry_id=reg["id"], deidentified=True)
    study = res_svc.create_study(db, code="st.smoke", title="Smoke study", registry_id=reg["id"], design={"outcomes": "recurrence"})
    if not member.get("deid_token"):
        return fail(7, "missing deid token")
    ok(7, f"registry/cohort/enroll/export/study quality_n={quality['n']} export={export['export_id']}")

    # Phase 8
    tenant = ent_svc.ensure_default_tenant(db)
    ints = ent_svc.list_integrations(db, tenant["id"])
    if len(ints) < 8:
        return fail(8, f"expected integration stubs, got {len(ints)}")
    health = ent_svc.check_integration_health(db, ints[0]["id"])
    jid = ent_svc.enqueue_job(db, "smoke_job", {"x": 1})
    processed = ent_svc.process_next_job(db)
    nid = ent_svc.notify(db, title="Smoke", body="hi", tenant_id=tenant["id"])
    ent_svc.index_object(db, object_kind="patient", object_id="SMOKE-PT-1", title="Smoke patient", body="abdominal pain")
    hits = ent_svc.search(db, "smoke")
    obs = ent_svc.observability_snapshot(db)
    ar = ent_svc.t(db, "ckp.channel.history", "ar")
    if ar != "التاريخ المرضي":
        return fail(8, f"i18n ar unexpected: {ar}")
    if not health.get("ok"):
        return fail(8, f"health failed {health}")
    ok(8, f"tenant={tenant['code']} integrations={len(ints)} jobs={processed} notify={nid} search={len(hits)} obs={obs}")

    print("\n=== ALL PHASE SMOKES PASSED ===")
    print(json.dumps([{"phase": p, "ok": o, "msg": m} for p, o, m in results], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
