"""PostgreSQL + pgvector storage layer."""

import psycopg2
import psycopg2.extras

from config import DB_CONFIG
from parsing.chunker import Chunk


def get_connection():
    return psycopg2.connect(**DB_CONFIG)


def upsert_document(conn, doc_id: str, title: str, doc_type: str, doc_year: int | None,
                     source_filename: str) -> int:
    """Insert the document, or bump version if doc_id already exists.
    Returns the internal integer document id."""
    with conn.cursor() as cur:
        cur.execute("SELECT id, version FROM documents WHERE doc_id = %s", (doc_id,))
        row = cur.fetchone()
        if row is None:
            cur.execute(
                """INSERT INTO documents (doc_id, title, doc_type, doc_year, source_filename, version)
                   VALUES (%s, %s, %s, %s, %s, 1) RETURNING id""",
                (doc_id, title, doc_type, doc_year, source_filename),
            )
            document_id = cur.fetchone()[0]
        else:
            document_id, version = row
            cur.execute(
                """UPDATE documents SET title=%s, doc_type=%s, doc_year=%s,
                   source_filename=%s, version=%s, upload_date=now() WHERE id=%s""",
                (title, doc_type, doc_year, source_filename, version + 1, document_id),
            )
    conn.commit()
    return document_id


def delete_chunks_for_doc(conn, doc_id: str) -> int:
    with conn.cursor() as cur:
        cur.execute("DELETE FROM chunks WHERE doc_id = %s", (doc_id,))
        deleted = cur.rowcount
    conn.commit()
    return deleted


def insert_chunks(conn, document_id: int, chunks: list[Chunk], embeddings: list[list[float]]) -> None:
    assert len(chunks) == len(embeddings), "chunk/embedding count mismatch"
    # psycopg2 has no native vector type — pass pgvector's text input format
    # ("[0.1,0.2,...]") and let Postgres cast it on insert.
    rows = [
        (
            document_id, c.doc_id, c.doc_type, c.doc_title, c.doc_year,
            c.bab_number, c.bab_title, c.pasal_number, c.ayat_number,
            c.text, c.full_citation, c.page_start, c.page_end,
            c.source_file, c.needs_manual_review,
            "[" + ",".join(str(x) for x in emb) + "]",
        )
        for c, emb in zip(chunks, embeddings)
    ]
    with conn.cursor() as cur:
        psycopg2.extras.execute_values(
            cur,
            """INSERT INTO chunks (
                   document_id, doc_id, doc_type, doc_title, doc_year,
                   bab_number, bab_title, pasal_number, ayat_number,
                   text, full_citation, page_start, page_end,
                   source_file, needs_manual_review, embedding
               ) VALUES %s""",
            rows,
        )
    conn.commit()


# --- Review-tool helpers (webtool/app.py) ---

def fetch_docs_with_flag_counts(conn) -> list[tuple]:
    with conn.cursor() as cur:
        cur.execute(
            """SELECT doc_id, doc_title, count(*) FILTER (WHERE needs_manual_review) AS flagged,
                      count(*) AS total
               FROM chunks GROUP BY doc_id, doc_title ORDER BY doc_id"""
        )
        return cur.fetchall()


def fetch_next_flagged(conn, doc_id: str, after_id: int | None = None):
    with conn.cursor() as cur:
        if after_id is None:
            cur.execute(
                """SELECT id, full_citation, page_start, page_end, text, source_file
                   FROM chunks WHERE doc_id = %s AND needs_manual_review = TRUE
                   ORDER BY id LIMIT 1""",
                (doc_id,),
            )
        else:
            cur.execute(
                """SELECT id, full_citation, page_start, page_end, text, source_file
                   FROM chunks WHERE doc_id = %s AND needs_manual_review = TRUE AND id > %s
                   ORDER BY id LIMIT 1""",
                (doc_id, after_id),
            )
        return cur.fetchone()


def fetch_flagged_count(conn, doc_id: str) -> int:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT count(*) FROM chunks WHERE doc_id = %s AND needs_manual_review = TRUE",
            (doc_id,),
        )
        return cur.fetchone()[0]


def clear_review_flag(conn, chunk_id: int) -> None:
    with conn.cursor() as cur:
        cur.execute("UPDATE chunks SET needs_manual_review = FALSE WHERE id = %s", (chunk_id,))
    conn.commit()


def update_chunk_correction(conn, chunk_id: int, text: str, embedding: list[float]) -> None:
    emb_str = "[" + ",".join(str(x) for x in embedding) + "]"
    with conn.cursor() as cur:
        cur.execute(
            """UPDATE chunks SET text = %s, embedding = %s, needs_manual_review = FALSE
               WHERE id = %s""",
            (text, emb_str, chunk_id),
        )
    conn.commit()


def delete_chunk_by_id(conn, chunk_id: int) -> None:
    with conn.cursor() as cur:
        cur.execute("DELETE FROM chunks WHERE id = %s", (chunk_id,))
    conn.commit()
