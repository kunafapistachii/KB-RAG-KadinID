import { NextRequest, NextResponse } from 'next/server';
import { getPool } from '@/lib/db';
import { embedQuery } from '@/lib/embedding';
import { rerankChunks, type RerankDebug } from '@/lib/rerank';

export const runtime = 'nodejs';

// Widened vector pool the reranker chooses from before truncating to the
// requested k. Verified against the 20-query eval harness: pool=20 missed
// one query whose true match sat at vector rank 45; pool=50 hit 100%.
const RERANK_CANDIDATE_POOL = 50;

interface SearchBody {
  query?: string;
  k?: number;
  doc_type?: string;
  pasal_number?: string;
  doc_id?: string;
  debug?: boolean;
}

export async function POST(req: NextRequest) {
  let body: SearchBody;
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: { message: 'Invalid JSON body' } }, { status: 400 });
  }

  const query = (body.query || '').trim();
  if (!query) {
    return NextResponse.json({ error: { message: "'query' is required" } }, { status: 400 });
  }

  const k = Math.max(1, Math.min(Number(body.k) || 5, 20));

  const where: string[] = ['needs_manual_review = FALSE'];
  const params: unknown[] = [];
  let paramIndex = 1;

  if (body.doc_type) {
    where.push(`doc_type = $${++paramIndex}`);
    params.push(body.doc_type);
  }
  if (body.pasal_number) {
    where.push(`pasal_number = $${++paramIndex}`);
    params.push(body.pasal_number);
  }
  if (body.doc_id) {
    where.push(`doc_id = $${++paramIndex}`);
    params.push(body.doc_id);
  }

  let queryEmbedding: number[];
  try {
    queryEmbedding = await embedQuery(query);
  } catch (err) {
    return NextResponse.json(
      { error: { message: `Embedding failed: ${(err as Error).message}` } },
      { status: 502 }
    );
  }
  const embStr = `[${queryEmbedding.join(',')}]`;

  const sql = `
    SELECT id, doc_id, doc_type, doc_title, full_citation,
           bab_number, pasal_number, ayat_number, text,
           page_start, page_end, source_file,
           1 - (embedding <=> $1::vector) AS similarity
    FROM chunks
    WHERE ${where.join(' AND ')}
    ORDER BY embedding <=> $1::vector
    LIMIT ${RERANK_CANDIDATE_POOL}
  `;

  const pool = getPool();
  try {
    const result = await pool.query(sql, [embStr, ...params]);
    const candidates = result.rows.map((r) => ({
      chunk_id: r.id,
      doc_id: r.doc_id,
      doc_type: r.doc_type,
      doc_title: r.doc_title,
      full_citation: r.full_citation,
      bab_number: r.bab_number,
      pasal_number: r.pasal_number,
      ayat_number: r.ayat_number,
      text: r.text,
      page_start: r.page_start,
      page_end: r.page_end,
      source_file: r.source_file,
      similarity: Number(r.similarity),
    }));
    const hasKey = !!process.env.DEEPSEEK_API_KEY;
    const debug: RerankDebug | undefined = body.debug ? ({ hadApiKey: hasKey } as RerankDebug) : undefined;
    const data = hasKey ? await rerankChunks(query, candidates, k, debug) : candidates.slice(0, k);
    return NextResponse.json({ data, meta: { query, k, debug } });
  } catch (err) {
    return NextResponse.json(
      { error: { message: `Database query failed: ${(err as Error).message}` } },
      { status: 502 }
    );
  }
}
