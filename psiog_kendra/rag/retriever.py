"""Index and retrieve internal documentation.

Indexing is a one-time setup step (`make index`). Retrieval is pure semantic similarity —
the query is embedded and matched against chunk embeddings. There is no keyword fallback
anywhere in this module by design.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from psiog_kendra.config import settings
from psiog_kendra.llm import LLMGateway
from psiog_kendra.rag.chunker import Chunk, chunk_corpus
from psiog_kendra.rag.store import VectorStore


@dataclass(frozen=True)
class Retrieved:
    """One retrieved chunk plus its similarity score."""

    text: str
    citation: str
    source: str
    section: str
    score: float


async def index_corpus(
    store: VectorStore,
    llm: LLMGateway,
    docs_dir: Path | None = None,
) -> list[Chunk]:
    """Chunk, embed and store every document. Returns the chunks written."""
    chunks = chunk_corpus(docs_dir or settings().docs_dir)
    for chunk in chunks:
        embedding = await llm.embed(chunk.text)
        await store.set_vector(chunk.chunk_id, embedding, chunk.metadata())
    return chunks


async def retrieve(
    query: str,
    store: VectorStore,
    llm: LLMGateway,
    *,
    top_k: int | None = None,
    min_score: float | None = None,
) -> list[Retrieved]:
    """Semantic search for the chunks most relevant to `query`."""
    cfg = settings()
    top_k = top_k or cfg.rag_top_k
    threshold = cfg.rag_min_score if min_score is None else min_score

    query_embedding = await llm.embed(query)
    results = await store.similarity_search(query_embedding, top_k=top_k)

    retrieved: list[Retrieved] = []
    for r in results:
        if float(r.get("score", 0.0)) < threshold:
            continue
        meta: dict[str, Any] = r.get("metadata") or {}
        source = meta.get("source", r.get("key", "unknown"))
        section = meta.get("section", "Document")
        retrieved.append(
            Retrieved(
                text=meta.get("text") or r.get("text", ""),
                citation=meta.get("citation") or f"{source} § {section}",
                source=source,
                section=section,
                score=float(r.get("score", 0.0)),
            )
        )
    return retrieved
