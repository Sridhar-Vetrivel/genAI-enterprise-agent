"""The structured-output contracts and the domain vocabulary."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from psiog_kendra.domains import ALL_DOMAINS, agent_for, normalize_domain, normalize_domains
from psiog_kendra.schemas import AgentResponse, CopilotResponse, JudgeVerdict, RoutingDecision


class TestNormalizeDomain:
    @pytest.mark.parametrize("raw", ["data-platform", "DATA-PLATFORM", " data_platform "])
    def test_canonical_and_casing(self, raw: str) -> None:
        assert normalize_domain(raw) == "data-platform"

    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("databricks", "data-platform"),
            ("ETL", "data-platform"),
            ("ci/cd", "devops"),
            ("deployments", "devops"),
            ("customers", "crm"),
            ("hubspot", "crm"),
            ("runbooks", "docs"),
            ("documentation", "docs"),
            ("docs-agent", "docs"),
        ],
    )
    def test_aliases_a_small_model_actually_emits(self, raw: str, expected: str) -> None:
        assert normalize_domain(raw) == expected

    @pytest.mark.parametrize("raw", ["", "   ", "weather", "Cloud Monitoring", "nonsense"])
    def test_unknown_labels_are_dropped_not_guessed(self, raw: str) -> None:
        assert normalize_domain(raw) is None

    def test_non_string_input(self) -> None:
        assert normalize_domain(None) is None  # type: ignore[arg-type]
        assert normalize_domain(42) is None  # type: ignore[arg-type]


class TestNormalizeDomains:
    def test_deduplicates_and_orders_canonically(self) -> None:
        got = normalize_domains(["docs", "databricks", "docs", "data-platform"])
        assert got == ["data-platform", "docs"]

    def test_drops_unknowns_but_keeps_valid_ones(self) -> None:
        assert normalize_domains(["crm", "Cloud Monitoring", "weather"]) == ["crm"]

    def test_all_unknown_yields_empty(self) -> None:
        assert normalize_domains(["weather", "astrology"]) == []


class TestRoutingDecision:
    def test_normalises_model_emitted_labels(self) -> None:
        d = RoutingDecision(domains=["Databricks", "runbooks"], reasoning="r")
        assert d.domains == ["data-platform", "docs"]

    def test_cross_domain_is_derived_not_trusted(self) -> None:
        # The model claims a single domain is cross-domain. The domain list wins.
        d = RoutingDecision(domains=["crm"], is_cross_domain=True)
        assert d.is_cross_domain is False

        d = RoutingDecision(domains=["crm", "docs"], is_cross_domain=False)
        assert d.is_cross_domain is True

    def test_bare_string_is_accepted(self) -> None:
        assert RoutingDecision(domains="crm").domains == ["crm"]  # type: ignore[arg-type]

    def test_garbage_domains_yield_empty_list(self) -> None:
        assert RoutingDecision(domains=["weather"]).domains == []

    def test_extra_fields_are_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            RoutingDecision(domains=["crm"], sneaky="value")  # type: ignore[call-arg]


class TestAgentResponse:
    def test_confidence_is_clamped_to_the_vocabulary(self) -> None:
        assert AgentResponse(answer="a", confidence="VERY HIGH").confidence == "medium"
        assert AgentResponse(answer="a", confidence="High").confidence == "high"

    def test_citations_coerced_and_blanks_dropped(self) -> None:
        r = AgentResponse(answer="a", citations=["  x  ", "", "y"])
        assert r.citations == ["x", "y"]

    def test_single_citation_string(self) -> None:
        assert AgentResponse(answer="a", citations="src").citations == ["src"]  # type: ignore[arg-type]

    def test_extra_fields_are_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            AgentResponse(answer="a", hallucination="none")  # type: ignore[call-arg]


class TestJudgeVerdict:
    def test_hallucination_rate_formula(self) -> None:
        v = JudgeVerdict(grounded_claims=["a"] * 9, ungrounded_claims=["x"])
        assert v.total_claims == 10
        assert v.hallucination_rate == 10.0

    def test_fully_grounded(self) -> None:
        assert JudgeVerdict(grounded_claims=["a", "b"]).hallucination_rate == 0.0

    def test_fully_ungrounded(self) -> None:
        assert JudgeVerdict(ungrounded_claims=["a", "b"]).hallucination_rate == 100.0

    def test_an_empty_verdict_is_unmeasured_not_clean(self) -> None:
        # The bug this guards: a judge that enumerates nothing must not read as 0%
        # hallucination. `is_measured` is what tells the caller the judge did no work.
        v = JudgeVerdict()
        assert v.total_claims == 0
        assert v.is_measured is False

    def test_a_verdict_with_claims_is_measured(self) -> None:
        assert JudgeVerdict(grounded_claims=["a"]).is_measured is True

    def test_claims_are_coerced_and_blanks_dropped(self) -> None:
        v = JudgeVerdict(grounded_claims=["  a  ", "", "b"])
        assert v.grounded_claims == ["a", "b"]

    def test_a_bare_string_claim_is_accepted(self) -> None:
        assert JudgeVerdict(ungrounded_claims="just one").ungrounded_claims == ["just one"]  # type: ignore[arg-type]

    def test_extra_fields_are_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            JudgeVerdict(grounded_claims=[], total_claims=5)  # type: ignore[call-arg]


class TestCopilotResponse:
    def test_defaults_are_empty_not_none(self) -> None:
        r = CopilotResponse(answer="a")
        assert r.citations == [] and r.domains_used == []


def test_agent_for_resolves_every_domain() -> None:
    for domain in ALL_DOMAINS:
        assert agent_for(domain)


def test_agent_ids_are_env_configurable(monkeypatch: pytest.MonkeyPatch) -> None:
    from psiog_kendra.config import reset_settings

    monkeypatch.setenv("NODE_CRM_AGENT", "custom-crm-node")
    reset_settings()
    assert agent_for("crm") == "custom-crm-node"
