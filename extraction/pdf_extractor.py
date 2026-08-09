"""PDF text extraction using PyMuPDF (fitz)."""

from dataclasses import dataclass

import fitz  # PyMuPDF


@dataclass
class PageText:
    page_number: int  # 1-indexed
    text: str


def extract_pages(pdf_path: str) -> list[PageText]:
    """Extract text per page from a PDF. Returns raw, uncleaned text."""
    doc = fitz.open(pdf_path)
    pages = []
    try:
        for i, page in enumerate(doc):
            text = page.get_text("text")
            pages.append(PageText(page_number=i + 1, text=text))
    finally:
        doc.close()
    return pages


def is_likely_scanned(pdf_path: str, sample_pages: int = 5, char_threshold: int = 20) -> bool:
    """Heuristic: if sampled pages have near-zero extractable text, the PDF is
    probably a scan and needs OCR (see extraction/ocr_fallback.py)."""
    doc = fitz.open(pdf_path)
    try:
        n = min(sample_pages, doc.page_count)
        if n == 0:
            return False
        low_text_pages = 0
        for i in range(n):
            text = doc[i].get_text("text").strip()
            if len(text) < char_threshold:
                low_text_pages += 1
        return low_text_pages / n >= 0.8
    finally:
        doc.close()
