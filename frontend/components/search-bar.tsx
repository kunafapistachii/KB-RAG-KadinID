'use client';

import { useState, type FormEvent } from 'react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { DOC_TYPE_LABELS } from '@/types';

interface SearchBarProps {
  onSearch: (query: string, docType: string) => void;
  loading: boolean;
}

export function SearchBar({ onSearch, loading }: SearchBarProps) {
  const [query, setQuery] = useState('');
  const [docType, setDocType] = useState('');

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!query.trim()) return;
    onSearch(query.trim(), docType);
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-3 sm:flex-row">
      <Input
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Cari pasal, misal: berapa masa jabatan Ketua Umum?"
        className="flex-1"
        aria-label="Kata kunci pencarian"
      />
      <select
        value={docType}
        onChange={(e) => setDocType(e.target.value)}
        className="h-10 rounded-md border border-input bg-background px-3 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        aria-label="Filter jenis dokumen"
      >
        <option value="">Semua dokumen</option>
        {Object.entries(DOC_TYPE_LABELS).map(([value, label]) => (
          <option key={value} value={value}>
            {label}
          </option>
        ))}
      </select>
      <Button type="submit" disabled={loading || !query.trim()}>
        {loading ? 'Mencari...' : 'Cari'}
      </Button>
    </form>
  );
}
