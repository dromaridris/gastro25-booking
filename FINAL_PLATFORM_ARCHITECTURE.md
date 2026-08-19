# FINAL_PLATFORM_ARCHITECTURE

## Dependency map

```
┌─────────────────────────────────────────────────────────────────┐
│                     Enterprise (Phase 8)                        │
│  Tenant · Dept · RBAC · Audit · API · Jobs · Notify · Search    │
│  Integration adapters: FHIR/HL7/DICOM/LIS/RIS/PACS/HIS/...        │
└────────────────────────────┬────────────────────────────────────┘
                             │ identity / tenancy / ops
┌────────────────────────────┼────────────────────────────────────┐
│ Research (7)  │ Longitudinal (6) │ CDS (5) │ Docs (4) │ Workflow (3) │
└───────┬───────┴────────┬───────┴────┬─────┴────┬─────┴──────┬──────┘
        │ reads          │ ingest     │ reads    │ reads      │ mutates
        └────────────────┴────────────┴──────────┴────────────┤
                                                              ▼
                                              Encounter Belief State (EBS)
                                                              ▲
                                                              │
                                              Clinical Reasoning Engine (2)
                                                              ▲
                                                              │ graph snapshot
                                              Knowledge Platform / Releases (1)
```

**Hard rule:** Workflow / Docs / CDS never invent medical knowledge. They consume KG + EBS + CRE outputs.

**Specialty:** Core engines are specialty-agnostic. Domain packs (GI first) are data.

## Module paths
| Phase | Package |
|------:|---------|
| 1–2 | `clinical_knowledge_platform/` (+ `reasoning/`) |
| 3 | `clinical_knowledge_platform/workflow/` |
| 4 | `clinical_knowledge_platform/documentation/` |
| 5 | `clinical_knowledge_platform/cds/` |
| 6 | `clinical_knowledge_platform/longitudinal/` |
| 7 | `clinical_knowledge_platform/research/` |
| 8 | `clinical_knowledge_platform/enterprise/` |

Registered via:
- `db_schema_registry.py` → `clinical_knowledge_platform`
- `migration_bootstrap.register_migration_extensions` → all CKP route registrars

## Deployment
1. Existing Flask app (`app.py`) boots as today.
2. `ensure_all_schemas_for_path` creates additive `ckp_*` / `cre_session` tables.
3. First visit to `/clinical-encounter/` seeds demo KB if no published release.
4. SQLite remains default (current product). For multi-hospital scale: move CKP tables to Postgres with same schema; keep adapters external.

## Scalability notes
- EBS JSON is per-session; suitable for SQLite single-site.
- Longitudinal events grow with encounters — index on `patient_key` already present; archive old events by year if needed.
- Research exports are snapshots (not live joins) — good for load isolation.
- Job queue is DB-backed stub; swap to Redis/RQ/Celery without changing route contracts.
- Search index is simple LIKE; replace with FTS5/Elastic later behind `enterprise.search`.

## Security
- Routes use existing `login_required` / `roles_required`.
- CKP RBAC extension tables complement app roles (not a parallel login system).
- Research exports default **de-identified**.
- Enterprise audit + document audit + research audit.
- Integration credentials must live in env/secret store — never commit; `config_json` holds non-secret endpoints only in stubs.
- `/ckp/api/v1/health` is currently open for ops probes — lock down behind network ACL or token in production.

## Future extension
1. Real FHIR Patient/Encounter sync adapter
2. HL7 ORU→investigation_result mapping into EncounterController
3. DICOM worklist for procedure channel
4. Full stats engine sidecar for research survival curves
5. Link ward MRN ↔ `patient_key` canonical identity
6. Promote Domain Pack authorship UI (beyond seed)

## Coexistence
Legacy Clinical Intelligence (`clinical_intelligence/`, `clinical_knowledge/` JSON), ward, booking, MCQ remain untouched. CKP is additive.
