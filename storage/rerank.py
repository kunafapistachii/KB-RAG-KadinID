"""LLM relevance reranking over an already-retrieved candidate set.

One batched call per query (not one per candidate) — cost and latency both
scale with query volume, not candidate count. DeepSeek is OpenAI-compatible,
so this reuses the same client shape as embedding/embedder.py.
"""

import json

from openai import OpenAI

import config

_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=config.DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")
    return _client


def rerank_chunks(query: str, candidates: list, k: int = 5) -> list:
    """Ask the LLM which candidates actually answer the query, ordered by
    relevance. Falls back to the original (vector-ranked) order truncated to
    k if the LLM call fails or returns something unparseable — a rerank
    outage should degrade to baseline behavior, not break search."""
    if not candidates:
        return []

    listing = "\n\n".join(
        f"[{i}] {c.full_citation}\n{c.text[:500]}" for i, c in enumerate(candidates)
    )
    prompt = (
        f'User question (Indonesian legal document search): "{query}"\n\n'
        f"Below are {len(candidates)} candidate excerpts, indexed [0]..[{len(candidates) - 1}]. "
        f'Return ONLY a JSON object: {{"relevant": [idx, ...]}} listing the indices that '
        f"actually answer or are directly relevant to the question, ordered from most to "
        f"least relevant. Exclude excerpts that are only tangentially related or about a "
        f"different topic. Return at most {k} indices.\n\n{listing}"
    )

    try:
        resp = _get_client().chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0,
        )
        data = json.loads(resp.choices[0].message.content)
        indices = [
            i for i in data.get("relevant", [])
            if isinstance(i, int) and 0 <= i < len(candidates)
        ]
        if not indices:
            return candidates[:k]
        return [candidates[i] for i in indices[:k]]
    except Exception:
        return candidates[:k]
