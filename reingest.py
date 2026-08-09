#!/usr/bin/env python
"""Re-ingest an updated document: re-runs the full pipeline for one PDF and
replaces its existing chunks (matched by --doc-id) without touching other
documents. Use this when a source PDF changes, not for first-time ingestion.

Example:
    python reingest.py --file path/to/doc_v2.pdf --doc-id po_2024 \
        --doc-type peraturan_organisasi --doc-title "Peraturan Organisasi" --doc-year 2024
"""

import argparse

from scripts.pipeline_core import run_pipeline
from storage.db import get_connection

DOC_TYPES = ["uu", "keppres", "ad", "art", "peraturan_organisasi"]


def main():
    parser = argparse.ArgumentParser(description="Re-ingest an existing document (replaces its chunks)")
    parser.add_argument("--file", required=True, help="Path to the updated source PDF")
    parser.add_argument("--doc-id", required=True, help="Existing doc_id to replace")
    parser.add_argument("--doc-type", required=True, choices=DOC_TYPES)
    parser.add_argument("--doc-title", required=True)
    parser.add_argument("--doc-year", type=int, default=None)
    parser.add_argument("--ocr", action="store_true")
    parser.add_argument("--use-batch-api", action="store_true")
    args = parser.parse_args()

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM documents WHERE doc_id = %s", (args.doc_id,))
            exists = cur.fetchone() is not None
    finally:
        conn.close()

    if not exists:
        print(f"[reingest] WARNING: doc_id={args.doc_id!r} not found in documents table — "
              f"this will create it as new instead of updating.")

    run_pipeline(
        pdf_path=args.file,
        doc_type=args.doc_type,
        doc_title=args.doc_title,
        doc_year=args.doc_year,
        doc_id=args.doc_id,
        force_ocr=args.ocr,
        use_batch_api=args.use_batch_api,
        dry_run=False,
    )


if __name__ == "__main__":
    main()
