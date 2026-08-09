"""Turn a parsed BAB/Pasal/Ayat tree into flat chunks ready for embedding."""

import re
from dataclasses import dataclass, field

from config import MAX_CHUNK_CHARS
from parsing.structure_parser import BabNode, OrphanBlock, ParseResult

MIN_TRUSTED_CHARS = 30  # below this, a bare chunk is more likely a fragment than real content
_TRAILING_ELLIPSIS_RE = re.compile(r"\.\s*\.\s*\.?\s*$")
_RESIDUAL_HEADER_RE = re.compile(r"\bPRESIDEN\b|\bREPUBLIK INDONESIA\b", re.IGNORECASE)


def _looks_corrupted(text: str) -> bool:
    """Flag text that looks like it was cut off by page-boundary noise (OCR
    garbage from a stamp/QR code, or a header line that escaped cleaning)
    rather than being genuine short content — seen concretely in this
    project's source PDFs as 'Kadin ...\\n<garbled symbols>\\nPRESIDEN\\n...'."""
    stripped = text.strip()
    if len(stripped) < MIN_TRUSTED_CHARS:
        return True
    if _TRAILING_ELLIPSIS_RE.search(stripped):
        return True
    if _RESIDUAL_HEADER_RE.search(stripped):
        return True
    return False


@dataclass
class Chunk:
    doc_id: str
    doc_type: str
    doc_title: str
    doc_year: int | None
    bab_number: str | None
    bab_title: str | None
    pasal_number: str | None
    pasal_title: str | None
    ayat_number: str | None
    text: str
    full_citation: str
    page_start: int
    page_end: int
    source_file: str
    needs_manual_review: bool = False


def _build_citation(doc_title: str, doc_year: int | None, bab: BabNode | None,
                     pasal_number: str | None, pasal_title: str | None,
                     ayat_number: str | None) -> str:
    parts = [doc_title if not doc_year else f"{doc_title} {doc_year}"]
    if bab is not None and bab.bab_number:
        parts.append(f"BAB {bab.bab_number}")
    if pasal_number:
        parts.append(f"Pasal {pasal_number}" + (f" ({pasal_title})" if pasal_title else ""))
    if ayat_number:
        parts.append(f"Ayat ({ayat_number})")
    return ", ".join([parts[0]] + parts[1:]) if len(parts) > 1 else parts[0]


def build_chunks(
    parse_result: ParseResult,
    doc_id: str,
    doc_type: str,
    doc_title: str,
    doc_year: int | None,
    source_file: str,
) -> list[Chunk]:
    chunks: list[Chunk] = []

    for bab in parse_result.bab_list:
        for pasal in bab.pasal_list:
            if pasal.ayat_list:
                # One chunk per ayat when ayat structure exists.
                for ayat in pasal.ayat_list:
                    if not ayat.text.strip():
                        continue
                    chunks.append(Chunk(
                        doc_id=doc_id, doc_type=doc_type, doc_title=doc_title, doc_year=doc_year,
                        bab_number=bab.bab_number, bab_title=bab.bab_title or None,
                        pasal_number=pasal.pasal_number, pasal_title=pasal.pasal_title,
                        ayat_number=ayat.ayat_number,
                        text=ayat.text,
                        full_citation=_build_citation(doc_title, doc_year, bab, pasal.pasal_number, pasal.pasal_title, ayat.ayat_number),
                        page_start=ayat.page_start, page_end=ayat.page_end,
                        source_file=source_file,
                        needs_manual_review=len(ayat.text) > MAX_CHUNK_CHARS or _looks_corrupted(ayat.text),
                    ))
                # Pasal-level lead-in text (before first ayat), if substantial, gets its own chunk.
                if len(pasal.text.strip()) > 0:
                    chunks.append(Chunk(
                        doc_id=doc_id, doc_type=doc_type, doc_title=doc_title, doc_year=doc_year,
                        bab_number=bab.bab_number, bab_title=bab.bab_title or None,
                        pasal_number=pasal.pasal_number, pasal_title=pasal.pasal_title,
                        ayat_number=None,
                        text=pasal.text.strip(),
                        full_citation=_build_citation(doc_title, doc_year, bab, pasal.pasal_number, pasal.pasal_title, None),
                        page_start=pasal.page_start, page_end=pasal.page_end,
                        source_file=source_file,
                        needs_manual_review=_looks_corrupted(pasal.text),
                    ))
            elif pasal.text.strip():
                # No ayat structure: whole pasal is one chunk, unless too long
                # to safely trust as a single unit.
                chunks.append(Chunk(
                    doc_id=doc_id, doc_type=doc_type, doc_title=doc_title, doc_year=doc_year,
                    bab_number=bab.bab_number, bab_title=bab.bab_title or None,
                    pasal_number=pasal.pasal_number, pasal_title=pasal.pasal_title,
                    ayat_number=None,
                    text=pasal.text.strip(),
                    full_citation=_build_citation(doc_title, doc_year, bab, pasal.pasal_number, pasal.pasal_title, None),
                    page_start=pasal.page_start, page_end=pasal.page_end,
                    source_file=source_file,
                    needs_manual_review=len(pasal.text) > MAX_CHUNK_CHARS or _looks_corrupted(pasal.text),
                ))

    for orphan in parse_result.orphan_blocks:
        if not orphan.text.strip():
            continue
        chunks.append(Chunk(
            doc_id=doc_id, doc_type=doc_type, doc_title=doc_title, doc_year=doc_year,
            bab_number=None, bab_title=None, pasal_number=None, pasal_title=None, ayat_number=None,
            text=orphan.text,
            full_citation=f"{doc_title} {doc_year or ''} (uncategorized)".strip(),
            page_start=orphan.page_start, page_end=orphan.page_end,
            source_file=source_file,
            needs_manual_review=True,
        ))

    _flag_duplicate_ayat(chunks)
    return chunks


def _flag_duplicate_ayat(chunks: list[Chunk]) -> None:
    """If the same (bab, pasal, ayat) key produced more than one chunk —
    seen concretely as a cross-reference like 'ayat (11)' inside body text
    landing at the start of a wrapped line and being misread as a new Ayat
    marker — none of the duplicates can be trusted as THE canonical text for
    that citation, so flag all of them rather than let one look clean."""
    seen: dict[tuple, list[Chunk]] = {}
    for c in chunks:
        if c.ayat_number is None:
            continue
        key = (c.bab_number, c.pasal_number, c.ayat_number)
        seen.setdefault(key, []).append(c)
    for group in seen.values():
        if len(group) > 1:
            for c in group:
                c.needs_manual_review = True
