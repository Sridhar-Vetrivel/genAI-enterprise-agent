"""Chunking, the vector store, and semantic retrieval — including the Week 7 gate."""

from __future__ import annotations

from pathlib import Path

import pytest

from psiog_kendra.config import reset_settings, settings
from psiog_kendra.rag.chunker import chunk_corpus, chunk_markdown
from psiog_kendra.rag.retriever import index_corpus, retrieve
from psiog_kendra.rag.store import LocalVectorStore
from tests.conftest import FakeLLM

DOC = """# Runbook 99

Preamble text.

## Symptom

The job fails loudly.

## Recovery

Turn it off and on again.
"""


class TestChunkMarkdown:
    def test_splits_on_section_headings(self) -> None:
        chunks = chunk_markdown(DOC, source="runbook-99.md")
        assert {c.section for c in chunks} >= {"Symptom", "Recovery"}

    def test_chunk_carries_its_section_so_it_can_be_cited(self) -> None:
        chunk = next(c for c in chunk_markdown(DOC, source="r.md") if c.section == "Recovery")
        assert chunk.citation == "r.md § Recovery"
        assert "on again" in chunk.text

    def test_heading_is_prepended_so_the_embedding_carries_the_topic(self) -> None:
        chunk = next(c for c in chunk_markdown(DOC, source="r.md") if c.section == "Symptom")
        assert chunk.text.startswith("Symptom")

    def test_chunk_ids_are_unique(self) -> None:
        ids = [c.chunk_id for c in chunk_markdown(DOC, source="r.md")]
        assert len(ids) == len(set(ids))

    def test_document_with_no_headings_still_produces_a_chunk(self) -> None:
        chunks = chunk_markdown("just prose, no headings", source="flat.md")
        assert len(chunks) == 1 and chunks[0].section == "Document"

    def test_empty_document_produces_nothing(self) -> None:
        assert chunk_markdown("", source="empty.md") == []

    def test_long_section_is_windowed(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("RAG_CHUNK_CHARS", "100")
        monkeypatch.setenv("RAG_CHUNK_OVERLAP", "20")
        reset_settings()
        chunks = chunk_markdown(f"## Long\n\n{'x' * 500}", source="long.md")
        assert len(chunks) > 1

    def test_metadata_has_everything_a_citation_needs(self) -> None:
        meta = chunk_markdown(DOC, source="r.md")[0].metadata()
        assert {"source", "section", "url", "citation", "text"} <= set(meta)


class TestChunkCorpus:
    def test_chunks_the_real_docs(self) -> None:
        chunks = chunk_corpus(settings().docs_dir)
        assert len(chunks) > 5
        assert any("runbook-12" in c.source for c in chunks)

    def test_missing_directory_yields_nothing(self, tmp_path: Path) -> None:
        assert chunk_corpus(tmp_path / "nope") == []


class TestLocalVectorStore:
    async def test_stores_and_retrieves_by_similarity(self) -> None:
        store = LocalVectorStore()
        await store.set_vector("a", [1.0, 0.0], {"text": "A"})
        await store.set_vector("b", [0.0, 1.0], {"text": "B"})

        hits = await store.similarity_search([1.0, 0.0], top_k=2)
        assert hits[0]["key"] == "a"
        assert hits[0]["score"] > hits[1]["score"]

    async def test_top_k_limits_results(self) -> None:
        store = LocalVectorStore()
        for i in range(5):
            await store.set_vector(f"k{i}", [float(i), 1.0], {"text": str(i)})
        assert len(await store.similarity_search([1.0, 1.0], top_k=2)) == 2

    async def test_empty_store_returns_nothing(self) -> None:
        assert await LocalVectorStore().similarity_search([1.0], top_k=5) == []

    async def test_round_trips_through_disk(self, tmp_path: Path) -> None:
        path = tmp_path / "v.json"
        store = LocalVectorStore(path)
        await store.set_vector("a", [1.0, 2.0], {"text": "A", "source": "s"})
        store.save()

        reloaded = LocalVectorStore(path)
        assert len(reloaded) == 1
        hits = await reloaded.similarity_search([1.0, 2.0], top_k=1)
        assert hits[0]["metadata"]["source"] == "s"

    async def test_orphan_detection_flags_missing_metadata(self) -> None:
        store = LocalVectorStore()
        await store.set_vector(
            "good", [1.0], {"source": "s", "section": "x", "citation": "c", "text": "t"}
        )
        await store.set_vector("bad", [1.0], {"source": "s"})
        assert store.orphans() == ["bad"]


class TestIndexAndRetrieve:
    async def test_indexes_every_chunk(self, fake_llm: FakeLLM, tmp_path: Path) -> None:
        store = LocalVectorStore(tmp_path / "v.json")
        chunks = await index_corpus(store, fake_llm, settings().docs_dir)
        assert len(chunks) == len(store)
        assert len(fake_llm.embed_calls) == len(chunks)

    async def test_week7_gate_no_orphan_chunks(self, indexed_store: LocalVectorStore) -> None:
        assert indexed_store.orphans() == []

    async def test_retrieval_is_semantic_and_returns_citations(
        self, fake_llm: FakeLLM, indexed_store: LocalVectorStore
    ) -> None:
        hits = await retrieve("schema mismatch recovery", indexed_store, fake_llm, min_score=0.0)
        assert hits
        assert all(h.citation and h.source for h in hits)
        # Results must come back ranked.
        assert [h.score for h in hits] == sorted((h.score for h in hits), reverse=True)

    async def test_low_scoring_chunks_are_dropped_not_cited(
        self, fake_llm: FakeLLM, indexed_store: LocalVectorStore
    ) -> None:
        # Nothing can clear a similarity threshold of 1.1, so nothing may be cited.
        assert await retrieve("anything", indexed_store, fake_llm, min_score=1.1) == []

    async def test_top_k_is_respected(
        self, fake_llm: FakeLLM, indexed_store: LocalVectorStore
    ) -> None:
        hits = await retrieve("pipeline", indexed_store, fake_llm, top_k=2, min_score=0.0)
        assert len(hits) <= 2

    async def test_empty_index_retrieves_nothing(self, fake_llm: FakeLLM) -> None:
        assert await retrieve("q", LocalVectorStore(), fake_llm, min_score=0.0) == []
