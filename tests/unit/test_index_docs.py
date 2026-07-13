"""The one-time indexing entrypoint and its Week 7 data-validation gate."""

from __future__ import annotations

from pathlib import Path

import pytest

from psiog_kendra.config import settings
from psiog_kendra.index_docs import build_index
from psiog_kendra.rag.store import LocalVectorStore
from tests.conftest import FakeLLM


class TestBuildIndex:
    async def test_writes_every_chunk_and_persists_it(
        self, fake_llm: FakeLLM, tmp_path: Path
    ) -> None:
        index = tmp_path / "vectors.json"
        count, orphans = await build_index(llm=fake_llm, index_path=index)

        assert count > 0
        assert orphans == []
        assert index.exists()
        # The index must survive a reload — the docs agent reads it from disk.
        assert len(LocalVectorStore(index)) == count

    async def test_gate_passes_on_the_real_corpus(self, fake_llm: FakeLLM, tmp_path: Path) -> None:
        _, orphans = await build_index(
            llm=fake_llm, index_path=tmp_path / "v.json", docs_dir=settings().docs_dir
        )
        assert orphans == []

    async def test_indexed_chunks_are_citable(self, fake_llm: FakeLLM, tmp_path: Path) -> None:
        index = tmp_path / "v.json"
        await build_index(llm=fake_llm, index_path=index)

        store = LocalVectorStore(index)
        hits = await store.similarity_search(await fake_llm.embed("schema mismatch"), top_k=1)
        assert hits[0]["metadata"]["citation"]
        assert "§" in hits[0]["metadata"]["citation"]

    async def test_empty_corpus_indexes_nothing(self, fake_llm: FakeLLM, tmp_path: Path) -> None:
        empty = tmp_path / "no_docs"
        empty.mkdir()
        count, orphans = await build_index(
            llm=fake_llm, index_path=tmp_path / "v.json", docs_dir=empty
        )
        assert count == 0 and orphans == []

    async def test_gate_fails_when_metadata_is_incomplete(
        self, fake_llm: FakeLLM, tmp_path: Path
    ) -> None:
        # An orphan must be reported, not silently indexed — a chunk with no source
        # cannot be cited, and an uncitable chunk cannot ground an answer.
        index = tmp_path / "v.json"
        await build_index(llm=fake_llm, index_path=index)

        store = LocalVectorStore(index)
        await store.set_vector("orphan", [0.1] * 16, {"text": "no source, no section"})
        assert store.orphans() == ["orphan"]


class TestIndexIsFresh:
    """The committed index must match the committed corpus."""

    @pytest.mark.live
    async def test_checked_in_index_covers_every_document(self) -> None:
        from psiog_kendra.rag.chunker import chunk_corpus

        cfg = settings()
        store = LocalVectorStore(cfg.index_path)
        expected = len(chunk_corpus(cfg.docs_dir))

        assert len(store) == expected, "index is stale - run `make index`"
        assert store.orphans() == []
