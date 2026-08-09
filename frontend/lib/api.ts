import type { DocumentSummary, SearchResponse } from '@/types';

// Same-origin: /api/search and /api/documents are Next.js route handlers
// (see app/api/*), not a separate service.

export async function searchChunks(params: {
  query: string;
  k?: number;
  docType?: string;
  pasalNumber?: string;
}): Promise<SearchResponse> {
  const res = await fetch(`/api/search`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      query: params.query,
      k: params.k ?? 5,
      doc_type: params.docType || undefined,
      pasal_number: params.pasalNumber || undefined,
    }),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body?.error?.message || `Search failed (${res.status})`);
  }
  return res.json();
}

export async function fetchDocuments(): Promise<{ data: DocumentSummary[] }> {
  const res = await fetch(`/api/documents`);
  if (!res.ok) throw new Error(`Failed to load documents (${res.status})`);
  return res.json();
}

export async function fetchPasal(params: {
  docId: string;
  pasalNumber: string;
}): Promise<SearchResponse> {
  const res = await fetch(`/api/pasal`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ doc_id: params.docId, pasal_number: params.pasalNumber }),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body?.error?.message || `Lookup failed (${res.status})`);
  }
  return res.json();
}
