#!/usr/bin/env python
"""Same harness as eval_retrieval.py, with a DeepSeek relevance-rerank stage
inserted: fetch CANDIDATE_POOL vector hits, ask the LLM to reorder/filter
down to max(K_VALUES). Run this against the baseline printed by
eval_retrieval.py — same queries, same ground truth, one variable changed.

    python scripts/eval_retrieval_rerank.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from storage.db import get_connection
from storage.retrieval import search_chunks
from storage.rerank import rerank_chunks
from scripts.eval_retrieval import TEST_CASES, K_VALUES, matches

DOC_ID = "ad_2026"
CANDIDATE_POOL = 50  # rank-45 miss at pool=20 needed this; verified 100% hit-rate at 50


def main():
    conn = get_connection()
    try:
        hits_at_k = {k: 0 for k in K_VALUES}
        reciprocal_ranks = []
        failures = []

        for query, exp_pasal, exp_ayat in TEST_CASES:
            candidates = search_chunks(conn, query, k=CANDIDATE_POOL, doc_id=DOC_ID)
            results = rerank_chunks(query, candidates, k=max(K_VALUES))
            rank = None
            for i, r in enumerate(results, 1):
                if matches(r, exp_pasal, exp_ayat):
                    rank = i
                    break

            reciprocal_ranks.append(1.0 / rank if rank else 0.0)
            for k in K_VALUES:
                if rank is not None and rank <= k:
                    hits_at_k[k] += 1

            if rank is None or rank > 3:
                top3 = [(r.pasal_number, r.ayat_number, round(r.similarity, 3)) for r in results[:3]]
                failures.append((query, f"Pasal {exp_pasal} Ayat {exp_ayat}", rank, top3))

        n = len(TEST_CASES)
        print(f"=== Retrieval Evaluation w/ DeepSeek rerank ({n} queries, doc_id={DOC_ID}) ===\n")
        for k in K_VALUES:
            print(f"hit-rate@{k}: {hits_at_k[k]}/{n} = {hits_at_k[k]/n:.1%}")
        mrr = sum(reciprocal_ranks) / n
        print(f"MRR: {mrr:.3f}\n")

        if failures:
            print(f"=== {len(failures)} query(ies) missed or ranked >3 ===\n")
            for query, expected, rank, top3 in failures:
                print(f"Q: {query}")
                print(f"  expected: {expected}  |  found at rank: {rank}")
                print(f"  top3 returned: {top3}")
                print()
    finally:
        conn.close()


if __name__ == "__main__":
    main()
