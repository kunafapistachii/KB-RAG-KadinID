import { Card } from '@/components/ui/card';
import { DOC_TYPE_LABELS, type SearchResult } from '@/types';

export function ResultCard({ result }: { result: SearchResult }) {
  const flagged = result.similarity < 0.5;

  return (
    <Card className="p-4">
      <div className="mb-2 flex flex-wrap items-center gap-2 text-xs">
        <span className="rounded bg-secondary px-2 py-0.5 font-medium text-secondary-foreground">
          {DOC_TYPE_LABELS[result.doc_type] ?? result.doc_type}
        </span>
        <span className="text-muted-foreground">
          hal. {result.page_start === result.page_end
            ? result.page_start
            : `${result.page_start}-${result.page_end}`}
        </span>
        <span className="ml-auto text-muted-foreground" title="Kemiripan semantik terhadap query">
          {(result.similarity * 100).toFixed(0)}% relevan
        </span>
      </div>
      <p className="mb-2 font-semibold">{result.full_citation}</p>
      <p className="whitespace-pre-line text-sm text-foreground/90">{result.text}</p>
      {flagged && (
        <p className="mt-2 text-xs text-amber-600">
          Kemiripan rendah — verifikasi manual ke dokumen asli sebelum dipakai sebagai rujukan pasti.
        </p>
      )}
    </Card>
  );
}
