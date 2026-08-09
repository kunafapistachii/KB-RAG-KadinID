"""Parse cleaned page text into a BAB > Pasal > Ayat hierarchy using regex.

Flexible on purpose: document types (UU, Keppres, AD/ART, PO) vary slightly.
Anything that can't be confidently assigned goes into `orphan_blocks` instead
of being forced into the wrong place — legal citation accuracy matters more
than 100% structural coverage.
"""

import re
from dataclasses import dataclass, field

from extraction.pdf_extractor import PageText

BAB_RE = re.compile(r"^BAB\s+([IVXLCDM]+[A-Z]?)\b\s*(.*)$", re.IGNORECASE)
PASAL_RE = re.compile(r"^Pasal\s+(\d+[A-Za-z]?)\s*$", re.IGNORECASE)
AYAT_RE = re.compile(r"^\((\d+[a-zA-Z]?)\)\s*(.*)$")
HURUF_RE = re.compile(r"^([a-z])\.\s+(.*)$")

MAX_TITLE_LOOKAHEAD_CHARS = 120


@dataclass
class AyatNode:
    ayat_number: str
    text: str = ""
    page_start: int = 0
    page_end: int = 0


@dataclass
class PasalNode:
    pasal_number: str
    text: str = ""
    ayat_list: list[AyatNode] = field(default_factory=list)
    page_start: int = 0
    page_end: int = 0


@dataclass
class BabNode:
    bab_number: str | None
    bab_title: str
    pasal_list: list[PasalNode] = field(default_factory=list)
    page_start: int = 0
    page_end: int = 0


@dataclass
class OrphanBlock:
    text: str
    page_start: int
    page_end: int


@dataclass
class ParseResult:
    bab_list: list[BabNode]
    orphan_blocks: list[OrphanBlock]
    coverage_percent: float
    total_chars: int
    assigned_chars: int


def _flatten_lines(pages: list[PageText]) -> list[tuple[int, str]]:
    lines = []
    for p in pages:
        for line in p.text.split("\n"):
            lines.append((p.page_number, line))
    return lines


def _find_noise_marker_indices(lines: list[tuple[int, str]]) -> set[int]:
    """Detect bursts of bare '(N)' markers with no body text — seen
    concretely as OCR noise like '(1)\\n(2)\\n(3)\\n(4)\\n(1)\\n(2)' at a page
    top (residual scan artifacts), which AYAT_RE would otherwise happily
    match as real Ayat boundaries. A genuine ayat marker always has
    substantial text on the same line or the ones right after it; a bare
    marker immediately followed by another bare marker (or the numbering
    resetting/repeating) never occurs in real legal text — flag the whole
    burst as noise to skip entirely."""
    non_blank = [(i, l.strip()) for i, (_, l) in enumerate(lines) if l.strip()]

    bare_positions = []  # (position in non_blank, original index, ayat number)
    for pos, (idx, text) in enumerate(non_blank):
        m = AYAT_RE.match(text)
        if m and not m.group(2).strip():
            bare_positions.append((pos, idx, m.group(1)))

    noise_indices: set[int] = set()
    i = 0
    while i < len(bare_positions):
        j = i
        run = [bare_positions[i]]
        while j + 1 < len(bare_positions) and bare_positions[j + 1][0] == bare_positions[j][0] + 1:
            j += 1
            run.append(bare_positions[j])
        if len(run) >= 2:
            noise_indices.update(orig_idx for _, orig_idx, _ in run)
        i = j + 1
    return noise_indices


def parse_structure(pages: list[PageText]) -> ParseResult:
    lines = _flatten_lines(pages)
    noise_indices = _find_noise_marker_indices(lines)

    bab_list: list[BabNode] = []
    orphan_blocks: list[OrphanBlock] = []

    current_bab: BabNode | None = None
    current_pasal: PasalNode | None = None
    current_ayat: AyatNode | None = None
    orphan_buffer: list[tuple[int, str]] = []

    total_chars = 0
    assigned_chars = 0

    def flush_orphan():
        nonlocal orphan_buffer
        text = "\n".join(t for _, t in orphan_buffer).strip()
        if text:
            pages_seen = [pg for pg, _ in orphan_buffer]
            orphan_blocks.append(OrphanBlock(text=text, page_start=pages_seen[0], page_end=pages_seen[-1]))
        orphan_buffer = []

    def flush_ayat():
        nonlocal current_ayat
        if current_ayat is not None and current_pasal is not None:
            current_ayat.text = current_ayat.text.strip()
            current_pasal.ayat_list.append(current_ayat)
        current_ayat = None

    def flush_pasal():
        nonlocal current_pasal
        flush_ayat()
        if current_pasal is not None and current_bab is not None:
            current_pasal.text = current_pasal.text.strip()
            current_bab.pasal_list.append(current_pasal)
        current_pasal = None

    def flush_bab():
        nonlocal current_bab
        flush_pasal()
        if current_bab is not None:
            bab_list.append(current_bab)
        current_bab = None

    i = 0
    n = len(lines)
    while i < n:
        page_num, raw_line = lines[i]
        line = raw_line.strip()
        total_chars += len(line)

        if not line:
            i += 1
            continue

        if i in noise_indices:
            i += 1
            continue

        bab_match = BAB_RE.match(line)
        pasal_match = PASAL_RE.match(line)
        ayat_match = AYAT_RE.match(line)
        huruf_match = HURUF_RE.match(line)

        if bab_match:
            flush_orphan()
            flush_bab()
            bab_number = bab_match.group(1)
            title = bab_match.group(2).strip()
            # title often sits on the next non-empty line instead of inline
            if not title and i + 1 < n:
                next_page, next_raw = lines[i + 1]
                next_line = next_raw.strip()
                if (
                    next_line
                    and len(next_line) <= MAX_TITLE_LOOKAHEAD_CHARS
                    and not BAB_RE.match(next_line)
                    and not PASAL_RE.match(next_line)
                ):
                    title = next_line
                    i += 1
            current_bab = BabNode(bab_number=bab_number, bab_title=title, page_start=page_num, page_end=page_num)
            assigned_chars += len(line)
            i += 1
            continue

        if pasal_match:
            flush_orphan()
            flush_pasal()
            if current_bab is None:
                # Pasal appears before any BAB heading — create an implicit
                # bab-less container rather than dropping the pasal.
                current_bab = BabNode(bab_number=None, bab_title="", page_start=page_num, page_end=page_num)
            pasal_number = pasal_match.group(1)
            current_pasal = PasalNode(pasal_number=pasal_number, page_start=page_num, page_end=page_num)
            current_bab.page_end = page_num
            assigned_chars += len(line)
            i += 1
            continue

        if ayat_match and current_pasal is not None:
            flush_ayat()
            ayat_number = ayat_match.group(1)
            remainder = ayat_match.group(2)
            current_ayat = AyatNode(ayat_number=ayat_number, text=remainder, page_start=page_num, page_end=page_num)
            current_pasal.page_end = page_num
            assigned_chars += len(line)
            i += 1
            continue

        if huruf_match and current_pasal is not None:
            letter, remainder = huruf_match.group(1), huruf_match.group(2)
            item_text = f"{letter}. {remainder}"
            if current_ayat is not None:
                current_ayat.text += "\n" + item_text
                current_ayat.page_end = page_num
            else:
                current_pasal.text += "\n" + item_text
            current_pasal.page_end = page_num
            assigned_chars += len(line)
            i += 1
            continue

        # Plain continuation line
        if current_ayat is not None:
            current_ayat.text += "\n" + line
            current_ayat.page_end = page_num
            current_pasal.page_end = page_num
            assigned_chars += len(line)
        elif current_pasal is not None:
            current_pasal.text += "\n" + line
            current_pasal.page_end = page_num
            assigned_chars += len(line)
        else:
            orphan_buffer.append((page_num, line))

        if current_bab is not None:
            current_bab.page_end = page_num

        i += 1

    flush_orphan()
    flush_bab()

    coverage_percent = (assigned_chars / total_chars * 100) if total_chars else 0.0

    return ParseResult(
        bab_list=bab_list,
        orphan_blocks=orphan_blocks,
        coverage_percent=round(coverage_percent, 2),
        total_chars=total_chars,
        assigned_chars=assigned_chars,
    )
