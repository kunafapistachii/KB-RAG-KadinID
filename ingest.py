#!/usr/bin/env python
"""Ingest a new document into the AD-ART Knowledge Base.

Example:
    python ingest.py --file path/to/doc.pdf --doc-type peraturan_organisasi \
        --doc-title "Peraturan Organisasi" --doc-year 2024
"""

import argparse

from scripts.pipeline_core import run_pipeline

DOC_TYPES = ["uu", "keppres", "ad", "art", "peraturan_organisasi"]


def main():
    parser = argparse.ArgumentParser(description="Ingest a legal document PDF into the knowledge base")
    parser.add_argument("--file", required=True, help="Path to the source PDF")
    parser.add_argument("--doc-type", required=True, choices=DOC_TYPES)
    parser.add_argument("--doc-title", required=True)
    parser.add_argument("--doc-year", type=int, default=None)
    parser.add_argument("--doc-id", default=None, help="Override the auto-generated doc_id")
    parser.add_argument("--ocr", action="store_true", help="Force OCR extraction (scanned PDFs)")
    parser.add_argument("--use-batch-api", action="store_true",
                         help="Use OpenAI Batch API for embeddings (50%% cheaper, up to 24h turnaround)")
    parser.add_argument("--dry-run", action="store_true",
                         help="Run extraction/cleaning/parsing/chunking only — skip embedding and DB writes")
    args = parser.parse_args()

    run_pipeline(
        pdf_path=args.file,
        doc_type=args.doc_type,
        doc_title=args.doc_title,
        doc_year=args.doc_year,
        doc_id=args.doc_id,
        force_ocr=args.ocr,
        use_batch_api=args.use_batch_api,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
