<role>
Kamu adalah senior backend engineer yang membangun data ingestion pipeline untuk sistem RAG (Retrieval-Augmented Generation) berbasis dokumen legal Indonesia.
</role>

<context>
Saya sedang membangun aplikasi web (nama sementara: AD-ART Knowledge Base) yang menyimpan dokumen legal organisasi (AD, ART, UU, Keppres, Peraturan Organisasi) sebagai knowledge base untuk AI Q&A.

Dokumen yang akan diproses:
- UU 1 Tahun 1987
- Keppres 18 Tahun 2022
- Anggaran Dasar (AD)
- Anggaran Rumah Tangga (ART)
- Peraturan Organisasi (PO) — 439 halaman, dokumen paling kompleks

Karakteristik dokumen:
- Format: PDF, sebagian besar teks asli (bukan hasil scan) — TAPI perlu diverifikasi per file
- Struktur konsisten: BAB > Pasal > Ayat > (opsional) huruf a/b/c
- Kemungkinan ada page header/footer berulang yang perlu dibersihkan
- Kemungkinan ada lampiran di PO yang formatnya beda (tabel/form, bukan pasal biasa)

Scope tahap ini: HANYA pipeline parsing + ingestion. Belum ada UI, belum ada fitur chat/Q&A. Frontend Next.js menyusul di tahap berikutnya, jangan dikerjakan dulu.
</context>

<task>
Bangun pipeline Python yang:

1. **Extraction**: Baca PDF, extract teks + informasi halaman menggunakan PyMuPDF (fitz). Sediakan fallback OCR (pytesseract) untuk kasus dokumen hasil scan — tapi buat ini opsional/terpisah, jangan dijalankan otomatis untuk semua dokumen.

2. **Cleaning**: Bersihkan hasil extraction dari:
   - Header/footer yang berulang di setiap halaman (deteksi otomatis pola yang muncul di >80% halaman)
   - Artifact hyphenation (kata terpotong di akhir baris)
   - Normalisasi whitespace

3. **Structure detection**: Parse teks menjadi hierarki terstruktur menggunakan regex, dengan pola:
   - `BAB [angka romawi]` sebagai level teratas
   - `Pasal [angka]` sebagai level kedua
   - `(angka)` sebagai Ayat, level ketiga (opsional, tidak semua pasal punya ayat)
   - `[huruf].` sebagai sub-item ayat (opsional)

   Buat parser fleksibel karena format bisa sedikit beda antar jenis dokumen (UU vs Keppres vs AD/ART vs PO). Sertakan validasi coverage: laporkan berapa persen teks yang berhasil ter-assign ke struktur vs yang tidak (uncategorized/orphan text), supaya saya bisa tau kalau ada pola yang belum ke-cover.

4. **Chunking**: Setiap unit (biasanya per Pasal, atau per Ayat jika Pasal terlalu panjang >1500 karakter) jadi satu chunk, dengan metadata:
   - doc_id, doc_type (uu/keppres/ad/art/peraturan_organisasi), doc_title, doc_year
   - bab_number, bab_title
   - pasal_number
   - ayat_number (nullable)
   - text (isi chunk)
   - full_citation (string siap pakai, misal: "Peraturan Organisasi 2024, BAB III Pasal 12 Ayat (2)")
   - page_start, page_end
   - source_file

5. **Embedding**: Generate embedding untuk setiap chunk menggunakan OpenAI `text-embedding-3-small`. Implementasikan batching yang efisien (jangan panggil API satu-satu per chunk), gunakan Batch API jika greenfield mendukung untuk indexing awal (biar dapat diskon 50%).

6. **Storage**: Simpan ke PostgreSQL dengan ekstensi pgvector. Buat dua tabel:
   - `documents`: metadata dokumen (id, title, type, year, source_filename, upload_date, version)
   - `chunks`: isi chunk + vector embedding + foreign key ke documents + semua metadata di poin 4

   Sertakan index yang tepat: index vector (ivfflat/hnsw) untuk similarity search, plus index biasa untuk filter by doc_type/pasal_number.

7. **CLI/script untuk re-ingestion**: Buat script yang bisa dijalankan ulang kalau ada dokumen baru/update — harus bisa hapus chunk lama untuk doc_id tertentu lalu insert ulang, tanpa perlu re-proses semua dokumen dari awal.

8. **Validasi**: Sertakan test/script sederhana untuk sample random chunk dan bandingkan manual dengan PDF asli — supaya saya bisa QA hasil parsing sebelum lanjut ke fase berikutnya.
</task>

<tech_stack>
- Python 3.11+
- PyMuPDF (fitz) untuk PDF extraction
- pytesseract sebagai opsi OCR (tidak wajib dipakai default)
- OpenAI Python SDK untuk embedding (text-embedding-3-small)
- PostgreSQL + pgvector
- psycopg2 atau SQLAlchemy untuk koneksi DB
- python-dotenv untuk config (API key, DB credentials)
</tech_stack>

<deliverables>
1. Struktur folder project yang jelas (misal: `extraction/`, `parsing/`, `embedding/`, `storage/`, `scripts/`)
2. Script `ingest.py` sebagai entry point utama: `python ingest.py --file path/to/doc.pdf --doc-type peraturan_organisasi --doc-title "..." --doc-year 2024`
3. Script `reingest.py` untuk update dokumen yang sudah ada
4. Schema SQL untuk setup database (`schema.sql`)
5. README singkat: cara setup environment, cara jalanin, cara baca hasil validasi coverage
6. Mulai development dan testing dengan 1 dokumen PENDEK dulu (AD atau ART), baru generalisasi ke dokumen lain. JANGAN langsung coba parse PO yang 439 halaman di awal.
</deliverables>

<constraints>
- Jangan build UI/frontend apapun di tahap ini
- Jangan hardcode API key — pakai environment variable
- Prioritaskan correctness struktur parsing di atas kecepatan development — dokumen ini legal reference, salah asosiasi pasal itu fatal
- Untuk dokumen yang parsingnya gagal/ambigu, JANGAN dipaksakan — tandai sebagai "needs_manual_review" daripada menghasilkan struktur yang salah
</constraints>
