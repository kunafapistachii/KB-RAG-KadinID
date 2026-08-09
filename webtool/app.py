"""Minimal local web tool for manually reviewing needs_manual_review chunks.

Not the project's real frontend (that's Next.js, a later stage) — this is a
throwaway internal tool scoped to clearing the review queue with a browser
instead of a terminal. Run with:

    python webtool/app.py

Then open http://localhost:5050
"""

import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import fitz
from flask import Flask, Response, redirect, render_template, request, url_for

from embedding.embedder import embed_sync, build_embedding_text
from storage.db import (
    clear_review_flag,
    delete_chunk_by_id,
    fetch_docs_with_flag_counts,
    fetch_flagged_count,
    fetch_next_flagged,
    get_connection,
    update_chunk_correction,
)

app = Flask(__name__)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@app.route("/")
def index():
    conn = get_connection()
    try:
        docs = fetch_docs_with_flag_counts(conn)
    finally:
        conn.close()
    return render_template("index.html", docs=docs)


@app.route("/review/<doc_id>")
def review(doc_id):
    after_id = request.args.get("after", type=int)
    conn = get_connection()
    try:
        chunk = fetch_next_flagged(conn, doc_id, after_id)
        remaining = fetch_flagged_count(conn, doc_id)
    finally:
        conn.close()

    if chunk is None:
        return render_template("done.html", doc_id=doc_id)

    chunk_id, citation, page_start, page_end, text, source_file = chunk
    return render_template(
        "review.html",
        doc_id=doc_id, chunk_id=chunk_id, citation=citation,
        page_start=page_start, page_end=page_end, text=text,
        source_file=source_file, remaining=remaining,
    )


@app.route("/review/<doc_id>/<int:chunk_id>/keep", methods=["POST"])
def keep(doc_id, chunk_id):
    conn = get_connection()
    try:
        clear_review_flag(conn, chunk_id)
    finally:
        conn.close()
    return redirect(url_for("review", doc_id=doc_id))


@app.route("/review/<doc_id>/<int:chunk_id>/skip", methods=["POST"])
def skip(doc_id, chunk_id):
    return redirect(url_for("review", doc_id=doc_id, after=chunk_id))


@app.route("/review/<doc_id>/<int:chunk_id>/delete", methods=["POST"])
def delete(doc_id, chunk_id):
    conn = get_connection()
    try:
        delete_chunk_by_id(conn, chunk_id)
    finally:
        conn.close()
    return redirect(url_for("review", doc_id=doc_id))


@app.route("/review/<doc_id>/<int:chunk_id>/save", methods=["POST"])
def save(doc_id, chunk_id):
    corrected = request.form.get("text", "").strip()
    if not corrected:
        return redirect(url_for("review", doc_id=doc_id))
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT full_citation FROM chunks WHERE id = %s", (chunk_id,))
            citation = cur.fetchone()[0]
        embedding = embed_sync([build_embedding_text(citation, corrected)])[0]
        update_chunk_correction(conn, chunk_id, corrected, embedding)
    finally:
        conn.close()
    return redirect(url_for("review", doc_id=doc_id))


@app.route("/page-image/<source_file>/<int:page_num>")
def page_image(source_file, page_num):
    """Render one PDF page (1-indexed) to PNG so reviewers don't have to
    flip through the source file by hand."""
    safe_name = os.path.basename(source_file)  # no path traversal
    pdf_path = os.path.join(PROJECT_ROOT, safe_name)
    if not os.path.exists(pdf_path):
        return Response(f"PDF not found: {safe_name}", status=404)

    doc = fitz.open(pdf_path)
    try:
        if page_num < 1 or page_num > doc.page_count:
            return Response("Page out of range", status=404)
        page = doc[page_num - 1]
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
        png_bytes = pix.tobytes("png")
    finally:
        doc.close()
    return Response(png_bytes, mimetype="image/png")


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5050, debug=True)
