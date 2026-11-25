from __future__ import annotations

import re
from dataclasses import dataclass

from bs4 import BeautifulSoup


@dataclass
class TextChunk:
    chunk_index: int
    section_heading: str | None
    page_number: int | None
    content: str


def extract_clean_html_text(html: str) -> str:
    """Extract main readable text from HTML while removing nav, scripts, and page chrome."""
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "noscript", "nav", "header", "footer", "aside", "svg"]):
        tag.decompose()

    main = soup.find("main") or soup.find("article") or soup.find(id="main-content") or soup.body or soup
    lines: list[str] = []
    for elem in main.find_all(["h1", "h2", "h3", "h4", "p", "li", "td", "th"]):
        txt = " ".join(elem.get_text(" ", strip=True).split())
        if len(txt) >= 3:
            if elem.name in ("h1", "h2", "h3", "h4"):
                lines.append(f"## {txt}")
            else:
                lines.append(txt)

    if not lines:
        raw = " ".join(main.get_text(" ", strip=True).split())
        return raw

    # Deduplicate consecutive identical lines common in CMS tables/cards
    deduped: list[str] = []
    for line in lines:
        if not deduped or deduped[-1] != line:
            deduped.append(line)
    return "\n".join(deduped)


def _looks_like_heading(line: str) -> str | None:
    stripped = line.strip()
    if stripped.startswith("## "):
        return stripped[3:].strip()[:240]
    if 4 <= len(stripped) <= 90 and not stripped.endswith("."):
        if re.match(r"^(\d+(\.\d+)*\.?\s+)?[A-Z][A-Za-z0-9\s,&/()-]{3,}$", stripped):
            return stripped[:240]
    return None


def chunk_pages(
    pages: list[tuple[int | None, str]],
    max_chars: int = 850,
    overlap_chars: int = 120,
) -> list[TextChunk]:
    """Split extracted document pages into citation-ready passages preserving page numbers."""
    chunks: list[TextChunk] = []
    idx = 0
    current_heading: str | None = None

    for page_num, raw_text in pages:
        if not raw_text or not raw_text.strip():
            continue
        lines = [ln.strip() for ln in raw_text.splitlines() if ln.strip()]
        buffer = ""

        for line in lines:
            heading = _looks_like_heading(line)
            if heading:
                if len(buffer) >= 120:
                    chunks.append(
                        TextChunk(
                            chunk_index=idx,
                            section_heading=current_heading,
                            page_number=page_num,
                            content=buffer.strip(),
                        )
                    )
                    idx += 1
                    buffer = buffer[-overlap_chars:].strip() if overlap_chars > 0 else ""
                current_heading = heading
                if line.startswith("## "):
                    line = heading

            candidate = f"{buffer}\n{line}".strip() if buffer else line
            if len(candidate) <= max_chars:
                buffer = candidate
            else:
                if buffer:
                    chunks.append(
                        TextChunk(
                            chunk_index=idx,
                            section_heading=current_heading,
                            page_number=page_num,
                            content=buffer.strip(),
                        )
                    )
                    idx += 1
                tail = buffer[-overlap_chars:].strip() if overlap_chars > 0 and buffer else ""
                # Handle single oversized line safely
                if len(line) > max_chars:
                    for start in range(0, len(line), max_chars - overlap_chars):
                        piece = line[start : start + max_chars].strip()
                        if piece:
                            chunks.append(
                                TextChunk(
                                    chunk_index=idx,
                                    section_heading=current_heading,
                                    page_number=page_num,
                                    content=piece,
                                )
                            )
                            idx += 1
                    buffer = ""
                else:
                    buffer = f"{tail}\n{line}".strip() if tail else line

        if buffer.strip():
            chunks.append(
                TextChunk(
                    chunk_index=idx,
                    section_heading=current_heading,
                    page_number=page_num,
                    content=buffer.strip(),
                )
            )
            idx += 1

    return chunks
