"""AgentField node: the Internal Documentation specialist (RAG).

This is the one agent that uses AgentField's vector-memory fabric directly:
`memory.set_vector` to index and `memory.similarity_search` to retrieve.

    python -m agents.docs_agent

Index the corpus into the control plane's vector memory once, at startup:

    curl -X POST http://localhost:8080/api/v1/execute/docs-agent.index_documentation \
      -H "Content-Type: application/json" -d '{"input": {}}'
"""

from __future__ import annotations

from agents._runtime import make_agent
from psiog_kendra.config import settings
from psiog_kendra.llm import OllamaGateway
from psiog_kendra.rag.retriever import index_corpus
from psiog_kendra.rag.store import AgentFieldVectorStore
from psiog_kendra.schemas import AgentResponse
from psiog_kendra.specialists.docs_agent import DocsAgent

app = make_agent(
    settings().node_docs,
    description="Internal knowledge specialist: runbooks, architecture docs, incidents.",
    tags=["docs", "rag"],
)

_llm = OllamaGateway()
# Retrieval runs against AgentField's vector memory, not a local file.
_store = AgentFieldVectorStore(app.memory)
_agent = DocsAgent(_llm, _store)


@app.skill()
async def index_documentation() -> dict[str, int]:
    """Deterministic: chunk -> embed -> set_vector. Run once at setup."""
    chunks = await index_corpus(_store, _llm, settings().docs_dir)
    return {"chunks_indexed": len(chunks)}


@app.skill()
async def search_documentation(query: str) -> list[dict[str, object]]:
    """Deterministic: semantic similarity search. No keyword matching anywhere."""
    hits = await _agent.search(query)
    return [
        {"citation": h.citation, "section": h.section, "score": h.score, "text": h.text}
        for h in hits
    ]


@app.reasoner()
async def answer_docs_question(query: str) -> AgentResponse:
    """LLM: answer strictly from the retrieved chunks, citing document and section."""
    return await _agent.answer(query)


if __name__ == "__main__":
    app.run()
