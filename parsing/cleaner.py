"""Cleaning of raw extracted PDF text: repeated header/footer removal,
hyphenation-artifact fixing, whitespace normalization."""

import re
from collections import Counter
from dataclasses import dataclass, field

from extraction.pdf_extractor import PageText
from parsing.structure_parser import BAB_RE, PASAL_RE, AYAT_RE, HURUF_RE

EDGE_LINES_CHECKED = 6          # look at first/last N non-blank lines per page for boilerplate
                                 # (wider than a typical 2-3 line header/footer to tolerate stray
                                 # OCR noise lines from page-bottom stamps/QR codes pushing the
                                 # real header further from the physical page edge)
BOILERPLATE_THRESHOLD = 0.8     # must occur on >=80% of pages to be considered header/footer


def _is_structural_line(line: str) -> bool:
    """True if line looks like a BAB/Pasal/Ayat/huruf marker — never treat
    these as boilerplate, even if digit-normalization makes two different
    pasal numbers collide (e.g. 'Pasal 1' and 'Pasal 4' both -> 'Pasal #')."""
    line = line.strip()
    return bool(BAB_RE.match(line) or PASAL_RE.match(line) or AYAT_RE.match(line) or HURUF_RE.match(line))


def _normalize_line_for_matching(line: str) -> str:
    """Strip digits and ALL whitespace so page-number-only differences (e.g.
    'Halaman 12' vs 'Halaman 13') and inconsistent OCR spacing (e.g. '-19-'
    vs '- 24 -') still collapse to the same boilerplate key."""
    line = line.strip()
    line = re.sub(r"\d+", "#", line)
    line = re.sub(r"\s+", "", line)
    return line


@dataclass
class CleaningReport:
    detected_boilerplate: list[str] = field(default_factory=list)
    pages_cleaned: int = 0


def detect_boilerplate_lines(pages: list[PageText]) -> set[str]:
    """Find lines (normalized) that repeat on >=80% of pages near the top or
    bottom — these are page headers/footers to strip."""
    if not pages:
        return set()

    counter: Counter[str] = Counter()
    for p in pages:
        lines = [l for l in p.text.split("\n") if l.strip()]
        edge_lines = lines[:EDGE_LINES_CHECKED] + lines[-EDGE_LINES_CHECKED:]
        seen_this_page = {
            _normalize_line_for_matching(l) for l in edge_lines
            if l.strip() and not _is_structural_line(l)
        }
        for norm in seen_this_page:
            counter[norm] += 1

    n_pages = len(pages)
    boilerplate = {
        norm for norm, count in counter.items()
        if norm and count / n_pages >= BOILERPLATE_THRESHOLD
    }
    return boilerplate


def _fix_hyphenation(text: str) -> str:
    """Merge words split by a trailing hyphen at line end, e.g.
    'organi-\\nsasi' -> 'organisasi'."""
    return re.sub(r"(\w)-\n(\w)", r"\1\2", text)


def _normalize_whitespace(text: str) -> str:
    lines = [re.sub(r"[ \t]+", " ", l).strip() for l in text.split("\n")]
    text = "\n".join(lines)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def clean_pages(pages: list[PageText]) -> tuple[list[PageText], CleaningReport]:
    boilerplate = detect_boilerplate_lines(pages)
    report = CleaningReport(detected_boilerplate=sorted(boilerplate))

    cleaned_pages = []
    for p in pages:
        lines = p.text.split("\n")
        # Edge membership must be computed on non-blank line positions — same
        # basis detect_boilerplate_lines used — otherwise leading/trailing
        # blank lines (common OCR artifact) shift raw indices out of the
        # detected edge window and header/footer lines silently stop matching.
        non_blank_idx = [i for i, l in enumerate(lines) if l.strip()]
        edge_positions = set(non_blank_idx[:EDGE_LINES_CHECKED]) | set(non_blank_idx[-EDGE_LINES_CHECKED:])
        kept_lines = []
        for idx, line in enumerate(lines):
            is_edge = idx in edge_positions
            if (is_edge and not _is_structural_line(line)
                    and _normalize_line_for_matching(line) in boilerplate):
                continue
            kept_lines.append(line)
        text = "\n".join(kept_lines)
        text = _fix_hyphenation(text)
        text = _normalize_whitespace(text)
        cleaned_pages.append(PageText(page_number=p.page_number, text=text))
        report.pages_cleaned += 1

    return cleaned_pages, report
