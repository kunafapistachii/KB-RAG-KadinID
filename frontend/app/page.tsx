'use client';

import { useMemo, useState } from 'react';
import { SearchBar } from '@/components/search-bar';
import { ResultCard } from '@/components/result-card';
import { PasalBrowser } from '@/components/pasal-browser';
import { searchChunks } from '@/lib/api';
import { cn, comparePasalAyat } from '@/lib/utils';
import type { SearchResult } from '@/types';

type Tab = 'search' | 'browse';
type SortMode = 'relevance' | 'pasal';

export default function HomePage() {
  const [tab, setTab] = useState<Tab>('search');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastQuery, setLastQuery] = useState('');
  const [sortMode, setSortMode] = useState<SortMode>('relevance');

  async function handleSearch(query: string, docType: string) {
    setLoading(true);
    setError(null);
    setLastQuery(query);
    try {
      const res = await searchChunks({ query, docType, k: 8 });
      setResults(res.data);
      setSortMode('relevance');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Terjadi kesalahan');
      setResults([]);
    } finally {
      setLoading(false);
    }
  }

  const sortedResults = useMemo(() => {
    if (sortMode === 'relevance') return results;
    return [...results].sort(comparePasalAyat);
  }, [results, sortMode]);

  return (
    <main className="mx-auto min-h-screen max-w-3xl px-4 py-10">
      <header className="mb-8">
        <h1 className="text-2xl font-bold">AD-ART Knowledge Base</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Cari pasal dan ayat dari AD, ART, UU, Keppres, dan Peraturan Organisasi.
        </p>
      </header>

      <div className="mb-6 flex gap-1 border-b border-border" role="tablist">
        <button
          type="button"
          role="tab"
          aria-selected={tab === 'search'}
          onClick={() => setTab('search')}
          className={cn(
            'border-b-2 px-3 py-2 text-sm font-medium',
            tab === 'search'
              ? 'border-primary text-foreground'
              : 'border-transparent text-muted-foreground hover:text-foreground'
          )}
        >
          Pencarian
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={tab === 'browse'}
          onClick={() => setTab('browse')}
          className={cn(
            'border-b-2 px-3 py-2 text-sm font-medium',
            tab === 'browse'
              ? 'border-primary text-foreground'
              : 'border-transparent text-muted-foreground hover:text-foreground'
          )}
        >
          Jelajahi per Pasal
        </button>
      </div>

      {tab === 'search' ? (
        <>
          <SearchBar onSearch={handleSearch} loading={loading} />

          {results.length > 0 && (
            <div className="mt-4 flex items-center gap-2 text-sm">
              <span className="text-muted-foreground">Urutkan:</span>
              <button
                type="button"
                onClick={() => setSortMode('relevance')}
                className={cn(
                  'rounded-full px-3 py-1',
                  sortMode === 'relevance'
                    ? 'bg-secondary font-medium text-secondary-foreground'
                    : 'text-muted-foreground hover:text-foreground'
                )}
              >
                Relevansi
              </button>
              <button
                type="button"
                onClick={() => setSortMode('pasal')}
                className={cn(
                  'rounded-full px-3 py-1',
                  sortMode === 'pasal'
                    ? 'bg-secondary font-medium text-secondary-foreground'
                    : 'text-muted-foreground hover:text-foreground'
                )}
              >
                Nomor Pasal
              </button>
            </div>
          )}

          <div className="mt-4 space-y-3">
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

            {sortedResults.map((r) => (
              <ResultCard key={r.chunk_id} result={r} />
            ))}
          </div>
        </>
      ) : (
        <PasalBrowser />
      )}
    </main>
  );
}
