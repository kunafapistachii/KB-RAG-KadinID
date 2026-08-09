import OpenAI from 'openai';

let client: OpenAI | null = null;

function getClient(): OpenAI {
  if (!client) {
    client = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });
  }
  return client;
}

const EMBEDDING_MODEL = 'text-embedding-3-small';

/** Embed a raw user query — no citation prefix (only chunks get that, to
 * give short legal snippets topic context; a query is already self-contained). */
export async function embedQuery(query: string): Promise<number[]> {
  const resp = await getClient().embeddings.create({
    model: EMBEDDING_MODEL,
    input: query,
  });
  return resp.data[0].embedding;
}
