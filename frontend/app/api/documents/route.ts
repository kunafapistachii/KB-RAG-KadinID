import { NextResponse } from 'next/server';
import { getPool } from '@/lib/db';

export const runtime = 'nodejs';

export async function GET() {
  const pool = getPool();
  try {
    const result = await pool.query(`
      SELECT d.doc_id, d.title, d.doc_type, d.doc_year, d.version, d.upload_date,
             (SELECT count(*) FROM chunks c WHERE c.doc_id = d.doc_id) AS chunk_count
      FROM documents d ORDER BY d.doc_id
    `);
    const data = result.rows.map((r) => ({
      doc_id: r.doc_id,
      title: r.title,
      doc_type: r.doc_type,
      doc_year: r.doc_year,
      version: r.version,
      upload_date: r.upload_date ? r.upload_date.toISOString() : null,
      chunk_count: Number(r.chunk_count),
    }));
    return NextResponse.json({ data });
  } catch (err) {
    return NextResponse.json(
      { error: { message: `Database query failed: ${(err as Error).message}` } },
      { status: 502 }
    );
  }
}
