# GastroIntelligence → Gastro25 Hybrid Platform  
# AI Feature Migration Inventory (Read-Only Source Audit)

**Policy:** GastroIntelligence and Gastro25 remain **unchanged as source projects**.  
**Destination:** `D:\Gastro25\gastro_booking\` runtime (`gi_platform/`, `gi_routes/`, SQLite schema).  
**Reference copy (already in hybrid repo, not runtime):** `gi_import/source/modules/`.

**GI canonical source:**  
`D:\GastroIntelligence\موقع من تصميم كلاود\gastrointelligence-foundation\gastrointelligence\app\`

---

## Executive Summary

| Status | Count | Meaning |
|--------|------:|---------|
| Full reference in `gi_import` | 12 modules | Source code copied for study; **not wired to Flask runtime** |
| Partial runtime adapter | 8 areas | Stub or deterministic logic only |
| No runtime equivalent | 4 modules | Must be ported (SQLite + routes + templates) |
| LLM provider stack | 0% live | GI uses provider stubs (`null`, `openai`, `claude`, `gemini`, `local` adapters); G25 has `GI_AI_PROVIDER=stub` only |

**Total AI-related Python files in GI source:** ~155 across 12 feature areas (+ clinical_history intelligence + shared engines).

---

## 1. Core LLM Infrastructure

### Clinical AI (Sprint 9A) — **P0 dependency for all LLM features**

| Field | Detail |
|-------|--------|
| **GI location** | `app/modules/clinical_ai/` (15 files) |
| **gi_import** | `gi_import/source/modules/clinical_ai/` ✅ 15/15 |
| **Key files** | `ai_services.py`, `ai_session.py`, `prompt_engine.py`, `prompt_blocks.py`, `provider_factory.py`, `providers.py`, `context_builder.py`, `ai_response_parser.py`, `config.py`, `routes.py`, `models.py`, `permissions.py`, `bootstrap.py`, `constants.py` |
| **Dependencies** | `app.engines.audit_engine`, `app.extensions.db`, Flask config, RBAC `clinical_ai:view/use/configure` |
| **DB tables (Postgres)** | `clinical_ai_sessions`, `clinical_ai_request_audits` |
| **API routes** | Blueprint `/clinical-ai`: `GET /status`, `GET /config`, `POST /config/preview`, `POST /sessions/run` |
| **Configuration** | `CLINICAL_AI_DEFAULT_PROVIDER`, `CLINICAL_AI_PROVIDER_PRIORITY`, `CLINICAL_AI_REQUEST_TIMEOUT`, `CLINICAL_AI_MAX_TOKENS`, `CLINICAL_AI_TEMPERATURE`, `CLINICAL_AI_LOG_PROMPTS`, `CLINICAL_AI_LOG_RESPONSES`, `CLINICAL_AI_TRAINEE_ENABLED`, `CLINICAL_AI_FEATURE_FLAGS` |
| **G25 runtime** | **partial** — `gi_platform/ai_service.py` (~68 lines stub), `gi_routes/ai.py` (3 routes), templates `gi/ai_patient.html`, `gi/ai_session.html` |
| **G25 tables** | `gi_ai_session`, `gi_ai_request_log` ✅ |
| **G25 config** | `GI_AI_PROVIDER=stub` (env only) |
| **Copy needed?** | **YES (partial → full)** — port provider factory, prompt engine, session manager, config UI |

---

## 2. Clinical Workflow AI Modules (all depend on `clinical_ai.*`)

| # | Feature | GI module | Files | GI routes prefix | Postgres tables | G25 runtime | Copy? |
|---|---------|-----------|------:|------------------|-----------------|-------------|-------|
| 2a | **AI History Generator / Guided History** | `clinical_history_ai/` | 11 | `/clinical-history-ai` | `guided_history_questions`, `guided_history_question_rules`, `guided_history_sessions`, `guided_history_answers`, `guided_history_drafts` | **none** (deterministic `history_service` only) | **YES** |
| 2b | **Clinical Assessment / Differential Diagnosis AI** | `clinical_assessment/` | 12 | `/clinical-assessment` | `diagnosis_rule_definitions`, `clinical_assessment_runs`, `diagnosis_suggestions`, `physician_diagnosis_decisions` | **partial** — `cds_service.py`, `catalogue_runtime.compute_differential_for_session()` | **PARTIAL** |
| 2c | **Clinical Interpretation / Lab reasoning AI** | `clinical_interpretation/` | 11 | `/clinical-interpretation` | `clinical_interpretation_runs`, `interpretation_findings`, `differential_update_records`, `physician_interpretation_decisions` | **none** | **YES** |
| 2d | **Investigation Recommendation Engine** | `investigation_planning/` | 12 | `/investigation-planning` | `investigation_library_entries`, `investigation_recommendation_rules`, `investigation_plans`, `investigation_suggestions`, `physician_investigation_decisions` | **partial** — `gi_investigation_suggestion`, `gi_investigation_order`, lab module | **PARTIAL** |
| 2e | **AI Management Plan Generator** | `management_plan_ai/` | 12 | `/management-plan` | `management_plan_rules`, `management_plans`, `management_suggestions`, `physician_management_decisions` | **partial** — flat `gi_management_plan` + workflow approve | **PARTIAL** |
| 2f | **Documentation AI** | `documentation_ai/` | 12 | `/documentation-ai` | `documentation_templates`, `clinical_document_drafts`, `document_sections`, `document_version_records`, `signed_clinical_documents`, `physician_document_actions` | **none** (manual discharge summaries only) | **YES** |

**Shared LLM entry points (generators):**  
`clinical_history_ai/ai_generator.py`, `clinical_assessment/ai_generator.py`, `clinical_interpretation/interpretation_engine.py`, `investigation_planning/recommendation_generator.py`, `management_plan_ai/recommendation_generator.py`, `documentation_ai/document_generator.py`, `patient_journey/followup_engine.py`

---

## 3. Decision Support (Deterministic — Not LLM, but Intelligence Core)

| Feature | GI location | Files | Routes | G25 runtime | Copy? |
|---------|-------------|------:|--------|-------------|-------|
| **CDS Orchestrator** | `decision_support/` | 17 (+ `engines/` 9 engines) | Library only (no blueprint) | **partial** — `cds_service.py`, `catalogue_runtime.py` | **PARTIAL** |
| **History CDS bridge** | `clinical_history/cds_adapter.py` | 1 | via `/clinical-history/*` | **partial** — unified clinical workflow | **PARTIAL** |
| **History intelligence** | `clinical_history/intelligence/` | 7 | via interview flow | **partial** — ported into `catalogue_runtime.py` | **PARTIAL** |
| **History advisors** | `reasoning_engine.py`, `management_advisor.py`, `investigation_advisor.py`, `interview_engine.py`, `narrative_engine.py`, `knowledge_bridge.py` | 8+ | `/clinical-history/*` | **partial** — `narrative_engine.py`, `history_service.py` | **PARTIAL** |

**CDS engines in GI:** `adaptive_history_engine`, `branch_engine`, `differential_engine`, `guideline_engine`, `investigation_engine`, `red_flag_engine`, `score_engine`, `teaching_engine`

**G25 CDS tables:** `gi_cds_assessment`, `gi_clinical_score_result`, `gi_investigation_suggestion` ✅

---

## 4. Patient Journey AI

| Field | Detail |
|-------|--------|
| **GI location** | `patient_journey/` (13 files) |
| **gi_import** | ✅ 13/13 |
| **AI usage** | `followup_engine.py` — AI summary drafts for journey |
| **DB tables** | `follow_up_plans`, `follow_up_events`, `clinical_outcome_records`, `journey_summary_drafts`, `follow_up_recommendation_rules` |
| **Routes** | `/patient-journey` — timeline, follow-up CRUD, outcomes, summary generate/approve/reject |
| **G25 runtime** | **partial** — `patient_journey_service.py`, `gi_routes/journey.py`, table `gi_journey_event` |
| **Copy needed?** | **PARTIAL** — follow-up plans, outcome records, AI summary workflow |

---

## 5. Medical Score Engine

| Field | Detail |
|-------|--------|
| **GI location** | `decision_support/engines/score_engine.py` + knowledge score objects |
| **G25 runtime** | **partial/full for calc** — `score_registry.py`, `score_service.py`, auto-calc from labs, `gi_clinical_score_result` |
| **Copy needed?** | **PARTIAL** — GI teaching/score linkage via KL; G25 has 12 calculators |

---

## 6. Knowledge Library AI Integration

| Feature | GI location | G25 runtime | Copy? |
|---------|-------------|-------------|-------|
| **Knowledge objects / CDS feed** | `knowledge_library/` (18 files) | **partial** — `knowledge_service.py`, SQLite KL tables | **PARTIAL** |
| **Knowledge Activation Workflow** | subset + activation routes | **partial** — `gi_knowledge_activation`, `/knowledge-library/activation` | **PARTIAL** |
| **Guideline Recommendation Engine** | `decision_support/engines/guideline_engine.py` | **partial** — via CDS + KL seeds | **PARTIAL** |
| **Catalogue sync / migrator** | `kl_catalog_loader.py`, `catalogue_migrator.py`, `ui_catalogue_sync.py` | **partial** — `catalogue_loader.py`, `catalogue_migrate.py` | **PARTIAL** |
| **AI Knowledge Search** | Not a separate LLM module — `global_search/` is text/ILIKE search | G25 `/search` + ward hits | **N/A (no semantic AI in GI)** |

---

## 7. AI Analytics

| Field | Detail |
|-------|--------|
| **GI location** | `analytics/` (26 files: quality_metrics, specialty_metrics) |
| **gi_import** | ✅ 26/26 |
| **AI linkage** | Reads outputs from `documentation_ai`, `patient_journey`, `clinical_history_ai`, `management_plan_ai` |
| **DB tables** | `metric_definitions`, `analytics_snapshots` |
| **Routes** | `/analytics` — metrics, snapshots, configure |
| **Config** | `ANALYTICS_TRAINEE_ENABLED`, RBAC `analytics:view/configure/export` |
| **G25 runtime** | **none** |
| **Copy needed?** | **YES** (after upstream AI modules produce data) |

---

## 8. AI Research Assistant

| Field | Detail |
|-------|--------|
| **GI** | No dedicated "AI research assistant" module found |
| **G25** | Research module is manual registry + variable capture (`gi_research_*`) — not LLM |
| **Copy needed?** | **NO** (feature does not exist in GI source as LLM) |

---

## 9. Shared / Hidden Infrastructure

| Component | GI location | G25 runtime | Copy? |
|-----------|-------------|-------------|-------|
| **Audit engine** | `app/engines/audit_engine.py` | `audit_service.py`, `gi_audit_event` | Adapted ✅ |
| **Permission engine** | `app/engines/permission_engine.py` | `permission_service.py`, role lists | Adapted ✅ |
| **RBAC AI permissions** | `rbac/seed_data.py` | Partial native roles | **PARTIAL** |
| **Prompt management** | `clinical_ai/prompt_blocks.py`, `prompt_engine.py` | **none** | **YES** (with clinical_ai) |
| **AI APIs** | `/clinical-ai/*` JSON API | `/clinical-ai/patient/*` HTML only | **PARTIAL** |
| **Background services** | None (synchronous Flask) | Same | N/A |
| **Registry metadata** | N/A | `gi_registry/master_registry.py` branch `ai_engine` | Docs only ✅ |

---

## 10. Environment Variables Crosswalk

| Variable | GI | G25 hybrid |
|----------|-----|------------|
| `CLINICAL_AI_DEFAULT_PROVIDER` | ✅ | ❌ not wired |
| `CLINICAL_AI_PROVIDER_PRIORITY` | ✅ | ❌ |
| `CLINICAL_AI_REQUEST_TIMEOUT` | ✅ | ❌ |
| `CLINICAL_AI_MAX_TOKENS` | ✅ | ❌ |
| `CLINICAL_AI_TEMPERATURE` | ✅ | ❌ |
| `CLINICAL_AI_LOG_PROMPTS/RESPONSES` | ✅ | ❌ |
| `CLINICAL_AI_TRAINEE_ENABLED` | ✅ | ❌ |
| `CLINICAL_AI_FEATURE_FLAGS` | ✅ | ❌ |
| `GI_AI_PROVIDER` | — | ✅ `stub` |
| `KNOWLEDGE_PROVIDER` | `postgres` | SQLite adapter |
| `KNOWLEDGE_LIBRARY_AUTO_SEED` | ✅ | via catalogue migrate |
| `ANALYTICS_TRAINEE_ENABLED` | ✅ | ❌ |
| `OPENAI_API_KEY` / etc. | Not in GI codebase (provider stubs) | Not wired |

---

## 11. Database Table Crosswalk (Postgres → SQLite)

| GI tables | G25 table(s) | Status |
|-----------|--------------|--------|
| `clinical_ai_sessions`, `clinical_ai_request_audits` | `gi_ai_session`, `gi_ai_request_log` | ✅ exists |
| `guided_history_*` (5) | `gi_history_session`, `gi_history_answer`, `gi_history_narrative` | partial |
| `clinical_assessment_*` (4) | — | ❌ |
| `clinical_interpretation_*` (4) | — | ❌ |
| `investigation_plans`, `investigation_suggestions`, … | `gi_investigation_suggestion`, `gi_investigation_order` | partial |
| `management_plans`, `management_suggestions`, … | `gi_management_plan` | partial |
| `documentation_*` (6) | `ward_discharge_summary` | partial manual |
| `follow_up_plans`, `journey_summary_drafts`, … | `gi_journey_event` | partial |
| `metric_definitions`, `analytics_snapshots` | — | ❌ |
| CDS | `gi_cds_assessment` | ✅ |
| Scores | `gi_clinical_score_result` | ✅ |

---

## 12. Recommended Migration Order (Copy to Runtime)

1. **P0** — `clinical_ai` core (providers, prompts, sessions, audit)
2. **P1** — Complete `decision_support` engines + orchestrator
3. **P2** — `clinical_history_ai` (largest clinical UX gap)
4. **P3** — `clinical_assessment` + `clinical_interpretation`
5. **P4** — Extend `investigation_planning` + `management_plan_ai`
6. **P5** — `documentation_ai`
7. **P6** — `patient_journey` AI summaries + follow-up
8. **P7** — `analytics` quality metrics

---

## 13. What Is NOT AI in GI (Excluded from copy scope)

- `global_search` — SQL/text search, no LLM
- `research` module — structured registries, no LLM assistant
- ERCP / procedure report generation in Gastro25 — separate, do not touch
- `dept_ops`, `appointments`, `ward` — operational, not AI

---

*Generated for hybrid platform planning. No files in GastroIntelligence or Gastro25 source trees were modified during this audit.*
