# Clinical Intelligence — Knowledge Base

Platform-level medical knowledge (specialty-neutral).  
**Gastroenterology is the first consumer module, not the product.**

## ROADMAP V1 alignment

| Phase | Name | Output | Code? |
|------:|------|--------|-------|
| 1 | Clinical Dictionary | Entity JSON packs | No |
| 2 | History Templates | Per-complaint Bates-style templates | No |
| 3 | Universal Question Library | Shared `Q######` questions | No |
| 4 | History Engine | Load template → ask → save | **Yes** |
| 5 | Physical Examination Engine | Exam focus per complaint | Yes |
| 6 | Differential Engine | After history only | Yes |
| 7 | Investigation Engine | Labs / imaging / endoscopy / scores | Yes |
| 8 | Management Engine | After differentials | Yes |
| 9 | AI Layer | Last | Yes |

**Current status:** Phases 1–16 delivered. Knowledge in `clinical_knowledge/`; runtime in `clinical_intelligence/` — see `clinical_intelligence/STATUS.md`.

**History authority:** This tree is the canonical source for structured Bates-style history templates. Legacy ward / Guided History AI templates are deprecated for new work — see `clinical_intelligence/HISTORY_MIGRATION.md`.

## Folder layout

```text
clinical_knowledge/
  README.md
  NAMING.md
  ROADMAP.md
  schemas/
  dictionary/          # Phase 1
  questions/           # Phase 3 — Universal Question Library
  templates/
    history/           # Phase 2 — Bates history templates per complaint
  packs/
    complaints/        # optional composite views / indexes
```

## Bates role

Bates is used **only** for:

- Chief complaint → history questions
- Important associated symptoms
- Alarm / red-flag features
- Exam organization later (Phase 5)

Diseases come later (e.g. Sleisenger / guidelines) — not in Phases 1–3.

## Design rules

- No AI in dictionary / templates / questions.
- Questions are never duplicated: templates reference `Q######` IDs.
- Templates ask only clinically relevant history structure (OLDCARTS/OPQRST-style), not disease lists.
- **Chief complaints are symptoms only** (Bates). Apply across all systems — bleeding was only one example. See `HISTORY_SYMPTOM_MODEL.md` for the mapping of long symptom inventories → CC packs / synonyms / associated questions.
- Scalable to thousands of complaints and every specialty.

## Drop-in replace

Copy/replace this whole `clinical_knowledge/` folder on the server (or set `CLINICAL_KNOWLEDGE_ROOT`), then reload CI knowledge cache / restart the app.
