"""Generate embeddings for chunks via OpenAI text-embedding-3-small.

Two modes:
- embed_sync: batched synchronous calls (default — fast turnaround, use for
  reingest / small updates).
- embed_via_batch_api: OpenAI Batch API (50% cheaper, ~24h turnaround) — use
  for large initial indexing runs like the 439-page PO document.
"""

import json
import time

from openai import OpenAI

from config import OPENAI_API_KEY, EMBEDDING_MODEL, EMBEDDING_BATCH_SIZE

_client: OpenAI | None = None


def get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=OPENAI_API_KEY)
    return _client


def build_embedding_text(citation: str, text: str) -> str:
    """Prepend the chunk's citation context before embedding. Without this,
    short chunks (e.g. 'Jika kuorum tidak tercapai, maka Munas ditunda...')
    embed with no signal about which body/topic they belong to, since
    'kuorum' rules differ by pasal. The stored `text` column stays clean for
    display/citation — only the embedding input changes."""
    return f"{citation}\n{text}"


def embed_sync(texts: list[str]) -> list[list[float]]:
    """Embed texts in batches of EMBEDDING_BATCH_SIZE, preserving order."""
    client = get_client()
    embeddings: list[list[float]] = []
    for start in range(0, len(texts), EMBEDDING_BATCH_SIZE):
        batch = texts[start:start + EMBEDDING_BATCH_SIZE]
        resp = client.embeddings.create(model=EMBEDDING_MODEL, input=batch)
        # API preserves input order in resp.data
        embeddings.extend([item.embedding for item in resp.data])
    return embeddings


def embed_via_batch_api(texts: list[str], poll_interval_s: int = 30) -> list[list[float]]:
    """Submit all texts as one OpenAI Batch API job (/v1/embeddings), poll
    until complete, and return embeddings in input order. Blocks until the
    batch finishes (can take up to 24h) — intended for large one-off runs,
    not interactive use."""
    client = get_client()

    lines = []
    for i, text in enumerate(texts):
        lines.append(json.dumps({
            "custom_id": f"chunk-{i}",
            "method": "POST",
            "url": "/v1/embeddings",
            "body": {"model": EMBEDDING_MODEL, "input": text},
        }))
    jsonl_bytes = ("\n".join(lines) + "\n").encode("utf-8")

    uploaded = client.files.create(file=("batch_input.jsonl", jsonl_bytes), purpose="batch")

    batch = client.batches.create(
        input_file_id=uploaded.id,
        endpoint="/v1/embeddings",
        completion_window="24h",
    )

    while True:
        batch = client.batches.retrieve(batch.id)
        if batch.status in ("completed", "failed", "expired", "cancelled"):
            break
        time.sleep(poll_interval_s)

    if batch.status != "completed":
        raise RuntimeError(f"Batch API job ended with status={batch.status}")

    output_text = client.files.content(batch.output_file_id).text
    results_by_id: dict[str, list[float]] = {}
    for line in output_text.strip().split("\n"):
        record = json.loads(line)
        custom_id = record["custom_id"]
        embedding = record["response"]["body"]["data"][0]["embedding"]
        results_by_id[custom_id] = embedding

    return [results_by_id[f"chunk-{i}"] for i in range(len(texts))]
