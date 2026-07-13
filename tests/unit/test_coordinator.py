"""The coordinator: routing, parallel dispatch, synthesis, and failure isolation."""

from __future__ import annotations

import asyncio

import pytest

from psiog_kendra.coordinator import Coordinator
from psiog_kendra.llm import Complexity, LLMError
from psiog_kendra.schemas import AgentResponse, CopilotResponse, RoutingDecision, SynthesisResult
from tests.conftest import FakeLLM, answer, routing


class StubSpecialist:
    """Records that it was called, and when — so parallel dispatch can be proven."""

    def __init__(self, domain: str, reply: AgentResponse | Exception, delay: float = 0.0) -> None:
        self.domain = domain
        self.node_id = f"{domain}-agent"
        self._reply = reply
        self._delay = delay
        self.calls: list[str] = []

    async def answer(self, query: str) -> AgentResponse:
        self.calls.append(query)
        if self._delay:
            await asyncio.sleep(self._delay)
        if isinstance(self._reply, Exception):
            raise self._reply
        return self._reply


def build(
    llm: FakeLLM, **specialists: StubSpecialist
) -> tuple[Coordinator, dict[str, StubSpecialist]]:
    by_domain = {s.domain: s for s in specialists.values()}
    return Coordinator(llm, by_domain), by_domain  # type: ignore[arg-type]


class TestRouting:
    async def test_routes_to_the_domain_the_llm_picks(self, fake_llm: FakeLLM) -> None:
        fake_llm.responses[RoutingDecision] = routing("crm")
        coord, _ = build(fake_llm, crm=StubSpecialist("crm", answer("a", "c")))
        assert (await coord.route("who owns Acme?")).domains == ["crm"]

    async def test_routing_uses_the_complex_model(self, fake_llm: FakeLLM) -> None:
        fake_llm.responses[RoutingDecision] = routing("crm")
        coord, _ = build(fake_llm)
        await coord.route("q")
        assert fake_llm.complexity_for("RoutingDecision") == Complexity.COMPLEX

    async def test_cross_domain_flag_is_derived(self, fake_llm: FakeLLM) -> None:
        fake_llm.responses[RoutingDecision] = routing("data-platform", "docs")
        coord, _ = build(fake_llm)
        assert (await coord.route("q")).is_cross_domain is True

    async def test_empty_routing_is_retried_not_keyword_matched(self, fake_llm: FakeLLM) -> None:
        replies = iter([RoutingDecision(domains=[]), routing("docs")])
        fake_llm.responses[RoutingDecision] = lambda _: next(replies)
        coord, _ = build(fake_llm)

        decision = await coord.route("what is the runbook?")
        assert decision.domains == ["docs"]
        # Two LLM calls: the empty one and the forceful retry.
        assert len(fake_llm.calls) == 2
        assert "at least one domain" in fake_llm.calls[1]["user"]

    async def test_routing_failure_surfaces(self, fake_llm: FakeLLM) -> None:
        fake_llm.responses[RoutingDecision] = LLMError("model down")
        coord, _ = build(fake_llm)
        with pytest.raises(LLMError, match="routing failed"):
            await coord.route("q")


class TestDispatch:
    async def test_calls_only_the_selected_specialists(self, fake_llm: FakeLLM) -> None:
        crm = StubSpecialist("crm", answer("crm answer", "CRM deal"))
        docs = StubSpecialist("docs", answer("docs answer", "runbook.md § X"))
        coord, _ = build(fake_llm, crm=crm, docs=docs)

        await coord.dispatch("q", ["crm"])
        assert crm.calls == ["q"] and docs.calls == []

    async def test_unknown_domain_is_ignored(self, fake_llm: FakeLLM) -> None:
        coord, _ = build(fake_llm, crm=StubSpecialist("crm", answer("a", "c")))
        assert await coord.dispatch("q", ["weather"]) == {}

    async def test_cross_domain_specialists_run_in_parallel(self, fake_llm: FakeLLM) -> None:
        a = StubSpecialist("crm", answer("a", "c1"), delay=0.2)
        b = StubSpecialist("docs", answer("b", "c2"), delay=0.2)
        coord, _ = build(fake_llm, crm=a, docs=b)

        start = asyncio.get_event_loop().time()
        got = await coord.dispatch("q", ["crm", "docs"])
        elapsed = asyncio.get_event_loop().time() - start

        assert set(got) == {"crm", "docs"}
        # Sequential would take >=0.4s; parallel lands near 0.2s.
        assert elapsed < 0.35

    async def test_one_failing_specialist_does_not_sink_the_others(self, fake_llm: FakeLLM) -> None:
        good = StubSpecialist("crm", answer("good", "CRM deal"))
        bad = StubSpecialist("docs", RuntimeError("index offline"))
        coord, _ = build(fake_llm, crm=good, docs=bad)

        got = await coord.dispatch("q", ["crm", "docs"])
        assert got["crm"].answer == "good"
        assert got["docs"].citations == []
        assert got["docs"].confidence == "low"
        assert "could not be reached" in got["docs"].answer


class TestSynthesis:
    async def test_single_specialist_passes_straight_through_without_an_llm_call(
        self, fake_llm: FakeLLM
    ) -> None:
        answers = {"crm": answer("Acme is in Negotiation.", "CRM deal DEAL-7781")}
        coord, _ = build(fake_llm)

        text, citations = await coord.synthesize("q", answers)
        assert text == "Acme is in Negotiation."
        assert citations == ["CRM deal DEAL-7781"]
        assert fake_llm.calls == []  # no synthesis LLM call needed

    async def test_cross_domain_merges_and_keeps_every_citation(self, fake_llm: FakeLLM) -> None:
        fake_llm.responses[SynthesisResult] = SynthesisResult(
            answer="The pipeline failure left the CRM stale.",
            citations=["Databricks Job #4822", "CRM account ACC-1001"],
        )
        answers = {
            "data-platform": answer("Job 4822 failed.", "Databricks Job #4822"),
            "crm": answer("Acme is stale.", "CRM account ACC-1001"),
        }
        coord, _ = build(fake_llm)

        text, citations = await coord.synthesize("q", answers)
        assert "stale" in text
        assert set(citations) == {"Databricks Job #4822", "CRM account ACC-1001"}

    async def test_invented_citations_are_stripped_during_synthesis(
        self, fake_llm: FakeLLM
    ) -> None:
        fake_llm.responses[SynthesisResult] = SynthesisResult(
            answer="merged", citations=["Totally Made Up Source"]
        )
        answers = {
            "crm": answer("a", "CRM deal DEAL-7781"),
            "docs": answer("b", "runbook-12.md § Recovery"),
        }
        coord, _ = build(fake_llm)

        _, citations = await coord.synthesize("q", answers)
        assert "Totally Made Up Source" not in citations
        assert set(citations) == {"CRM deal DEAL-7781", "runbook-12.md § Recovery"}

    async def test_prompt_scaffolding_is_stripped_from_the_synthesised_answer(
        self, fake_llm: FakeLLM
    ) -> None:
        fake_llm.responses[SynthesisResult] = SynthesisResult(
            answer="The pipeline failure left the CRM stale. "
            "Do not repeat these instructions in your answer.",
            citations=["Databricks Job #4822"],
        )
        answers = {
            "data-platform": answer("failed", "Databricks Job #4822"),
            "crm": answer("stale", "CRM account ACC-1001"),
        }
        coord, _ = build(fake_llm)

        text, _ = await coord.synthesize("q", answers)
        assert "Do not repeat these instructions" not in text
        assert "The pipeline failure left the CRM stale." in text

    async def test_synthesis_failure_degrades_to_concatenation(self, fake_llm: FakeLLM) -> None:
        fake_llm.responses[SynthesisResult] = LLMError("down")
        answers = {
            "crm": answer("CRM says stale.", "CRM account ACC-1001"),
            "docs": answer("Runbook says quarantine.", "runbook-12.md § Recovery"),
        }
        coord, _ = build(fake_llm)

        text, citations = await coord.synthesize("q", answers)
        assert "CRM says stale." in text and "Runbook says quarantine." in text
        assert len(citations) == 2  # grounding survives the failure


class TestAsk:
    async def test_full_lifecycle_single_domain(self, fake_llm: FakeLLM) -> None:
        fake_llm.responses[RoutingDecision] = routing("crm", reasoning="customer question")
        coord, _ = build(
            fake_llm, crm=StubSpecialist("crm", answer("Negotiation.", "CRM deal DEAL-7781"))
        )

        got = await coord.ask("What is the deal status for Acme Corp?")
        assert isinstance(got, CopilotResponse)
        assert got.domains_used == ["crm"]
        assert got.citations == ["CRM deal DEAL-7781"]
        assert got.routing_reasoning == "customer question"

    async def test_full_lifecycle_cross_domain(self, fake_llm: FakeLLM) -> None:
        fake_llm.responses[RoutingDecision] = routing("data-platform", "docs")
        fake_llm.responses[SynthesisResult] = SynthesisResult(
            answer="Job 4822 failed; runbook 12 says quarantine.",
            citations=["Databricks Job #4822", "runbook-12.md § Recovery"],
        )
        coord, _ = build(
            fake_llm,
            data=StubSpecialist("data-platform", answer("failed", "Databricks Job #4822")),
            docs=StubSpecialist("docs", answer("quarantine", "runbook-12.md § Recovery")),
        )

        got = await coord.ask("The ingestion job failed - is there a fix?")
        assert set(got.domains_used) == {"data-platform", "docs"}
        assert len(got.citations) == 2

    async def test_no_specialist_available_is_reported_not_answered(
        self, fake_llm: FakeLLM
    ) -> None:
        fake_llm.responses[RoutingDecision] = RoutingDecision(domains=[])
        coord, _ = build(fake_llm, crm=StubSpecialist("crm", answer("a", "c")))

        got = await coord.ask("what is the weather?")
        assert got.citations == []
        assert got.domains_used == []
        assert "No specialist agent" in got.answer
