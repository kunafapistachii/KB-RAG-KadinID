"""Vector similarity search over chunks (the 'R' in RAG)."""

from dataclasses import dataclass

from embedding.embedder import embed_sync


@dataclass
class SearchResult:
    chunk_id: int
    doc_id: str
    doc_type: str
    doc_title: str
    full_citation: str
    bab_number: str | None
    pasal_number: str | None
    pasal_title: str | None
    ayat_number: str | None
    text: str
    page_start: int
    page_end: int
    source_file: str
    similarity: float  # cosine similarity, 1.0 = identical, higher = closer


def embed_query(query: str) -> list[float]:
    """Embed a raw user query — no citation prefix (that's only for chunks,
    to give them topic context; a query is already a self-contained ask)."""
    return embed_sync([query])[0]


def search_chunks(
    conn,
    query: str,
    k: int = 5,
    doc_type: str | None = None,
    pasal_number: str | None = None,
    doc_id: str | None = None,
    include_flagged: bool = False,
) -> list[SearchResult]:
    """Embed the query and return the k nearest chunks by cosine similarity.
    Excludes needs_manual_review=TRUE chunks by default — unverified text
    shouldn't be surfaced as a legal answer."""
    query_embedding = embed_query(query)
    emb_str = "[" + ",".join(str(x) for x in query_embedding) + "]"

    where = []
    params: list = []
    if not include_flagged:
        where.append("needs_manual_review = FALSE")
    if doc_type:
        where.append("doc_type = %s")
        params.append(doc_type)
    if pasal_number:
        where.append("pasal_number = %s")
        params.append(pasal_number)
    if doc_id:
        where.append("doc_id = %s")
        params.append(doc_id)
    where_clause = ("WHERE " + " AND ".join(where)) if where else ""

    sql = f"""
        SELECT id, doc_id, doc_type, doc_title, full_citation,
               bab_number, pasal_number, pasal_title, ayat_number, text,
               page_start, page_end, source_file,
               1 - (embedding <=> %s::vector) AS similarity
        FROM chunks
        {where_clause}
        ORDER BY embedding <=> %s::vector
        LIMIT %s
    """
    params_final = [emb_str, *params, emb_str, k]

    with conn.cursor() as cur:
        cur.execute(sql, params_final)
        rows = cur.fetchall()

    return [
        SearchResult(
            chunk_id=r[0], doc_id=r[1], doc_type=r[2], doc_title=r[3],
            full_citation=r[4], bab_number=r[5], pasal_number=r[6], pasal_title=r[7],
            ayat_number=r[8],
            text=r[9], page_start=r[10], page_end=r[11], source_file=r[12],
            similarity=float(r[13]),
        )
        for r in rows
    ]
