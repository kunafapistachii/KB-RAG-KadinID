'use client';

import { useState } from 'react';
import { SearchBar } from '@/components/search-bar';
import { ResultCard } from '@/components/result-card';
import { searchChunks } from '@/lib/api';
import type { SearchResult } from '@/types';

export default function HomePage() {
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastQuery, setLastQuery] = useState('');

  async function handleSearch(query: string, docType: string) {
    setLoading(true);
    setError(null);
    setLastQuery(query);
    try {
      const res = await searchChunks({ query, docType, k: 8 });
      setResults(res.data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Terjadi kesalahan');
      setResults([]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="mx-auto min-h-screen max-w-3xl px-4 py-10">
      <header className="mb-8">
        <h1 className="text-2xl font-bold">AD-ART Knowledge Base</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Cari pasal dan ayat dari AD, ART, UU, Keppres, dan Peraturan Organisasi.
        </p>
      </header>

      <SearchBar onSearch={handleSearch} loading={loading} />

      <div className="mt-6 space-y-3">
        {error && (
          <p className="rounded-md border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">
            {error}
          </p>
        )}

        {!error && !loading && lastQuery && results.length === 0 && (
          <p className="text-sm text-muted-foreground">
            Tidak ada hasil untuk &ldquo;{lastQuery}&rdquo;.
          </p>
        )}

        {results.map((r) => (
          <ResultCard key={r.chunk_id} result={r} />
        ))}
      </div>
    </main>
  );
}
