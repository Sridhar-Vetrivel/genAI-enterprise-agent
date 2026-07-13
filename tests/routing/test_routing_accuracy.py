"""Routing accuracy against the 12 mandatory test queries.

Two layers:

  * Offline (always runs) — the ground truth is well-formed, the accuracy maths is
    correct, and the coordinator routes to whatever the LLM decided.

  * Live (`--live`) — the real gemma3:4b actually classifies all 12 queries.
    Target: 100%. Skipped by default so CI never depends on a local GPU/RAM.

      pytest tests/routing --live
"""

from __future__ import annotations

import pytest

from psiog_kendra.app import build_copilot
from psiog_kendra.domains import ALL_DOMAINS
from psiog_kendra.llm import OllamaGateway
from psiog_kendra.qa.test_queries import TEST_QUERIES, by_id, routing_accuracy
from psiog_kendra.schemas import RoutingDecision
from tests.conftest import FakeLLM


class TestGroundTruth:
    def test_there_are_twelve_queries(self) -> None:
        assert len(TEST_QUERIES) == 12

    def test_ids_are_unique_and_sequential(self) -> None:
        assert [q.id for q in TEST_QUERIES] == list(range(1, 13))

    def test_every_expected_domain_is_in_the_vocabulary(self) -> None:
        for q in TEST_QUERIES:
            assert q.expected_domains
            assert set(q.expected_domains) <= set(ALL_DOMAINS)

    def test_every_domain_is_covered_by_at_least_one_query(self) -> None:
        covered = {d for q in TEST_QUERIES for d in q.expected_domains}
        assert covered == set(ALL_DOMAINS)

    def test_the_suite_has_cross_domain_coverage(self) -> None:
        cross = [q for q in TEST_QUERIES if q.is_cross_domain]
        assert len(cross) >= 4
        # And one that spans all four domains.
        assert any(len(q.expected_domains) == len(ALL_DOMAINS) for q in cross)

    def test_by_id_raises_on_an_unknown_query(self) -> None:
        with pytest.raises(KeyError):
            by_id(99)


class TestRoutingAccuracyMaths:
    def test_all_correct_is_one_hundred(self) -> None:
        results = {q.id: set(q.expected_domains) for q in TEST_QUERIES}
        assert routing_accuracy(results) == 100.0

    def test_all_wrong_is_zero(self) -> None:
        results = {
            q.id: {"crm"} if "crm" not in q.expected_domains else {"docs"} for q in TEST_QUERIES
        }
        assert routing_accuracy(results) == 0.0

    def test_half_correct(self) -> None:
        results = {1: {"data-platform"}, 5: {"docs"}}  # 1 right, 1 wrong
        assert routing_accuracy(results) == 50.0

    def test_a_partial_domain_set_does_not_count_as_correct(self) -> None:
        # Query 12 needs all four; returning three is a routing failure, not a near miss.
        assert routing_accuracy({12: {"data-platform", "devops", "crm"}}) == 0.0

    def test_empty_results(self) -> None:
        assert routing_accuracy({}) == 0.0


class TestCoordinatorHonoursTheRoutingDecision:
    """Whatever the LLM classifies, the coordinator must dispatch exactly that."""

    @pytest.mark.parametrize("tq", TEST_QUERIES, ids=lambda q: f"q{q.id}")
    async def test_dispatches_exactly_the_routed_domains(self, tq) -> None:
        llm = FakeLLM({RoutingDecision: RoutingDecision(domains=sorted(tq.expected_domains))})
        copilot = build_copilot(llm=llm)

        decision = await copilot.route(tq.query)
        assert set(decision.domains) == set(tq.expected_domains)


@pytest.mark.live
class TestLiveRoutingAccuracy:
    """The real LLM classifying all 12 queries. Run with: pytest tests/routing --live"""

    async def test_routing_accuracy_meets_target(self) -> None:
        copilot = build_copilot(llm=OllamaGateway())

        results: dict[int, set[str]] = {}
        failures: list[str] = []
        for tq in TEST_QUERIES:
            decision = await copilot.route(tq.query)
            results[tq.id] = set(decision.domains)
            if results[tq.id] != set(tq.expected_domains):
                failures.append(
                    f"  q{tq.id}: expected {sorted(tq.expected_domains)} "
                    f"got {sorted(results[tq.id])} - {tq.query}"
                )

        accuracy = routing_accuracy(results)
        assert accuracy == 100.0, f"routing accuracy {accuracy}%\n" + "\n".join(failures)
