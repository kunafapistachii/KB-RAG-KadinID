# AD-ART Knowledge Base — Ingestion Pipeline

Parsing + ingestion pipeline for Indonesian legal/organizational documents
(UU, Keppres, AD, ART, Peraturan Organisasi) into a pgvector-backed knowledge
base. No UI/chat here — extraction, cleaning, structure parsing, chunking,
embedding, and storage only.

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
   OCR fallback (optional) also needs the Tesseract binary on your system,
   plus the Indonesian language pack (`tesseract-ocr-ind`).

2. Create `.env` from `.env.example` and fill in `OPENAI_API_KEY` and DB
   credentials.

3. Create the database and schema:
   ```bash
   createdb adart_kb
   psql -d adart_kb -f schema.sql
   ```
   Requires the `pgvector` extension installed on the Postgres server.

## Usage

Ingest a new document:
```bash
python ingest.py --file path/to/ad.pdf --doc-type ad --doc-title "Anggaran Dasar" --doc-year 2024
```

Dry run (extraction → chunking only, no API calls or DB writes — use this
first to sanity-check parsing before spending on embeddings):
```bash
python ingest.py --file path/to/ad.pdf --doc-type ad --doc-title "Anggaran Dasar" --doc-year 2024 --dry-run
```

Force OCR for a scanned PDF:
```bash
python ingest.py --file scan.pdf --doc-type po --doc-title "..." --doc-year 2024 --ocr
```

Large initial index (e.g. the 439-page PO) via OpenAI Batch API (50% cheaper,
up to 24h turnaround):
```bash
python ingest.py --file po.pdf --doc-type peraturan_organisasi --doc-title "Peraturan Organisasi" --doc-year 2024 --use-batch-api
```

Re-ingest an updated document (replaces its chunks only, doesn't touch other docs):
```bash
python reingest.py --file po_v2.pdf --doc-id peraturan_organisasi_2024 --doc-type peraturan_organisasi --doc-title "Peraturan Organisasi" --doc-year 2024
```

## Recommended order

Start with a short document (AD or ART) to validate the pipeline before
attempting the 439-page PO. Use `--dry-run` first on each new document type.

## Reading the coverage report

Each run prints:
```
[parse] coverage: 94.3% (18420/19532 chars assigned)
[parse] 5 BAB, 42 Pasal, 3 orphan block(s)
[chunk] 51 chunks built, 2 flagged needs_manual_review
```

- **coverage%**: share of extracted text characters that were assigned to a
  BAB/Pasal/Ayat structure. Low coverage means the regex patterns in
  `parsing/structure_parser.py` (`BAB_RE`, `PASAL_RE`, `AYAT_RE`, `HURUF_RE`)
  don't match this document's formatting — inspect the orphan blocks.
- **orphan blocks**: text that appeared outside any Pasal (e.g. preamble,
  signature blocks, or a differently-formatted lampiran/attachment). These
  become chunks with `needs_manual_review = TRUE` instead of being forced
  into the wrong Pasal.
- **needs_manual_review**: also set when a chunk exceeds 1500 characters with
  no Ayat structure to split on (can't safely subdivide without risking a
  wrong citation).

Query flagged chunks directly:
```sql
SELECT doc_id, pasal_number, full_citation, page_start, page_end
FROM chunks WHERE needs_manual_review = TRUE;
```

## Clearing the review queue

Two ways to work through `needs_manual_review` chunks:

**CLI** (`scripts/review_flagged.py`) — one chunk at a time in the terminal,
open the source PDF yourself alongside it:
```bash
python scripts/review_flagged.py --doc-id ad_2026
```

**Web tool** (`webtool/app.py`) — same workflow in a browser, auto-renders
the relevant PDF page(s) next to an editable text box (no manual PDF
flipping). Internal/throwaway tool, not the project's real frontend:
```bash
python webtool/app.py
# open http://localhost:5050
```
Per chunk: **Save correction** (retypes + re-embeds), **Keep as-is** (text
was fine, just clears the flag), **Skip** (leave for later), or **Delete**
(e.g. a duplicate/garbage row with no real content to recover).

## Validating parsed chunks against the source PDF

```bash
python scripts/validate_sample.py --doc-id ad_2024 --n 10
python scripts/validate_sample.py --doc-id ad_2024 --only-flagged
```
Prints citation + page range + text for each sampled chunk — open the PDF at
that page range and confirm the text matches before trusting the parse.

## Retrieval (search)

Embeddings include a citation-context prefix (`full_citation + text`) before
being sent to OpenAI — without it, short chunks like "Jika kuorum tidak
tercapai..." carry no signal about which body/pasal they belong to. Stored
`text` stays clean; only the embedding input changes. If you ingested docs
before this was added, re-embed them:
```bash
python scripts/reembed_with_context.py --doc-id ad_2026
```

Query via `storage/retrieval.py` (`search_chunks`) directly from Python, or
through `frontend/app/api/search/route.ts` — the frontend talks straight to
Supabase + OpenAI itself (Next.js API routes), no separate backend process.
`api/app.py` (Flask) is the same logic ported to Python and kept only as a
reference/fallback if you ever need a standalone API outside Vercel — the
deployed app does not use it.
Excludes `needs_manual_review = TRUE` chunks by default.

## Evaluating retrieval quality

```bash
python scripts/eval_retrieval.py
```
Runs 20 real queries with manually-verified ground-truth citations against
`ad_2026`, reports hit-rate@3/5/10 and MRR, and lists queries that missed or
ranked below top-3 for failure analysis. Re-run after any chunking/embedding
change — don't trust retrieval quality without a number.

## Frontend

`frontend/` — Next.js App Router. Search + embedding + DB access all happen
server-side in its own API routes (`app/api/search`, `app/api/documents`) —
deploys as a single app, no separate backend to host.
```bash
cd frontend && npm install && npm run dev
# open http://localhost:3000
```
Needs `OPENAI_API_KEY` and `DB_HOST`/`DB_PORT`/`DB_NAME`/`DB_USER`/
`DB_PASSWORD` in `frontend/.env.local` (same Supabase credentials as the
root `.env`). Deploy target: Vercel — set the same env vars in the project
settings; Supabase stays as-is, nothing else to host.

## Project layout

```
extraction/   PDF text extraction (PyMuPDF) + optional OCR fallback (pytesseract)
parsing/      header/footer cleaning, BAB/Pasal/Ayat structure parser, chunker
embedding/    OpenAI text-embedding-3-small (sync batched + Batch API)
storage/      psycopg2 + pgvector storage layer, retrieval (vector search)
api/          Flask REST API over retrieval — reference only, not deployed
frontend/     Next.js search UI + API routes (search/embed/DB, deploys to Vercel)
scripts/      shared pipeline core, validation sampler, eval harness, re-embed tool
ingest.py     CLI entry point for new documents
reingest.py   CLI entry point for updating existing documents
schema.sql    documents + chunks tables, pgvector indexes
```
