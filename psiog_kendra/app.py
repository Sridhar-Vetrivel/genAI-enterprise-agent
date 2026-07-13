"""Composition root — builds the coordinator with all four specialists wired in.

Everything downstream takes its collaborators by injection, so the test suite can
substitute a fake LLM or a fake source client without touching this module.
"""

from __future__ import annotations

from pathlib import Path

from psiog_kendra.config import settings
from psiog_kendra.coordinator import Coordinator, Specialist
from psiog_kendra.llm import LLMGateway, OllamaGateway
from psiog_kendra.rag.store import LocalVectorStore, VectorStore
from psiog_kendra.specialists.crm_agent import CRMAgent
from psiog_kendra.specialists.data_agent import DataAgent
from psiog_kendra.specialists.devops_agent import DevOpsAgent
from psiog_kendra.specialists.docs_agent import DocsAgent


def build_specialists(llm: LLMGateway, store: VectorStore) -> dict[str, Specialist]:
    """The four specialists, keyed by the domain each one owns."""
    agents: list[Specialist] = [
        DataAgent(llm),
        DevOpsAgent(llm),
        CRMAgent(llm),
        DocsAgent(llm, store),
    ]
    return {agent.domain: agent for agent in agents}


def build_copilot(
    llm: LLMGateway | None = None,
    store: VectorStore | None = None,
    index_path: Path | None = None,
) -> Coordinator:
    """Build the whole copilot. Defaults to the local Ollama LLM and the on-disk index."""
    llm = llm or OllamaGateway()
    store = store or LocalVectorStore(index_path or settings().index_path)
    return Coordinator(llm, build_specialists(llm, store))
