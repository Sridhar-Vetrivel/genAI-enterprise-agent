"""Docs specialist — semantic search over indexed internal documentation (RAG).

Skill (deterministic): embed the query, run a similarity search over the vector index.
Reasoner (LLM): answer strictly from the retrieved chunks, citing document and section.

This is the only agent whose retrieval is purely semantic: no keyword match anywhere.
"""

from __future__ import annotations

from psiog_kendra.config import settings
from psiog_kendra.domains import DOCS
from psiog_kendra.llm import Complexity, LLMError, LLMGateway
from psiog_kendra.prompting import build_grounded_prompt, finalize
from psiog_kendra.rag.retriever import Retrieved, retrieve
from psiog_kendra.rag.store import VectorStore
from psiog_kendra.schemas import AgentResponse

SYSTEM = """You are the Internal Documentation specialist for the Psiog enterprise copilot.
You answer questions from runbooks, architecture docs and incident records.

Rules you must not break:
- Use ONLY the document excerpts given to you. They are the single source of truth.
- Never add a step, threshold or recommendation that is not in the excerpts.
- If the excerpts do not answer the question, say the documentation does not cover it.
- When the answer is a runbook procedure, give the steps in order.
- Every citation must be one of the citation strings supplied to you, copied verbatim.
- Be concise: 2-5 sentences.
"""


class DocsAgent:
    """The docs specialist. Its node id comes from NODE_DOCS_AGENT."""

    domain = DOCS

    def __init__(self, llm: LLMGateway, store: VectorStore) -> None:
        self.node_id = settings().node_docs
        self._llm = llm
        self._store = store

    async def search(self, query: str) -> list[Retrieved]:
        """Skill: semantic similarity search over the indexed corpus."""
        return await retrieve(query, self._store, self._llm)

    async def answer(self, query: str) -> AgentResponse:
        """Reasoner: produce a grounded, cited answer from retrieved chunks."""
        chunks = await self.search(query)
        if not chunks:
            return AgentResponse(
                answer="The indexed internal documentation does not cover this question.",
                citations=[],
                confidence="low",
            )

        citations = list(dict.fromkeys(c.citation for c in chunks))
        excerpts = "\n\n".join(
            f"[{c.citation}] (similarity {c.score:.2f})\n{c.text}" for c in chunks
        )
        user = build_grounded_prompt(
            question=query,
            facts_label="Excerpts retrieved from the internal documentation:",
            facts=excerpts,
            citations=citations,
        )
        try:
            response = await self._llm.structured(
                system=SYSTEM, user=user, schema=AgentResponse, complexity=Complexity.COMPLEX
            )
        except LLMError:
            top = chunks[0]
            return AgentResponse(answer=top.text[:400], citations=[top.citation], confidence="low")
        # Strip recited scaffolding, lift any inline citation out of the prose, and keep
        # only citations we actually supplied. See prompting.finalize.
        response.answer, response.citations = finalize(
            response.answer, response.citations, citations
        )
        return response
