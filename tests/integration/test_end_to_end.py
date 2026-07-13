"""End-to-end: query in -> cited response out.

Real source fixtures, real chunking, real vector index, real coordinator. Only the LLM
is faked — so these prove the wiring and the grounding, not the model's prose.

The `--live` variants run the whole thing against the real gemma3 models.
"""

from __future__ import annotations

import pytest

from psiog_kendra.app import build_copilot, build_specialists
from psiog_kendra.config import reset_settings
from psiog_kendra.domains import ALL_DOMAINS
from psiog_kendra.llm import OllamaGateway
from psiog_kendra.qa.test_queries import by_id
from psiog_kendra.rag.store import LocalVectorStore
from psiog_kendra.schemas import AgentResponse, RoutingDecision, SynthesisResult
from tests.conftest import FakeLLM, routing


@pytest.fixture(autouse=True)
def _permissive_rag(monkeypatch: pytest.MonkeyPatch) -> None:
    # FakeLLM's pseudo-embeddings do not reproduce nomic's score distribution.
    monkeypatch.setenv("RAG_MIN_SCORE", "0.0")
    reset_settings()


class TestWiring:
    def test_every_domain_has_exactly_one_specialist(
        self, fake_llm: FakeLLM, indexed_store: LocalVectorStore
    ) -> None:
        specialists = build_specialists(fake_llm, indexed_store)
        assert set(specialists) == set(ALL_DOMAINS)

    def test_specialists_are_distinct_agents_not_one_llm(
        self, fake_llm: FakeLLM, indexed_store: LocalVectorStore
    ) -> None:
        specialists = build_specialists(fake_llm, indexed_store)
        node_ids = {s.node_id for s in specialists.values()}
        assert len(node_ids) == 4
        types = {type(s).__name__ for s in specialists.values()}
        assert types == {"DataAgent", "DevOpsAgent", "CRMAgent", "DocsAgent"}


class TestSingleDomainLifecycle:
    async def test_data_platform_query_is_grounded_in_databricks(
        self, fake_llm: FakeLLM, indexed_store: LocalVectorStore
    ) -> None:
        fake_llm.responses[RoutingDecision] = routing("data-platform")
        fake_llm.responses[AgentResponse] = lambda user: AgentResponse(
            answer="sales_etl completed successfully.",
            citations=[line[2:] for line in user.splitlines() if line.startswith("- ")][:1],
        )
        copilot = build_copilot(llm=fake_llm, store=indexed_store)

        got = await copilot.ask(by_id(1).query)
        assert got.domains_used == ["data-platform"]
        assert got.citations and got.citations[0].startswith("Databricks Job #")

    async def test_docs_query_is_grounded_in_a_document_section(
        self, fake_llm: FakeLLM, indexed_store: LocalVectorStore
    ) -> None:
        fake_llm.responses[RoutingDecision] = routing("docs")
        fake_llm.responses[AgentResponse] = lambda user: AgentResponse(
            answer="Quarantine the partition and re-run the job.",
            citations=[line[2:] for line in user.splitlines() if line.startswith("- ")][:1],
        )
        copilot = build_copilot(llm=fake_llm, store=indexed_store)

        got = await copilot.ask(by_id(7).query)
        assert got.domains_used == ["docs"]
        assert "§" in got.citations[0]  # document + section

    async def test_crm_query_is_grounded_in_a_crm_record(
        self, fake_llm: FakeLLM, indexed_store: LocalVectorStore
    ) -> None:
        fake_llm.responses[RoutingDecision] = routing("crm")
        fake_llm.responses[AgentResponse] = lambda user: AgentResponse(
            answer="Karthik Rao owns TechStart Ltd.",
            citations=[line[2:] for line in user.splitlines() if line.startswith("- ")][:1],
        )
        copilot = build_copilot(llm=fake_llm, store=indexed_store)

        got = await copilot.ask(by_id(6).query)
        assert got.citations and got.citations[0].startswith("CRM ")


class TestCrossDomainLifecycle:
    async def test_pipeline_failure_and_crm_impact_are_cross_cited(
        self, fake_llm: FakeLLM, indexed_store: LocalVectorStore
    ) -> None:
        fake_llm.responses[RoutingDecision] = routing("data-platform", "crm")
        fake_llm.responses[AgentResponse] = lambda user: AgentResponse(
            answer="grounded",
            citations=[line[2:] for line in user.splitlines() if line.startswith("- ")][:1],
        )
        fake_llm.responses[SynthesisResult] = lambda user: SynthesisResult(
            answer="The crm_sync failure left Acme stale.",
            # Keep every citation the specialists reported.
            citations=[
                c.strip()
                for line in user.splitlines()
                if line.startswith("Citations: ")
                for c in line.removeprefix("Citations: ").split(", ")
                if c.strip() and c.strip() != "none"
            ],
        )
        copilot = build_copilot(llm=fake_llm, store=indexed_store)

        got = await copilot.ask(by_id(9).query)
        assert set(got.domains_used) == {"data-platform", "crm"}
        # The answer must cite BOTH systems, which is the whole point of cross-domain.
        assert any(c.startswith("Databricks") for c in got.citations)
        assert any(c.startswith("CRM") for c in got.citations)

    async def test_a_dead_specialist_does_not_lose_the_other_domain(
        self, fake_llm: FakeLLM, indexed_store: LocalVectorStore
    ) -> None:
        fake_llm.responses[RoutingDecision] = routing("data-platform", "docs")
        fake_llm.responses[AgentResponse] = lambda user: AgentResponse(
            answer="grounded",
            citations=[line[2:] for line in user.splitlines() if line.startswith("- ")][:1],
        )
        fake_llm.responses[SynthesisResult] = SynthesisResult(answer="merged", citations=[])

        specialists = build_specialists(fake_llm, indexed_store)

        async def boom(_: str) -> AgentResponse:
            raise RuntimeError("vector index offline")

        specialists["docs"].answer = boom  # type: ignore[method-assign]
        from psiog_kendra.coordinator import Coordinator

        got = await Coordinator(fake_llm, specialists).ask(by_id(10).query)
        assert set(got.domains_used) == {"data-platform", "docs"}
        assert got.answer  # still answers from the surviving specialist


@pytest.mark.live
class TestLiveEndToEnd:
    """The real models, the real index. Run with: pytest tests/integration --live"""

    async def test_a_docs_question_returns_a_cited_answer(self) -> None:
        copilot = build_copilot(llm=OllamaGateway())
        got = await copilot.ask(by_id(7).query)

        assert got.citations, "a live answer must be grounded"
        assert got.domains_used
        assert len(got.answer) > 40

    async def test_a_cross_domain_question_cites_more_than_one_system(self) -> None:
        copilot = build_copilot(llm=OllamaGateway())
        got = await copilot.ask(by_id(9).query)

        assert len(got.domains_used) >= 2
        assert got.citations
