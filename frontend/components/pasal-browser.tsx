'use client';

import { useEffect, useState } from 'react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { ResultCard } from '@/components/result-card';
import { fetchDocuments, fetchPasal } from '@/lib/api';
import { comparePasalAyat } from '@/lib/utils';
import type { DocumentSummary, SearchResult } from '@/types';

export function PasalBrowser() {
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);
  const [docId, setDocId] = useState('');
  const [pasalNumber, setPasalNumber] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searched, setSearched] = useState(false);

  useEffect(() => {
    fetchDocuments()
      .then((res) => {
        setDocuments(res.data);
        if (res.data.length > 0) setDocId(res.data[0].doc_id);
      })
      .catch(() => setDocuments([]));
  }, []);

  async function handleLookup(e: React.FormEvent) {
    e.preventDefault();
    if (!docId || !pasalNumber.trim()) return;
    setLoading(true);
    setError(null);
    setSearched(true);
    try {
      const res = await fetchPasal({ docId, pasalNumber: pasalNumber.trim() });
      setResults([...res.data].sort(comparePasalAyat));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Terjadi kesalahan');
      setResults([]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <form onSubmit={handleLookup} className="flex flex-col gap-3 sm:flex-row">
        <select
          value={docId}
          onChange={(e) => setDocId(e.target.value)}
          className="h-10 rounded-md border border-input bg-background px-3 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring sm:w-64"
          aria-label="Pilih dokumen"
        >
          {documents.map((d) => (
            <option key={d.doc_id} value={d.doc_id}>
              {d.title}
            </option>
          ))}
        </select>
        <Input
          value={pasalNumber}
          onChange={(e) => setPasalNumber(e.target.value)}
          placeholder="Nomor pasal, misal: 22"
          className="sm:w-40"
          aria-label="Nomor pasal"
        />
        <Button type="submit" disabled={loading || !docId || !pasalNumber.trim()}>
          {loading ? 'Memuat...' : 'Tampilkan'}
        </Button>
      </form>

      <div className="mt-6 space-y-3">
        {error && (
          <p className="rounded-md border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">
            {error}
          </p>
        )}

        {!error && !loading && searched && results.length === 0 && (
          <p className="text-sm text-muted-foreground">
            Pasal {pasalNumber} tidak ditemukan di dokumen ini.
          </p>
        )}

        {results.map((r) => (
          <ResultCard key={r.chunk_id} result={r} showRelevance={false} />
        ))}
      </div>
    </div>
  );
}
