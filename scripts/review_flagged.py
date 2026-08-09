#!/usr/bin/env python
"""Interactive manual review for chunks flagged needs_manual_review=True.

Run this yourself in a real terminal (needs interactive stdin) — open the
source PDF at the printed page range alongside it.

Example:
    python scripts/review_flagged.py --doc-id ad_2026

Per chunk you can:
    [Enter]   keep as-is, clear the review flag (current text is actually fine)
    <text>    type the corrected text (end with a line containing only ".")
              re-embeds it and saves — clears the flag
    d         delete this chunk entirely (e.g. a duplicate/garbage row)
    s         skip, leave flagged for later
    q         quit — progress so far is already saved, rerun anytime to resume
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from storage.db import get_connection
from embedding.embedder import embed_sync, build_embedding_text


def read_multiline_text() -> str:
    lines = []
    while True:
        line = input()
        if line.strip() == ".":
            break
        lines.append(line)
    return "\n".join(lines).strip()


def main():
    parser = argparse.ArgumentParser(description="Manually review needs_manual_review chunks")
    parser.add_argument("--doc-id", required=True)
    args = parser.parse_args()

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT id, full_citation, page_start, page_end, text
                   FROM chunks WHERE doc_id = %s AND needs_manual_review = TRUE
                   ORDER BY id""",
                (args.doc_id,),
            )
            rows = cur.fetchall()

        if not rows:
            print(f"No flagged chunks left for doc_id={args.doc_id!r}.")
            return

        print(f"{len(rows)} flagged chunk(s) to review for doc_id={args.doc_id!r}.\n")

        for i, (chunk_id, citation, page_start, page_end, text) in enumerate(rows, 1):
            print("=" * 80)
            print(f"[{i}/{len(rows)}] chunk_id={chunk_id}  pages={page_start}-{page_end}")
            print(f"citation: {citation}")
            print("-" * 80)
            print(text)
            print("-" * 80)
            print("[Enter]=keep  <type text>+.=correct  d=delete  s=skip  q=quit")
            first_line = input("> ")

            if first_line.strip().lower() == "q":
                print("Stopping. Rerun the same command later to resume.")
                break
            if first_line.strip().lower() == "s":
                continue
            if first_line.strip().lower() == "d":
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM chunks WHERE id = %s", (chunk_id,))
                conn.commit()
                print("Deleted.")
                continue
            if first_line.strip() == "":
                with conn.cursor() as cur:
                    cur.execute("UPDATE chunks SET needs_manual_review = FALSE WHERE id = %s", (chunk_id,))
                conn.commit()
                print("Kept as-is, flag cleared.")
                continue

            # Any other input starts a corrected-text entry; first_line is its first line.
            rest = read_multiline_text() if first_line.strip() != "." else ""
            corrected = (first_line + "\n" + rest).strip() if rest else first_line.strip()
            if not corrected:
                print("Empty text, skipping (nothing changed).")
                continue

            embedding = embed_sync([build_embedding_text(citation, corrected)])[0]
            emb_str = "[" + ",".join(str(x) for x in embedding) + "]"
            with conn.cursor() as cur:
                cur.execute(
                    """UPDATE chunks SET text = %s, embedding = %s, needs_manual_review = FALSE
                       WHERE id = %s""",
                    (corrected, emb_str, chunk_id),
                )
            conn.commit()
            print("Updated and re-embedded.")

        with conn.cursor() as cur:
            cur.execute(
                "SELECT count(*) FROM chunks WHERE doc_id = %s AND needs_manual_review = TRUE",
                (args.doc_id,),
            )
            remaining = cur.fetchone()[0]
        print(f"\n{remaining} chunk(s) still flagged for doc_id={args.doc_id!r}.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
