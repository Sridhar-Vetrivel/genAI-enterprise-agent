"""The four specialist agents: skills, reasoners, grounding and degradation."""

from __future__ import annotations

import pytest

from psiog_kendra.config import reset_settings
from psiog_kendra.llm import Complexity, LLMError
from psiog_kendra.rag.store import LocalVectorStore
from psiog_kendra.schemas import AgentResponse
from psiog_kendra.specialists.crm_agent import CRMAgent, infer_account
from psiog_kendra.specialists.data_agent import DataAgent, infer_job_name, wants_failure
from psiog_kendra.specialists.devops_agent import DevOpsAgent, infer_service
from psiog_kendra.specialists.docs_agent import DocsAgent
from tests.conftest import FakeLLM, answer


class TestInferenceHelpers:
    """The deterministic hints that narrow a lookup. They never decide the answer."""

    @pytest.mark.parametrize(
        ("query", "expected"),
        [
            ("did the sales etl run?", "sales_etl"),
            ("the ingestion job failed", "ingestion_raw_events"),
            ("did the crm sync work?", "crm_sync"),
            ("how is the weather", None),
        ],
    )
    def test_infer_job_name_from_the_records(self, query: str, expected: str | None) -> None:
        known = ["sales_etl", "ingestion_raw_events", "crm_sync"]
        assert infer_job_name(query, known) == expected

    def test_infer_job_name_with_no_known_jobs(self) -> None:
        assert infer_job_name("sales etl", []) is None

    @pytest.mark.parametrize(
        ("query", "expected"),
        [
            ("did payments deploy?", "payments-service"),
            ("last deployment for the auth service", "auth-service"),
            ("nothing relevant", None),
        ],
    )
    def test_infer_service_from_the_records(self, query: str, expected: str | None) -> None:
        known = ["payments-service", "auth-service", "ingestion-service"]
        assert infer_service(query, known) == expected

    @pytest.mark.parametrize(
        ("query", "expected"),
        [
            ("deal status for Acme Corp", "Acme Corp"),
            ("who owns TechStart Ltd", "TechStart Ltd"),
        ],
    )
    def test_infer_account_from_the_records(self, query: str, expected: str) -> None:
        known = ["Acme Corp", "TechStart Ltd", "Northwind Retail"]
        assert infer_account(query, known) == expected

    def test_infer_account_falls_back_to_a_capitalised_name(self) -> None:
        # An account we have never seen must still narrow the lookup.
        assert infer_account("What is the deal status for Globex?", []) == "Globex"

    def test_infer_account_ignores_sentence_initial_question_words(self) -> None:
        assert infer_account("What is the deal status?", []) is None

    @pytest.mark.parametrize("q", ["what failed?", "show me the error", "the job broke"])
    def test_wants_failure_detects_failure_questions(self, q: str) -> None:
        assert wants_failure(q) is True

    def test_wants_failure_is_false_for_a_neutral_question(self) -> None:
        assert wants_failure("did the pipeline run successfully?") is False


class TestDataAgent:
    async def test_returns_a_grounded_cited_answer(self, fake_llm: FakeLLM) -> None:
        fake_llm.responses[AgentResponse] = lambda _: answer(
            "sales_etl succeeded.", "Databricks Job #4821 (sales_etl) run #99141"
        )
        got = await DataAgent(fake_llm).answer("did the sales etl run?")
        assert got.citations == ["Databricks Job #4821 (sales_etl) run #99141"]

    async def test_failure_question_narrows_to_failed_runs(self, fake_llm: FakeLLM) -> None:
        runs, _ = await DataAgent(fake_llm).fetch_runs("what was the error in the last failed job?")
        assert runs and all(r["result_state"] == "FAILED" for r in runs)

    async def test_the_error_message_reaches_the_prompt(self, fake_llm: FakeLLM) -> None:
        fake_llm.responses[AgentResponse] = answer("failed", "x")
        await DataAgent(fake_llm).answer("what was the error in the last failed Databricks job?")
        assert "SchemaMismatchException" in fake_llm.calls[0]["user"]

    async def test_a_fabricated_citation_is_stripped(self, fake_llm: FakeLLM) -> None:
        fake_llm.responses[AgentResponse] = answer("ok", "Databricks Job #9999 (invented) run #1")
        got = await DataAgent(fake_llm).answer("did the sales etl run?")
        assert "9999" not in got.citations[0]

    async def test_llm_failure_degrades_to_raw_facts_never_fabrication(
        self, fake_llm: FakeLLM
    ) -> None:
        fake_llm.responses[AgentResponse] = LLMError("model down")
        got = await DataAgent(fake_llm).answer("did the sales etl run?")
        assert got.confidence == "low"
        assert got.citations  # still grounded
        assert "sales_etl" in got.answer

    async def test_uses_the_complex_model(self, fake_llm: FakeLLM) -> None:
        fake_llm.responses[AgentResponse] = answer("a", "x")
        await DataAgent(fake_llm).answer("did the sales etl run?")
        assert fake_llm.complexity_for("AgentResponse") == Complexity.COMPLEX

    async def test_prompt_scaffolding_never_reaches_the_caller(self, fake_llm: FakeLLM) -> None:
        # gemma3:4b really did this on test query 2: it answered, then recited the tail of
        # its own prompt into the answer. The corrupted answer defeated the grounding judge.
        fake_llm.responses[AgentResponse] = answer(
            "The last failed job was run #99163. "
            "Citation strings you may use, verbatim: - Databricks Job #4830",
            "Databricks Job #4830 (crm_sync) run #99163",
        )
        got = await DataAgent(fake_llm).answer("what was the error in the last failed job?")
        assert "Citation strings you may use" not in got.answer
        assert "The last failed job was run #99163." in got.answer

    async def test_record_count_is_capped_by_config(
        self, fake_llm: FakeLLM, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("MAX_RECORDS_IN_PROMPT", "1")
        reset_settings()
        runs, citations = await DataAgent(fake_llm).fetch_runs("show me all runs")
        assert len(runs) == 1 and len(citations) == 1


class TestDevOpsAgent:
    async def test_explains_failing_gates(self, fake_llm: FakeLLM) -> None:
        fake_llm.responses[AgentResponse] = answer("coverage failed", "x")
        await DevOpsAgent(fake_llm).answer("did the ingestion deployment pass?")
        prompt = fake_llm.calls[0]["user"]
        assert "failing_gates" in prompt and "code-coverage" in prompt

    async def test_clean_run_has_no_failing_gates_in_the_prompt(self, fake_llm: FakeLLM) -> None:
        fake_llm.responses[AgentResponse] = answer("all passed", "x")
        await DevOpsAgent(fake_llm).answer("did the payments deployment pass all quality gates?")
        assert '"failing_gates": []' in fake_llm.calls[0]["user"]

    async def test_degrades_to_gate_facts_when_the_llm_fails(self, fake_llm: FakeLLM) -> None:
        fake_llm.responses[AgentResponse] = LLMError("down")
        got = await DevOpsAgent(fake_llm).answer("did the ingestion deployment pass?")
        assert "code-coverage" in got.answer and got.confidence == "low"

    async def test_clean_run_degradation_says_passed(self, fake_llm: FakeLLM) -> None:
        fake_llm.responses[AgentResponse] = LLMError("down")
        got = await DevOpsAgent(fake_llm).answer("did the payments deployment pass?")
        assert "passed all quality gates" in got.answer


class TestCRMAgent:
    async def test_answers_a_deal_question(self, fake_llm: FakeLLM) -> None:
        fake_llm.responses[AgentResponse] = answer(
            "Acme is in Negotiation.", "CRM deal DEAL-7781 (Acme Corp)"
        )
        got = await CRMAgent(fake_llm).answer("What is the deal status for Acme Corp?")
        assert "DEAL-7781" in got.citations[0]

    async def test_stale_record_uses_the_complex_model(self, fake_llm: FakeLLM) -> None:
        # Acme is flagged stale, so staleness reasoning is needed.
        fake_llm.responses[AgentResponse] = answer("a", "x")
        await CRMAgent(fake_llm).answer("deal status for Acme Corp?")
        assert fake_llm.complexity_for("AgentResponse") == Complexity.COMPLEX

    async def test_fresh_record_uses_the_simple_model(self, fake_llm: FakeLLM) -> None:
        # Northwind is current, so a plain field lookup is enough.
        fake_llm.responses[AgentResponse] = answer("a", "x")
        await CRMAgent(fake_llm).answer("deal status for Northwind Retail?")
        assert fake_llm.complexity_for("AgentResponse") == Complexity.SIMPLE

    async def test_sync_warning_reaches_the_prompt(self, fake_llm: FakeLLM) -> None:
        fake_llm.responses[AgentResponse] = answer("a", "x")
        await CRMAgent(fake_llm).answer("deal status for Acme Corp?")
        assert "stale" in fake_llm.calls[0]["user"]

    async def test_degrades_to_the_record_when_the_llm_fails(self, fake_llm: FakeLLM) -> None:
        fake_llm.responses[AgentResponse] = LLMError("down")
        got = await CRMAgent(fake_llm).answer("Who is the account owner for TechStart Ltd?")
        assert "Karthik Rao" in got.answer and got.confidence == "low"


class TestDocsAgent:
    async def test_answers_from_retrieved_chunks(
        self, fake_llm: FakeLLM, indexed_store: LocalVectorStore, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("RAG_MIN_SCORE", "0.0")
        reset_settings()
        fake_llm.responses[AgentResponse] = lambda user: answer(
            "Quarantine the partition.",
            *[line[2:] for line in user.splitlines() if line.startswith("- ")][:1],
        )
        got = await DocsAgent(fake_llm, indexed_store).answer("schema mismatch runbook")
        assert got.citations and "§" in got.citations[0]

    async def test_empty_index_declines_rather_than_inventing(self, fake_llm: FakeLLM) -> None:
        got = await DocsAgent(fake_llm, LocalVectorStore()).answer("anything")
        assert got.citations == []
        assert got.confidence == "low"
        assert "does not cover" in got.answer
        # The LLM must not even be consulted when there is nothing to ground on.
        assert fake_llm.calls == []

    async def test_llm_failure_falls_back_to_the_retrieved_text(
        self, fake_llm: FakeLLM, indexed_store: LocalVectorStore, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("RAG_MIN_SCORE", "0.0")
        reset_settings()
        fake_llm.responses[AgentResponse] = LLMError("down")
        got = await DocsAgent(fake_llm, indexed_store).answer("schema mismatch")
        assert got.answer and got.citations and got.confidence == "low"
