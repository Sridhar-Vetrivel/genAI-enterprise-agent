"""Shared fixtures.

The whole suite runs offline: no Ollama, no control plane, no network. The LLM is
replaced by FakeLLM, which returns scripted structured responses and records what it was
asked — so tests can assert on the model tier a call used, not just its output.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, TypeVar

import pytest
from pydantic import BaseModel

from psiog_kendra.config import reset_settings, settings
from psiog_kendra.llm import Complexity, LLMError
from psiog_kendra.rag.store import LocalVectorStore
from psiog_kendra.schemas import AgentResponse, RoutingDecision
from psiog_kendra.sources.base import load_mock

T = TypeVar("T", bound=BaseModel)


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--live",
        action="store_true",
        default=False,
        help="Run tests that call the real local LLM (needs Ollama + ~4 GiB free RAM).",
    )


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "live: needs a running Ollama with the models pulled")


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if config.getoption("--live"):
        return
    skip = pytest.mark.skip(reason="needs a live LLM; run with --live")
    for item in items:
        if "live" in item.keywords:
            item.add_marker(skip)


@pytest.fixture(autouse=True)
def _clean_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    """Every test starts from the documented defaults, never the developer's .env."""
    for key in (
        "USE_MOCK_SOURCES",
        "AI_MODEL_COMPLEX",
        "AI_MODEL_SIMPLE",
        "RAG_MIN_SCORE",
        "MAX_RECORDS_IN_PROMPT",
        "DATABRICKS_HOST",
        "DATABRICKS_TOKEN",
        "GITHUB_TOKEN",
        "CRM_API_BASE",
        "CRM_API_KEY",
        "AI_FALLBACK_ON_OOM",
        "AI_RETRIES",
    ):
        monkeypatch.delenv(key, raising=False)
    reset_settings()
    yield
    reset_settings()


class FakeLLM:
    """A scripted LLMGateway.

    `responses` maps a schema class to the object (or exception) to return. `calls`
    records (schema_name, complexity, system, user) for every structured() call.
    """

    def __init__(
        self,
        responses: dict[type[BaseModel], Any] | None = None,
        embedding: list[float] | None = None,
    ) -> None:
        self.responses = responses or {}
        self.calls: list[dict[str, Any]] = []
        self.embed_calls: list[str] = []
        self._embedding = embedding

    async def structured(
        self,
        *,
        system: str,
        user: str,
        schema: type[T],
        complexity: Complexity = Complexity.COMPLEX,
    ) -> T:
        self.calls.append(
            {"schema": schema.__name__, "complexity": complexity, "system": system, "user": user}
        )
        if schema not in self.responses:
            raise LLMError(f"FakeLLM has no scripted response for {schema.__name__}")
        reply = self.responses[schema]
        if isinstance(reply, Exception):
            raise reply
        if callable(reply):
            return reply(user)
        return reply

    async def embed(self, text: str) -> list[float]:
        self.embed_calls.append(text)
        if self._embedding is not None:
            return self._embedding
        # Deterministic pseudo-embedding: character-histogram, no model needed.
        vec = [0.0] * 16
        for ch in text.lower():
            vec[ord(ch) % 16] += 1.0
        norm = sum(v * v for v in vec) ** 0.5 or 1.0
        return [v / norm for v in vec]

    def complexity_for(self, schema_name: str) -> Complexity | None:
        for call in self.calls:
            if call["schema"] == schema_name:
                return call["complexity"]
        return None


@pytest.fixture
def fake_llm() -> FakeLLM:
    return FakeLLM()


def routing(*domains: str, reasoning: str = "test") -> RoutingDecision:
    return RoutingDecision(domains=list(domains), reasoning=reasoning)


def answer(text: str, *citations: str, confidence: str = "high") -> AgentResponse:
    return AgentResponse(answer=text, citations=list(citations), confidence=confidence)


@pytest.fixture
def mock_databricks() -> dict[str, Any]:
    return load_mock("databricks")


@pytest.fixture
def mock_devops() -> dict[str, Any]:
    return load_mock("devops")


@pytest.fixture
def mock_crm() -> dict[str, Any]:
    return load_mock("crm")


@pytest.fixture
async def indexed_store(fake_llm: FakeLLM, tmp_path: Path) -> LocalVectorStore:
    """A vector store populated from the real docs corpus using FakeLLM embeddings."""
    from psiog_kendra.rag.retriever import index_corpus

    store = LocalVectorStore(tmp_path / "vectors.json")
    await index_corpus(store, fake_llm, settings().docs_dir)
    return store
