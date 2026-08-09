"""Shared extraction -> cleaning -> parsing -> chunking -> embedding -> storage
pipeline used by both ingest.py and reingest.py."""

import os
import re

from extraction.pdf_extractor import extract_pages, is_likely_scanned
from extraction.ocr_fallback import extract_pages_ocr
from parsing.cleaner import clean_pages
from parsing.structure_parser import parse_structure
from parsing.chunker import build_chunks
from embedding.embedder import embed_sync, embed_via_batch_api, build_embedding_text
from storage.db import get_connection, upsert_document, delete_chunks_for_doc, insert_chunks


def slugify_doc_id(doc_type: str, doc_title: str, doc_year: int | None) -> str:
    base = f"{doc_type}_{doc_year}" if doc_year else f"{doc_type}_{doc_title}"
    slug = re.sub(r"[^a-z0-9]+", "_", base.lower()).strip("_")
    return slug


def run_pipeline(
    pdf_path: str,
    doc_type: str,
    doc_title: str,
    doc_year: int | None,
    doc_id: str | None = None,
    force_ocr: bool = False,
    use_batch_api: bool = False,
    dry_run: bool = False,
):
    """Runs the full pipeline for one PDF. If dry_run, skips embedding/storage
    and only returns the coverage report + chunks for inspection."""
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(pdf_path)

    doc_id = doc_id or slugify_doc_id(doc_type, doc_title, doc_year)
    source_file = os.path.basename(pdf_path)

    if force_ocr:
        print(f"[extract] OCR mode forced for {source_file}")
        pages = extract_pages_ocr(pdf_path)
    else:
        if is_likely_scanned(pdf_path):
            print(f"[extract] WARNING: {source_file} looks scanned (little/no extractable text). "
                  f"Re-run with --ocr if extraction quality looks bad.")
        pages = extract_pages(pdf_path)
    print(f"[extract] {len(pages)} pages extracted")

    cleaned_pages, clean_report = clean_pages(pages)
    print(f"[clean] boilerplate lines removed: {len(clean_report.detected_boilerplate)}")

    parse_result = parse_structure(cleaned_pages)
    print(f"[parse] coverage: {parse_result.coverage_percent}% "
          f"({parse_result.assigned_chars}/{parse_result.total_chars} chars assigned)")
    print(f"[parse] {len(parse_result.bab_list)} BAB, "
          f"{sum(len(b.pasal_list) for b in parse_result.bab_list)} Pasal, "
          f"{len(parse_result.orphan_blocks)} orphan block(s)")

    chunks = build_chunks(parse_result, doc_id, doc_type, doc_title, doc_year, source_file)
    review_count = sum(1 for c in chunks if c.needs_manual_review)
    print(f"[chunk] {len(chunks)} chunks built, {review_count} flagged needs_manual_review")

    if dry_run:
        return chunks, parse_result

    texts = [build_embedding_text(c.full_citation, c.text) for c in chunks]
    if use_batch_api:
        print("[embed] submitting to OpenAI Batch API (this can take up to 24h)...")
        embeddings = embed_via_batch_api(texts)
    else:
        print(f"[embed] embedding {len(texts)} chunks synchronously...")
        embeddings = embed_sync(texts)

    conn = get_connection()
    try:
        document_id = upsert_document(conn, doc_id, doc_title, doc_type, doc_year, source_file)
        deleted = delete_chunks_for_doc(conn, doc_id)
        if deleted:
            print(f"[storage] removed {deleted} existing chunk(s) for doc_id={doc_id}")
        insert_chunks(conn, document_id, chunks, embeddings)
        print(f"[storage] inserted {len(chunks)} chunks for doc_id={doc_id}")
    finally:
        conn.close()

    return chunks, parse_result
