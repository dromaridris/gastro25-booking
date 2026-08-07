# Site cleanup & duplication audit

Date: 2026-08-04  
Policy (user): **Keep** anything that may help future development even if unused today. **Remove** only clear junk / accidental duplicates with no future value.

## Cleanup tool

```bash
python scripts/cleanup_site.py          # dry-run
python scripts/cleanup_site.py --apply  # caches + orphan book uploads only
```

Does **not** touch patient documents, procedure images, `gi_import`, backups, or live modules.

---

## Removed (junk only)

| Item | Why junk |
|------|----------|
| `=2.31`, `=3.0`, `=3.1` | Accidental empty pip shell artifacts |
| `gastro.db` (0 bytes) | Wrong empty DB; live DB is `gastro_booking.db` |
| `test_gi_migrate.db` | Old test migration DB (~572 KB) |
| `__pycache__` / orphan book PDFs after extract | Regenerated / already extracted into DB |

---

## Kept for future (even if unused / parallel)

| Item | Why keep |
|------|----------|
| `gi_import/` (~55k LOC reference) | Schemas/vocab + future porting reference — **not** deleted; **not** live Flask routes — see `GI_IMPORT.md` |
| `backups/` | Historical migration snapshots |
| `gi_integration/` | Tiny catalog stub; harmless; may wire later |
| Guided History / History Templates / Training | Legacy **read-only** (writes frozen phase 7); data preserved |
| `procedure_reports/` | Old report rows access |
| Ward CDS + Knowledge Library | Live inpatient path |
| Clinical Intelligence + `clinical_knowledge/` | Canonical structured history |
| Root `test_*.py` smokes | Regression safety |

---

## Duplication notes (refactor later — do not mass-delete)

1. **`gi_import` vs live `gi_platform`/`gi_routes`** — conceptual mirror; live app does **not** register import as Flask (confirmed). Treat as **reference-only** (`GI_IMPORT.md`). Future: optionally extract only schemas/vocab into `advanced_reports/data/` then archive surplus *with explicit approval*.
2. **EGD ↔ Colonoscopy** routes ~78% similar — consolidate helpers later, keep both modules.
3. **Three history paths** — intentional split (CI teach / ward CDS / guided legacy). Legacy History AI Training + History Templates **writes are frozen** (phase 7); CI + `clinical_knowledge/` is canonical Bates.

Rough runtime-refactor candidate (not “delete now”): ~5–10% of *live* code.  
`gi_import` is large on disk but treated as **future asset / reference-only**, not garbage.

---

## لا تلمس

Patient docs, ERCP/colonoscopy/dilatation images, `gastro_booking.db`, ERCP core in `app.py`, MCQ bank content, `clinical_knowledge/`.
