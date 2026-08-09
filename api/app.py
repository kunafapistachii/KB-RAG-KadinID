"""REST API over the AD-ART knowledge base retrieval layer.

    python api/app.py
    # http://localhost:5051
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dataclasses import asdict

from flask import Flask, jsonify, request
from flask_cors import CORS

from storage.db import get_connection
from storage.retrieval import search_chunks

app = Flask(__name__)
CORS(app)


def error(message: str, status: int = 400):
    return jsonify({"error": {"message": message}}), status


@app.route("/api/search", methods=["POST"])
def search():
    body = request.get_json(silent=True) or {}
    query = (body.get("query") or "").strip()
    if not query:
        return error("'query' is required")

    k = body.get("k", 5)
    try:
        k = max(1, min(int(k), 20))
    except (TypeError, ValueError):
        return error("'k' must be an integer")

    doc_type = body.get("doc_type") or None
    pasal_number = body.get("pasal_number") or None
    doc_id = body.get("doc_id") or None

    conn = get_connection()
    try:
        results = search_chunks(
            conn, query, k=k, doc_type=doc_type,
            pasal_number=pasal_number, doc_id=doc_id,
        )
    finally:
        conn.close()

    return jsonify({"data": [asdict(r) for r in results], "meta": {"query": query, "k": k}})


@app.route("/api/documents", methods=["GET"])
def documents():
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT doc_id, title, doc_type, doc_year, version, upload_date,
                          (SELECT count(*) FROM chunks c WHERE c.doc_id = d.doc_id) AS chunk_count
                   FROM documents d ORDER BY doc_id"""
            )
            rows = cur.fetchall()
    finally:
        conn.close()

    docs = [
        {
            "doc_id": r[0], "title": r[1], "doc_type": r[2], "doc_year": r[3],
            "version": r[4], "upload_date": r[5].isoformat() if r[5] else None,
            "chunk_count": r[6],
        }
        for r in rows
    ]
    return jsonify({"data": docs})


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5051, debug=True)
