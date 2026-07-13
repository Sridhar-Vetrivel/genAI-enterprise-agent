"""Split internal docs into citable chunks.

Chunks are cut on markdown section boundaries so that every chunk carries the heading
it came from. The citation the user finally sees is "<document> § <section>", which is
only possible if the section survives chunking.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from psiog_kendra.config import settings

_HEADING = re.compile(r"^(#{1,6})\s+(.*)$", re.MULTILINE)


@dataclass(frozen=True)
class Chunk:
    """One indexable, citable slice of a document."""

    chunk_id: str
    text: str
    source: str
    section: str
    url: str

    @property
    def citation(self) -> str:
        return f"{self.source} § {self.section}"

    def metadata(self) -> dict[str, str]:
        return {
            "source": self.source,
            "section": self.section,
            "url": self.url,
            "citation": self.citation,
            "text": self.text,
        }


def _split_long(text: str, size: int, overlap: int) -> list[str]:
    """Window an oversized section, keeping an overlap so sentences aren't orphaned.

    Blank input yields no windows — an empty chunk would be an un-citable orphan.
    """
    if not text.strip():
        return []
    if len(text) <= size:
        return [text]
    step = max(1, size - overlap)
    windows = [text[i : i + size] for i in range(0, len(text), step)]
    return [w for w in windows if w.strip()]


def chunk_markdown(text: str, *, source: str, url: str | None = None) -> list[Chunk]:
    """Chunk one markdown document by section, then by size within a section."""
    cfg = settings()
    url = url or f"data/docs/{source}"

    matches = list(_HEADING.finditer(text))
    sections: list[tuple[str, str]] = []
    if not matches:
        sections.append(("Document", text))
    else:
        preamble = text[: matches[0].start()].strip()
        if preamble:
            sections.append(("Preamble", preamble))
        for i, m in enumerate(matches):
            title = m.group(2).strip()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            body = text[m.end() : end].strip()
            if body:
                sections.append((title, body))

    chunks: list[Chunk] = []
    for title, body in sections:
        for n, piece in enumerate(_split_long(body, cfg.rag_chunk_chars, cfg.rag_chunk_overlap)):
            slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-") or "section"
            chunks.append(
                Chunk(
                    chunk_id=f"{source}::{slug}::{n}",
                    # Prepend the heading so the embedding carries the section's topic.
                    text=f"{title}\n\n{piece.strip()}",
                    source=source,
                    section=title,
                    url=url,
                )
            )
    return chunks


def chunk_corpus(docs_dir: Path) -> list[Chunk]:
    """Chunk every markdown file in the corpus directory."""
    if not docs_dir.exists():
        return []
    chunks: list[Chunk] = []
    for path in sorted(docs_dir.glob("*.md")):
        chunks.extend(chunk_markdown(path.read_text(), source=path.name))
    return chunks
