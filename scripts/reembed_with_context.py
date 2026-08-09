#!/usr/bin/env python
"""One-off: re-embed existing chunks with citation-context-prefixed input,
without touching stored text/structure. Run after the embedding pipeline's
context-prefix behavior changes, to bring already-ingested docs in line.

Example:
    python scripts/reembed_with_context.py --doc-id ad_2026
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from storage.db import get_connection
from embedding.embedder import embed_sync, build_embedding_text
from config import EMBEDDING_BATCH_SIZE


def main():
    parser = argparse.ArgumentParser(description="Re-embed chunks with citation context prefix")
    parser.add_argument("--doc-id", required=True)
    args = parser.parse_args()

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, full_citation, text FROM chunks WHERE doc_id = %s ORDER BY id",
                (args.doc_id,),
            )
            rows = cur.fetchall()

        if not rows:
            print(f"No chunks found for doc_id={args.doc_id!r}.")
            return

        print(f"Re-embedding {len(rows)} chunks for doc_id={args.doc_id!r}...")

        for start in range(0, len(rows), EMBEDDING_BATCH_SIZE):
            batch = rows[start:start + EMBEDDING_BATCH_SIZE]
            inputs = [build_embedding_text(citation, text) for _, citation, text in batch]
            embeddings = embed_sync(inputs)
            with conn.cursor() as cur:
                for (chunk_id, _, _), emb in zip(batch, embeddings):
                    emb_str = "[" + ",".join(str(x) for x in emb) + "]"
                    cur.execute("UPDATE chunks SET embedding = %s WHERE id = %s", (emb_str, chunk_id))
            conn.commit()
            print(f"  {min(start + EMBEDDING_BATCH_SIZE, len(rows))}/{len(rows)} done")

        print("Done.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
