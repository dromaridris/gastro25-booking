# Bates OCR → Knowledge Library import

## Source

- PDF: `D:\gastro materials\BATES OCR.pdf` (~84 MB, 1066 pages, text layer via OCR)
- Work: Bates' Guide to Physical Examination and History Taking

## What was imported

| Item | Value |
|------|--------|
| Parent object | **id 978**, slug `bates-ocr-guide-physical-examination-history-taking` |
| Type / status | `guideline` / **published** |
| Pages | 1066 (14 empty) |
| Lines | 128 063 nonempty · 129 180 including blanks |
| Full text chars | ~5.6M (stored in parent `body_json.imported_text`) |
| Page batches | **107** `reference` objects (`bates-ocr-pages-####-####`), 10 pages each |
| Lines location | Every line (incl. blanks) in each batch’s `body_json.lines` |
| Import job | `gi_import_job` id **3** |
| Prior dump | Object **977** (truncated 120k-char import) → **archived**, superseded by 978 |

History Engine / Clinical Intelligence disease packs do **not** auto-consume this book text. Upload is complete in the Knowledge Library; structured Bates history templates remain under `clinical_knowledge/`.

## Where to see it in the UI

1. **Knowledge Library** → search `Bates OCR` → open the parent guideline  
   Path: `/knowledge-library?q=Bates+OCR` → `/knowledge-library/978`
2. **Guidelines** list (published guidelines): `/knowledge-library/guidelines`
3. **Page batches** (line-level chunks): `/knowledge-library?q=bates-ocr-pages&object_type=reference`
4. Parent detail → **Linked knowledge** lists `contains_chunk` → each batch  
5. **Import Manager** history shows job for `BATES OCR.pdf`

## Re-run

```powershell
cd D:\Gastro25\gastro_booking

# Full extract + import
python scripts/import_bates_ocr.py --pdf "D:\gastro materials\BATES OCR.pdf"

# Extract only (writes scripts/tmp_bates_ocr/)
python scripts/import_bates_ocr.py --extract-only

# Import only (uses existing extract)
python scripts/import_bates_ocr.py --import-only

# Optional: change batch size (default 10 pages)
python scripts/import_bates_ocr.py --pages-per-batch 20
```

Re-import is idempotent for the parent slug and replaces prior `bates-ocr-pages-*` batches. Object 977 is left archived (not deleted).

## Intermediate files

Under `scripts/tmp_bates_ocr/`:

- `full_text.txt` — page-marked full extract  
- `pages.jsonl` — one JSON object per page (text + lines)  
- `manifest.json` / `import_result.json` — counts and IDs  

Requires **pymupdf** (`fitz`). Uses the same store as Import Manager: `gi_knowledge_object` + provenance + `gi_import_job`.
