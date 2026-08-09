# AD-ART Knowledge Base — Project Status

RAG pipeline + search app for Indonesian legal/org documents (AD, ART, UU,
Keppres, Peraturan Organisasi). Read `README.md` for setup/usage commands —
this file is session state: what's done, what's pending, decisions made.

## Current state (as of this session)

- **AD.pdf (Anggaran Dasar) — fully ingested and clean.** 239 chunks in
  Supabase, `needs_manual_review = FALSE` on all of them, all embedded with
  citation-context prefix. Every BAB manually verified against actual PDF
  page images (not just OCR) after multiple structural bugs were found.
- **ART, UU 1/1987, Keppres 18/2022, Peraturan Organisasi (439p) — not
  started yet.**
- **RAG pipeline reviewed + fixed.** Retrieval layer built and evaluated
  (20-query harness: hit-rate@5=90%, @10=95%, MRR=0.712). Known gap: pure
  semantic search misses some lexical variants (e.g. "membubarkan" vs
  "Pembubaran") — hybrid search would fix this, not done yet.
- **Frontend built and working.** Next.js App Router in `frontend/`, API
  routes (`app/api/search`, `app/api/documents`) call OpenAI + Supabase
  directly — no separate backend needed. Deploys as a single Vercel app.
  `api/app.py` (Flask) is a reference port, not used in deployment.

## Key architecture decisions

- **Chunking**: structural (BAB > Pasal > Ayat), not fixed-size — preserves
  legal citation boundaries. Max 1500 chars/chunk, oversized ones flagged
  not force-split.
- **Embedding**: `text-embedding-3-small`, 1536 dims. Embeddings use
  `full_citation + "\n" + text` as input (see `embedding/embedder.py:build_embedding_text`)
  so short chunks carry topic context — raw `text` column stays clean for display.
- **DB**: Supabase Postgres + pgvector, HNSW cosine index. Chose this over
  a separate vector DB because metadata (doc_type, pasal_number) and vectors
  live in one place, filterable with plain SQL.
- **Deploy**: all-in-Vercel. Retrieval logic exists in both Python
  (`storage/retrieval.py`) and TypeScript (`frontend/app/api/search/route.ts`)
  — keep both in sync if retrieval logic changes.

## Known source-document problem (will recur on other docs)

AD.pdf's text layer looked fine but was corrupted (font/OCR artifacts:
`PRESIDEN`→`PFIESIDEN`, `1987`→`L987`) on ~half its pages — required
`--ocr` flag to fix via Tesseract. Also found and fixed real parser bugs
that will affect every future document:
1. Header/footer boilerplate detection had an edge-index bug (fixed,
   `parsing/cleaner.py`).
2. Cross-references like "ayat (4)" inside body text could get misread as
   a new Ayat marker mid-sentence, splitting content wrong (fixed with
   noise-burst detection, `parsing/structure_parser.py`).
3. `BAB_RE` doesn't match BAB numbers with trailing letters (e.g. "BAB
   XIIA") since the regex only accepts roman numerals — still unfixed,
   watch for this on other docs (had to fix it manually for AD's Pasal 45A).

## Effective workflow for the next document (learned from AD.pdf)

1. Copy PDF to project root.
2. Sample-check 2-3 pages of raw extracted text for garbling before
   assuming OCR isn't needed (`fitz` quick dump, look for word salad).
3. `python ingest.py --file X.pdf ... --dry-run [--ocr]` — check coverage%
   and flagged count before spending API money.
4. Real ingest (cheap, embedding cost is negligible at this scale).
5. Clear flagged chunks via `python webtool/app.py` (localhost:5050) — much
   faster than manual PDF reading, use manual retype only if the review
   tool reveals a new structural bug worth root-causing.
6. Spot-check *unflagged* chunks too (`scripts/validate_sample.py`) —
   several real bugs were found in chunks that weren't flagged.
7. Re-run `scripts/eval_retrieval.py`-style spot queries (need new
   ground-truth queries per doc) or just try 5 queries in the frontend UI.

For Peraturan Organisasi specifically (439 pages, has table-like lampiran
sections the current parser doesn't handle): use `--use-batch-api` for
cost, and test on a page subset before running the whole thing — the
structure parser is built for prose Pasal/Ayat, not tables.

## Credentials

`.env` (root, Python) and `frontend/.env.local` (Next.js) both need
`OPENAI_API_KEY` + `DB_HOST`/`DB_PORT`/`DB_NAME`/`DB_USER`/`DB_PASSWORD`
(Supabase). Both files are gitignored. If starting a fresh session without
them, ask the user rather than guessing.
