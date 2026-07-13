"""One-time RAG indexing: chunk -> embed -> store.

    make index

Also runs the Week 7 data-validation gate: every chunk must carry the metadata a
citation needs, and no chunk may be an orphan.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from psiog_kendra.config import settings
from psiog_kendra.llm import LLMGateway, OllamaGateway
from psiog_kendra.rag.retriever import index_corpus
from psiog_kendra.rag.store import LocalVectorStore


async def build_index(
    llm: LLMGateway | None = None,
    index_path: Path | None = None,
    docs_dir: Path | None = None,
) -> tuple[int, list[str]]:
    """Index the corpus. Returns (chunks written, orphan chunk ids)."""
    cfg = settings()
    store = LocalVectorStore(index_path or cfg.index_path)
    llm = llm or OllamaGateway()

    chunks = await index_corpus(store, llm, docs_dir or cfg.docs_dir)
    store.save()
    return len(chunks), store.orphans()


def main() -> None:
    cfg = settings()
    count, orphans = asyncio.run(build_index())

    print(f"indexed {count} chunks from {cfg.docs_dir}")
    print(f"index written to {cfg.index_path}")
    if orphans:
        print(f"FAILED data-validation gate: {len(orphans)} orphan chunk(s): {orphans[:5]}")
        raise SystemExit(1)
    print("data-validation gate passed: no orphan chunks, all metadata present")


if __name__ == "__main__":
    main()
