#!/usr/bin/env python
"""Retrieval evaluation harness for the AD-ART knowledge base.

20 natural-language queries against AD.pdf content, each with a manually
verified ground-truth (pasal_number, ayat_number) — the citation a human
reviewer would expect to come back. Single-relevant-doc-per-query is the
realistic shape for legal citation lookup (not multi-doc ranking), so the
metrics are hit-rate@k and MRR rather than generic precision/recall@k.

    python scripts/eval_retrieval.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from storage.db import get_connection
from storage.retrieval import search_chunks

DOC_ID = "ad_2026"

# (query, expected_pasal_number, expected_ayat_number_or_None)
TEST_CASES = [
    ("berapa lama masa jabatan pengurus Kadin?", "36", "1"),
    ("apa syarat kuorum Musyawarah Nasional supaya sah?", "17", "10"),
    ("siapa saja yang termasuk anggota luar biasa Kadin?", "32", "2"),
    ("bagaimana proses pergantian antarwaktu Ketua Umum kalau berhalangan tetap?", "38", "4"),
    ("apa tugas dan wewenang Dewan Pertimbangan Kadin Indonesia?", "21", "5"),
    ("berapa syarat sah kuorum Musyawarah Provinsi?", "25", "10"),
    ("apa itu Musyawarah Nasional Luar Biasa atau Munaslub?", "18", "1"),
    ("dari mana saja sumber dana organisasi Kadin?", "39", "1"),
    ("bagaimana cara membubarkan organisasi Kadin?", "42", None),
    ("apa saja hak anggota biasa Kadin?", "33", "1"),
    ("berapa kali Ketua Umum Kadin bisa dipilih kembali?", "36", "2"),
    ("apa fungsi Sekretariat Kadin Indonesia?", "24", "1"),
    ("siapa yang mengesahkan Dewan Pengurus Kadin Provinsi hasil Muprov?", "22", "7"),
    ("apa syarat menjadi Direktur Eksekutif Kadin?", "24", "4"),
    ("berapa kali setahun Rapimnas diadakan?", "23", "2"),
    ("apa wewenang Musyawarah Nasional?", "17", "8"),
    ("apa itu Musyawarah Nasional Khusus atau Munassus?", "19", "1"),
    ("apa kewajiban setiap anggota Kadin?", "34", None),
    ("kapan Anggaran Dasar ini mulai berlaku secara resmi?", "45", "2"),
    ("apa saja unsur perangkat organisasi Kadin Indonesia?", "16", "1"),
]

K_VALUES = [3, 5, 10]


def matches(result, expected_pasal, expected_ayat):
    if result.pasal_number != expected_pasal:
        return False
    if expected_ayat is None:
        return True
    return result.ayat_number == expected_ayat


def main():
    conn = get_connection()
    try:
        hits_at_k = {k: 0 for k in K_VALUES}
        reciprocal_ranks = []
        failures = []

        for query, exp_pasal, exp_ayat in TEST_CASES:
            results = search_chunks(conn, query, k=max(K_VALUES), doc_id=DOC_ID)
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
        print(f"=== Retrieval Evaluation ({n} queries, doc_id={DOC_ID}) ===\n")
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
