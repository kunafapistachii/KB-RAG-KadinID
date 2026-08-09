export interface SearchResult {
  chunk_id: number;
  doc_id: string;
  doc_type: string;
  doc_title: string;
  full_citation: string;
  bab_number: string | null;
  pasal_number: string | null;
  ayat_number: string | null;
  text: string;
  page_start: number;
  page_end: number;
  source_file: string;
  similarity: number;
}

export interface SearchResponse {
  data: SearchResult[];
  meta: { query: string; k: number };
}

export interface DocumentSummary {
  doc_id: string;
  title: string;
  doc_type: string;
  doc_year: number | null;
  version: number;
  upload_date: string | null;
  chunk_count: number;
}

export const DOC_TYPE_LABELS: Record<string, string> = {
  uu: 'Undang-Undang',
  keppres: 'Keputusan Presiden',
  ad: 'Anggaran Dasar',
  art: 'Anggaran Rumah Tangga',
  peraturan_organisasi: 'Peraturan Organisasi',
};
