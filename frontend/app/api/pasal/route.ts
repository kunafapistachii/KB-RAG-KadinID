import { NextRequest, NextResponse } from 'next/server';
import { getPool } from '@/lib/db';

export const runtime = 'nodejs';

interface PasalBody {
  doc_id?: string;
  pasal_number?: string;
}

// Direct lookup, not semantic search — no embedding call, no rerank. Used
// by the "browse by pasal" view where the user already knows exactly which
// pasal they want and just needs every ayat under it, in document order.
export async function POST(req: NextRequest) {
  let body: PasalBody;
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: { message: 'Invalid JSON body' } }, { status: 400 });
  }

  const docId = (body.doc_id || '').trim();
  const pasalNumber = (body.pasal_number || '').trim();
  if (!docId || !pasalNumber) {
    return NextResponse.json(
      { error: { message: "'doc_id' and 'pasal_number' are required" } },
      { status: 400 }
    );
  }

  const sql = `
    SELECT id, doc_id, doc_type, doc_title, full_citation,
           bab_number, pasal_number, pasal_title, ayat_number, text,
           page_start, page_end, source_file,
           1 AS similarity
    FROM chunks
    WHERE doc_id = $1 AND pasal_number = $2 AND needs_manual_review = FALSE
    ORDER BY id ASC
  `;

  const pool = getPool();
  try {
    const result = await pool.query(sql, [docId, pasalNumber]);
    const data = result.rows.map((r) => ({
      chunk_id: r.id,
      doc_id: r.doc_id,
      doc_type: r.doc_type,
      doc_title: r.doc_title,
      full_citation: r.full_citation,
      bab_number: r.bab_number,
      pasal_number: r.pasal_number,
      pasal_title: r.pasal_title,
      ayat_number: r.ayat_number,
      text: r.text,
      page_start: r.page_start,
      page_end: r.page_end,
      source_file: r.source_file,
      similarity: Number(r.similarity),
    }));
    return NextResponse.json({ data, meta: { doc_id: docId, pasal_number: pasalNumber } });
  } catch (err) {
    return NextResponse.json(
      { error: { message: `Database query failed: ${(err as Error).message}` } },
      { status: 502 }
    );
  }
}
