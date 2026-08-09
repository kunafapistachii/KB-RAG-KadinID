-- AD-ART Knowledge Base schema
-- Requires PostgreSQL with pgvector extension.

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS documents (
    id              SERIAL PRIMARY KEY,
    doc_id          TEXT UNIQUE NOT NULL,      -- stable slug, e.g. "po_2024" or "uu_1_1987"
    title           TEXT NOT NULL,
    doc_type        TEXT NOT NULL CHECK (doc_type IN ('uu', 'keppres', 'ad', 'art', 'peraturan_organisasi')),
    doc_year        INTEGER,
    source_filename TEXT NOT NULL,
    version         INTEGER NOT NULL DEFAULT 1,
    upload_date     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS chunks (
    id              SERIAL PRIMARY KEY,
    document_id     INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    doc_id          TEXT NOT NULL,             -- denormalized for fast delete-by-doc_id on reingest
    doc_type        TEXT NOT NULL,
    doc_title       TEXT NOT NULL,
    doc_year        INTEGER,
    bab_number      TEXT,
    bab_title       TEXT,
    pasal_number    TEXT,
    ayat_number     TEXT,
    text            TEXT NOT NULL,
    full_citation   TEXT NOT NULL,
    page_start      INTEGER,
    page_end        INTEGER,
    source_file     TEXT NOT NULL,
    needs_manual_review BOOLEAN NOT NULL DEFAULT FALSE,
    embedding       vector(1536),              -- text-embedding-3-small dimension
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Vector similarity search index (cosine distance, matches OpenAI embedding usage)
CREATE INDEX IF NOT EXISTS chunks_embedding_hnsw_idx
    ON chunks USING hnsw (embedding vector_cosine_ops);

-- Filter indexes
CREATE INDEX IF NOT EXISTS chunks_doc_type_idx ON chunks (doc_type);
CREATE INDEX IF NOT EXISTS chunks_pasal_number_idx ON chunks (pasal_number);
CREATE INDEX IF NOT EXISTS chunks_doc_id_idx ON chunks (doc_id);
CREATE INDEX IF NOT EXISTS chunks_needs_review_idx ON chunks (needs_manual_review) WHERE needs_manual_review = TRUE;
