#!/usr/bin/env python
"""Sample random chunks from the DB for manual QA against the source PDF.

Example:
    python scripts/validate_sample.py --doc-id po_2024 --n 10
    python scripts/validate_sample.py --doc-id po_2024 --only-flagged
"""

import argparse
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from storage.db import get_connection


def main():
    parser = argparse.ArgumentParser(description="Sample chunks for manual QA")
    parser.add_argument("--doc-id", required=True)
    parser.add_argument("--n", type=int, default=10, help="Number of random chunks to sample")
    parser.add_argument("--only-flagged", action="store_true",
                         help="Sample only chunks marked needs_manual_review")
    args = parser.parse_args()

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            query = """SELECT id, bab_number, pasal_number, ayat_number, full_citation,
                              page_start, page_end, text, needs_manual_review
                       FROM chunks WHERE doc_id = %s"""
            params = [args.doc_id]
            if args.only_flagged:
                query += " AND needs_manual_review = TRUE"
            cur.execute(query, params)
            rows = cur.fetchall()
    finally:
        conn.close()

    if not rows:
        print(f"No chunks found for doc_id={args.doc_id!r}"
              f"{' with needs_manual_review=TRUE' if args.only_flagged else ''}.")
        return

    sample = random.sample(rows, min(args.n, len(rows)))

    print(f"{len(rows)} total chunks for doc_id={args.doc_id!r}. Showing {len(sample)} sample(s):\n")
    for row in sample:
        chunk_id, bab, pasal, ayat, citation, page_start, page_end, text, needs_review = row
        print("=" * 80)
        print(f"chunk_id={chunk_id}  pages={page_start}-{page_end}  "
              f"needs_manual_review={needs_review}")
        print(f"citation: {citation}")
        print("-" * 80)
        print(text[:800] + ("..." if len(text) > 800 else ""))
        print()
        print(">>> Open the PDF at the page range above and confirm this text matches.")
        print()


if __name__ == "__main__":
    main()
