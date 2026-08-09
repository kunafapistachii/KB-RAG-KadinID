"""Optional OCR fallback for scanned PDFs. Not run automatically — call
explicitly (e.g. `python ingest.py --file x.pdf --ocr`) when
extraction.pdf_extractor.is_likely_scanned() returns True.

Requires: pytesseract + the Tesseract binary installed on the system.
"""

from dataclasses import dataclass

import fitz  # PyMuPDF
import pytesseract
from PIL import Image
import io

from extraction.pdf_extractor import PageText
from config import TESSERACT_CMD, TESSDATA_DIR, OCR_LANG

if TESSERACT_CMD:
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD


@dataclass
class OCRPageText(PageText):
    confidence_note: str = "ocr"


def extract_pages_ocr(pdf_path: str, dpi: int = 300, lang: str | None = None) -> list[PageText]:
    """Rasterize each page and run Tesseract OCR. Slow — use only for
    confirmed scanned/corrupted-text documents. lang defaults to config.OCR_LANG
    ('ind') and requires the Indonesian Tesseract language pack — see
    config.TESSDATA_DIR if it's not installed in Tesseract's default tessdata dir."""
    lang = lang or OCR_LANG
    tess_config = f"--tessdata-dir {TESSDATA_DIR}" if TESSDATA_DIR else ""

    doc = fitz.open(pdf_path)
    pages = []
    try:
        zoom = dpi / 72
        matrix = fitz.Matrix(zoom, zoom)
        for i, page in enumerate(doc):
            pix = page.get_pixmap(matrix=matrix)
            img = Image.open(io.BytesIO(pix.tobytes("png")))
            text = pytesseract.image_to_string(img, lang=lang, config=tess_config)
            pages.append(PageText(page_number=i + 1, text=text))
    finally:
        doc.close()
    return pages
