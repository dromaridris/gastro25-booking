# Naming conventions

## IDs

| Kind | Pattern | Example |
|------|---------|---------|
| Question | `Q` + 6 digits | `Q000001` |
| Symptom | `SX_` + snake | `SX_abdominal_pain` |
| Sign | `SG_` + snake | `SG_murphy_sign` |
| Risk factor | `RF_` + snake | `RF_nsaid_use` |
| Diagnosis (future) | `DX_` + snake | `DX_acute_cholecystitis` |
| Investigation (future-ready) | `IX_` + snake | `IX_cbc` |
| Procedure (future-ready) | `PR_` + snake | `PR_egd` |
| Complaint template | `CC_` + snake | `CC_abdominal_pain` |
| History template file | same as complaint code | `abdominal_pain.json` |

## Codes

- Human keys: English `snake_case`
- Stable once published; deprecate instead of reuse
- Synonyms live in `synonyms[]`, not alternate IDs
- Complaint codes (`CC_*`) must name **symptoms** (e.g. `CC_hematemesis`, `CC_abdominal_distention`), never syndromes (`ugib`, `ascites_portal_htn`)

## Files

- Dictionary: batched packs `dictionary/<entity_type plural>.json` (arrays), indexed by `dictionary/_index.json`
- Questions: batched `questions/library.json` (preferred for Phase 3); optional later split to `questions/Q######.json`
- History templates: `templates/history/<complaint_code>.json`
- Pack index: `packs/complaints/_index.json` + root `manifest.json`

## Versioning

- Each JSON object includes `schema_version` (int) and `revision` (int)
- Pack-level `manifest.json` uses semver when present
