import OpenAI from 'openai';
import type { SearchResult } from '@/types';

let client: OpenAI | null = null;

function getClient(): OpenAI {
  if (!client) {
    client = new OpenAI({ apiKey: process.env.DEEPSEEK_API_KEY, baseURL: 'https://api.deepseek.com' });
  }
  return client;
}

/** Ask the LLM which candidates actually answer the query, ordered by
 * relevance. One batched call per query, not one per candidate — cost and
 * latency scale with query volume, not candidate count. Falls back to the
 * original (vector-ranked) order truncated to k if the call fails or
 * returns something unparseable — a rerank outage should degrade to
 * baseline behavior, not break search. Measured on the eval harness:
 * MRR .712 -> .950 at candidate pool 20, 1.000 at pool 50. */
export async function rerankChunks(
  query: string,
  candidates: SearchResult[],
  k: number
): Promise<SearchResult[]> {
  if (candidates.length === 0) return [];

  const listing = candidates
    .map((c, i) => `[${i}] ${c.full_citation}\n${c.text.slice(0, 500)}`)
    .join('\n\n');
  const prompt =
    `User question (Indonesian legal document search): "${query}"\n\n` +
    `Below are ${candidates.length} candidate excerpts, indexed [0]..[${candidates.length - 1}]. ` +
    `Return ONLY a JSON object: {"relevant": [idx, ...]} listing the indices that ` +
    `actually answer or are directly relevant to the question, ordered from most to ` +
    `least relevant. Exclude excerpts that are only tangentially related or about a ` +
    `different topic. Return at most ${k} indices.\n\n${listing}`;

  try {
    const resp = await getClient().chat.completions.create({
      model: 'deepseek-chat',
      messages: [{ role: 'user', content: prompt }],
      response_format: { type: 'json_object' },
      temperature: 0,
    });
    const content = resp.choices[0].message.content || '{}';
    const parsed = JSON.parse(content) as { relevant?: unknown };
    const indices = Array.isArray(parsed.relevant)
      ? parsed.relevant.filter(
          (i): i is number => typeof i === 'number' && i >= 0 && i < candidates.length
        )
      : [];
    if (indices.length === 0) return candidates.slice(0, k);
    return indices.slice(0, k).map((i) => candidates[i]);
  } catch (err) {
    console.error('rerankChunks failed, falling back to vector order:', err);
    return candidates.slice(0, k);
  }
}
