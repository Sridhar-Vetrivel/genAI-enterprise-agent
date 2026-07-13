"""The Judge Agent and the QA report — the hallucination-rate machinery itself."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from psiog_kendra.config import reset_settings, settings
from psiog_kendra.llm import LLMError
from psiog_kendra.qa.judge import (
    JudgeAgent,
    claims_the_answer_actually_makes,
    load_raw_sources,
    strip_citation_echoes,
)
from psiog_kendra.qa.report import (
    QAReport,
    QueryResult,
    evaluate_query,
    load_previous_results,
    rejudge,
    render,
    run_qa,
)
from psiog_kendra.qa.test_queries import TEST_QUERIES, by_id
from psiog_kendra.schemas import (
    AgentResponse,
    CopilotResponse,
    JudgeVerdict,
    RoutingDecision,
    SynthesisResult,
)
from tests.conftest import FakeLLM, routing

# The judge now checks that a "claim" is even about what the answer discusses, so both the
# answer and the claims in these fixtures have to be real sentences. Single letters used to
# do; they no longer can, and that is the point of the check.
ANSWER = "The sales_etl pipeline succeeded at 02:14 UTC and wrote 1284502 records."
CLAIMS = [
    "The sales_etl pipeline succeeded",
    "It ran at 02:14 UTC",
    "It wrote 1284502 records",
]


def response(answer: str = ANSWER, citations: list[str] | None = None) -> CopilotResponse:
    # `is None`, not `or`: an explicitly empty citation list is the case under test.
    cited = ["Databricks Job #4821"] if citations is None else citations
    return CopilotResponse(answer=answer, citations=cited, domains_used=["data-platform"])


class TestLoadRawSources:
    def test_carries_every_system_the_copilot_can_cite(self) -> None:
        raw = load_raw_sources()
        assert {"databricks", "devops", "crm", "documentation"} <= set(raw)
        assert raw["documentation"]


AUTH_CITE = "GitHub Actions run #5498 (deploy-auth, commit 7de2b10)"


class TestStripCitationEchoes:
    def test_drops_a_citation_parroted_back_as_a_claim(self) -> None:
        claims = ["The last deployment was 2026-07-09T11:05:00Z", AUTH_CITE]
        assert strip_citation_echoes(claims, [AUTH_CITE]) == [
            "The last deployment was 2026-07-09T11:05:00Z"
        ]

    def test_punctuation_and_hashes_cannot_hide_the_echo(self) -> None:
        assert (
            strip_citation_echoes(
                ["GitHub Actions run 5498 deploy-auth commit 7de2b10"], [AUTH_CITE]
            )
            == []
        )

    def test_a_real_claim_naming_its_record_is_kept(self) -> None:
        # The match is exact-after-normalisation on purpose. A substring rule would eat this
        # — a genuine, checkable assertion that happens to name the record it came from.
        claim = "The job failed on Databricks Job #4822 (ingestion_raw_events) run #99150"
        cites = ["Databricks Job #4822 (ingestion_raw_events) run #99150"]
        assert strip_citation_echoes([claim], cites) == [claim]

    def test_blank_claims_are_dropped(self) -> None:
        assert strip_citation_echoes(["", "   "], [AUTH_CITE]) == []

    def test_nothing_to_strip_leaves_the_claims_alone(self) -> None:
        claims = ["The pipeline succeeded", "It wrote 1284502 rows"]
        assert strip_citation_echoes(claims, [AUTH_CITE]) == claims


# The real answer the copilot gave for QA query 4, and the real verdict the judge returned.
AUTH_ANSWER = (
    "The last deployment date for the auth service was 2026-07-09T11:05:00Z. All quality "
    "gates passed during this deployment, including unit tests, code coverage (83% against "
    "an 80% threshold), and the security scan which found no high/critical CVEs."
)


def auth_response() -> CopilotResponse:
    return CopilotResponse(answer=AUTH_ANSWER, citations=[AUTH_CITE], domains_used=["devops"])


class TestJudgeAgent:
    async def test_a_citation_echoed_as_a_claim_is_not_a_hallucination(
        self, fake_llm: FakeLLM
    ) -> None:
        # The real failure, from QA query 4. Every actual fact in the answer was confirmed
        # grounded; the judge then listed the CITATION STRING as a sixth claim and marked it
        # ungrounded — scoring a perfectly grounded answer at 16.67%. A citation says where
        # the answer came from; it is not something the answer asserts.
        fake_llm.responses[JudgeVerdict] = JudgeVerdict(
            grounded_claims=[
                "The last deployment date for the auth service was 2026-07-09T11:05:00Z",
                "All quality gates passed during this deployment",
                "Code coverage was 83% against an 80% threshold",
            ],
            ungrounded_claims=[AUTH_CITE],
        )
        verdict = await JudgeAgent(fake_llm).verify(auth_response())
        assert verdict.ungrounded_claims == []
        assert verdict.total_claims == 3
        assert verdict.hallucination_rate == 0.0

    async def test_an_echo_scored_grounded_does_not_pad_the_denominator(
        self, fake_llm: FakeLLM
    ) -> None:
        # The same echo landed in grounded_claims on query 3 — inflating the denominator and
        # quietly making the hallucination rate look better than it is. Both directions go.
        fake_llm.responses[JudgeVerdict] = JudgeVerdict(
            grounded_claims=["All quality gates passed during this deployment", AUTH_CITE],
            ungrounded_claims=["Code coverage was 83% against an 80% threshold"],
        )
        verdict = await JudgeAgent(fake_llm).verify(auth_response())
        assert verdict.total_claims == 2
        assert verdict.hallucination_rate == 50.0

    async def test_an_answer_that_is_only_a_citation_echo_is_unverified_not_clean(
        self, fake_llm: FakeLLM
    ) -> None:
        # If scrubbing the echoes leaves nothing, the judge enumerated nothing real. That
        # must not certify the answer as 0% — it is UNVERIFIED, which counts against us.
        fake_llm.responses[JudgeVerdict] = JudgeVerdict(grounded_claims=[AUTH_CITE])
        verdict = await JudgeAgent(fake_llm).verify(auth_response())
        assert verdict.hallucination_rate == 100.0
        assert "UNVERIFIED" in verdict.ungrounded_claims[0]

    async def test_source_fields_the_answer_never_mentioned_are_not_claims(
        self, fake_llm: FakeLLM
    ) -> None:
        # The real failure, from QA query 3. The judge stopped grading the answer and started
        # summarising the source: it listed the branch, the actor, the commit sha and the run
        # id — none of which the answer mentions. Each is trivially grounded (it copied them
        # out of the source it is grading against), so each pads the denominator with a free
        # pass and drags the hallucination rate DOWN. A metric that flatters us is the most
        # dangerous kind, because nobody goes looking for the bug.
        fake_llm.responses[JudgeVerdict] = JudgeVerdict(
            grounded_claims=[
                "The last deployment date for the auth service was 2026-07-09T11:05:00Z",
                "The branch is main",
                "The actor is priya.n",
                "The commit sha is a1f9c34",
                "The workflow run id is 5512",
            ],
        )
        verdict = await JudgeAgent(fake_llm).verify(auth_response())
        assert verdict.grounded_claims == [
            "The last deployment date for the auth service was 2026-07-09T11:05:00Z"
        ]
        assert verdict.total_claims == 1  # not 5

    async def test_a_claim_graded_both_ways_is_sent_back_to_the_judge(
        self, fake_llm: FakeLLM
    ) -> None:
        # The real failure, from QA query 3: "Yes, the latest deployment passed all quality
        # gates" (grounded) and "The latest deployment ... passed all quality gates"
        # (ungrounded) — the same assertion, filed under both verdicts at once. That single
        # contradiction WAS the reported hallucination rate for a wholly grounded answer.
        # A self-contradicting verdict says nothing about the answer; it says the judge
        # slipped. So it grades again rather than us scoring a coin-flip.
        contradictory = JudgeVerdict(
            grounded_claims=["Yes, all quality gates passed during this deployment"],
            ungrounded_claims=["All quality gates passed during this deployment"],
        )
        coherent = JudgeVerdict(grounded_claims=["All quality gates passed during this deployment"])
        replies = iter([contradictory, coherent])
        fake_llm.responses[JudgeVerdict] = lambda _: next(replies)

        verdict = await JudgeAgent(fake_llm).verify(auth_response())

        assert len(fake_llm.calls) == 2
        assert "BOTH grounded and ungrounded" in fake_llm.calls[1]["user"]
        assert verdict.hallucination_rate == 0.0
        assert verdict.ungrounded_claims == []

    async def test_a_claim_contradicted_twice_is_set_aside_not_scored(
        self, fake_llm: FakeLLM
    ) -> None:
        # If the judge contradicts itself twice on the same claim, it has not graded it.
        # Scoring it either way would be a thumb on the scale, so it is set aside and the
        # remaining claims are scored honestly.
        fake_llm.responses[JudgeVerdict] = JudgeVerdict(
            grounded_claims=[
                "Yes, all quality gates passed during this deployment",
                "The last deployment date for the auth service was 2026-07-09T11:05:00Z",
            ],
            ungrounded_claims=["All quality gates passed during this deployment"],
        )
        verdict = await JudgeAgent(fake_llm).verify(auth_response())

        assert len(fake_llm.calls) == 2  # it was given a second chance
        assert verdict.grounded_claims == [
            "The last deployment date for the auth service was 2026-07-09T11:05:00Z"
        ]
        assert verdict.ungrounded_claims == []
        assert verdict.hallucination_rate == 0.0

    async def test_reports_a_clean_answer_as_grounded(self, fake_llm: FakeLLM) -> None:
        fake_llm.responses[JudgeVerdict] = JudgeVerdict(grounded_claims=CLAIMS)
        verdict = await JudgeAgent(fake_llm).verify(response())
        assert verdict.hallucination_rate == 0.0
        assert verdict.is_measured is True

    async def test_detects_ungrounded_claims(self, fake_llm: FakeLLM) -> None:
        fake_llm.responses[JudgeVerdict] = JudgeVerdict(
            grounded_claims=CLAIMS, ungrounded_claims=["The sales_etl pipeline ran at 09:00"]
        )
        verdict = await JudgeAgent(fake_llm).verify(response())
        assert verdict.hallucination_rate == 25.0
        assert verdict.ungrounded_claims == ["The sales_etl pipeline ran at 09:00"]

    async def test_an_uncited_answer_is_ungrounded_by_definition(self, fake_llm: FakeLLM) -> None:
        verdict = await JudgeAgent(fake_llm).verify(response(citations=[]))
        assert verdict.hallucination_rate == 100.0
        # No LLM call needed - an answer with no citation cannot be verified.
        assert fake_llm.calls == []

    async def test_an_empty_answer_has_no_claims(self, fake_llm: FakeLLM) -> None:
        verdict = await JudgeAgent(fake_llm).verify(response(answer="   "))
        assert verdict.total_claims == 0
        assert fake_llm.calls == []

    async def test_a_judge_that_enumerates_nothing_is_retried(self, fake_llm: FakeLLM) -> None:
        # The bug this guards: gemma3 returned zero claims for a substantive answer, which
        # scored as a perfect 0% hallucination without checking anything.
        replies = iter([JudgeVerdict(), JudgeVerdict(grounded_claims=CLAIMS[:2])])
        fake_llm.responses[JudgeVerdict] = lambda _: next(replies)

        verdict = await JudgeAgent(fake_llm).verify(response())
        assert verdict.total_claims == 2
        assert len(fake_llm.calls) == 2
        assert "no claims at all" in fake_llm.calls[1]["user"]

    async def test_a_judge_that_never_enumerates_marks_the_answer_unverified(
        self, fake_llm: FakeLLM
    ) -> None:
        # Both attempts come back empty. This must NOT read as 0% hallucination.
        fake_llm.responses[JudgeVerdict] = JudgeVerdict()

        verdict = await JudgeAgent(fake_llm).verify(response())
        assert verdict.hallucination_rate == 100.0
        assert "UNVERIFIED" in verdict.ungrounded_claims[0]

    async def test_a_broken_judge_does_not_certify_the_answer_as_clean(
        self, fake_llm: FakeLLM
    ) -> None:
        # A judge that cannot run must never silently report 0% hallucination.
        fake_llm.responses[JudgeVerdict] = LLMError("judge down")
        verdict = await JudgeAgent(fake_llm).verify(response())
        assert verdict.hallucination_rate == 100.0
        assert "UNVERIFIED" in verdict.ungrounded_claims[0]

    async def test_the_judge_grades_against_raw_sources_not_the_agent_context(
        self, fake_llm: FakeLLM
    ) -> None:
        fake_llm.responses[JudgeVerdict] = JudgeVerdict(grounded_claims=["a"])
        await JudgeAgent(fake_llm).verify(response())
        # The real Databricks fixture content must be in the judge's prompt.
        assert "99141" in fake_llm.calls[0]["user"]

    async def test_source_payload_is_capped(
        self, fake_llm: FakeLLM, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from psiog_kendra.config import reset_settings

        monkeypatch.setenv("QA_JUDGE_SOURCE_CHAR_LIMIT", "200")
        reset_settings()
        fake_llm.responses[JudgeVerdict] = JudgeVerdict(grounded_claims=["a"])
        await JudgeAgent(fake_llm).verify(response())
        assert len(fake_llm.calls[0]["user"]) < 1500


class TestQueryResult:
    def test_hallucination_rate_per_query(self) -> None:
        r = QueryResult(
            id=1,
            query="q",
            expected_domains=["crm"],
            actual_domains=["crm"],
            routed_correctly=True,
            answer="a",
            citations=["c"],
            grounded_claim_texts=["a", "b", "c", "d"],
            ungrounded_claims=["e"],
        )
        assert r.total_claims == 5
        assert r.grounded_claims == 4
        assert r.hallucination_rate == 20.0

    def test_no_claims_is_zero(self) -> None:
        r = QueryResult(
            id=1,
            query="q",
            expected_domains=[],
            actual_domains=[],
            routed_correctly=False,
            answer="",
            citations=[],
        )
        assert r.hallucination_rate == 0.0


class TestQAReport:
    def _result(self, qid: int, correct: bool, total: int = 4, grounded: int = 4) -> QueryResult:
        tq = by_id(qid)
        return QueryResult(
            id=qid,
            query=tq.query,
            expected_domains=sorted(tq.expected_domains),
            actual_domains=sorted(tq.expected_domains) if correct else ["crm"],
            routed_correctly=correct,
            answer="a",
            citations=["c"],
            grounded_claim_texts=[f"g{i}" for i in range(grounded)],
            ungrounded_claims=[f"u{i}" for i in range(total - grounded)],
            judged=total > 0,
        )

    def test_unjudged_answers_are_reported_not_hidden(self) -> None:
        judged = self._result(1, True)
        unjudged = self._result(2, True, total=0, grounded=0)
        report = QAReport([judged, unjudged])
        assert report.judged_answers == 1
        assert "not verified by the judge" in render(report)

    def test_routing_accuracy_is_pooled(self) -> None:
        report = QAReport([self._result(1, True), self._result(2, False)])
        assert report.routing_accuracy == 50.0

    def test_hallucination_rate_pools_claims_not_percentages(self) -> None:
        # 10 claims, 1 ungrounded overall => 10%, NOT the mean of the per-query rates.
        report = QAReport(
            [self._result(1, True, total=8, grounded=8), self._result(2, True, total=2, grounded=1)]
        )
        assert report.hallucination_rate == 10.0

    def test_counts_answers_carrying_citations(self) -> None:
        a = self._result(1, True)
        b = self._result(2, True)
        b.citations = []
        assert QAReport([a, b]).cited_answers == 1

    def test_empty_report_does_not_divide_by_zero(self) -> None:
        report = QAReport([])
        assert report.routing_accuracy == 0.0
        assert report.hallucination_rate == 0.0

    def test_to_dict_carries_the_graded_numbers(self) -> None:
        summary = QAReport([self._result(1, True)]).to_dict()["summary"]
        assert summary["routing_accuracy_pct"] == 100.0
        assert summary["queries"] == 1

    def test_render_is_printable(self) -> None:
        out = render(QAReport([self._result(1, True), self._result(9, False)]))
        assert "Routing accuracy" in out and "Hallucination rate" in out
        assert "PASS" in out and "FAIL" in out


class TestEvaluateQuery:
    async def test_records_a_correct_route(self, fake_llm: FakeLLM) -> None:
        from psiog_kendra.app import build_copilot

        tq = by_id(5)  # CRM
        fake_llm.responses[RoutingDecision] = routing("crm")
        fake_llm.responses[JudgeVerdict] = JudgeVerdict(grounded_claims=["a", "b"])
        from psiog_kendra.schemas import AgentResponse

        fake_llm.responses[AgentResponse] = AgentResponse(
            answer="Acme is in Negotiation.", citations=["CRM deal DEAL-7781 (Acme Corp)"]
        )

        result = await evaluate_query(tq, build_copilot(llm=fake_llm), JudgeAgent(fake_llm))
        assert result.routed_correctly is True
        assert result.citations

    async def test_a_crashing_query_is_a_reported_failure_not_an_exception(
        self, fake_llm: FakeLLM
    ) -> None:
        from psiog_kendra.app import build_copilot

        fake_llm.responses[RoutingDecision] = LLMError("model down")
        result = await evaluate_query(by_id(1), build_copilot(llm=fake_llm), None)

        assert result.routed_correctly is False
        assert result.error is not None
        assert result.actual_domains == []

    async def test_must_mention_catches_a_grounded_but_wrong_answer(
        self, fake_llm: FakeLLM
    ) -> None:
        from psiog_kendra.app import build_copilot
        from psiog_kendra.schemas import AgentResponse

        tq = by_id(6)  # must mention "Karthik"
        fake_llm.responses[RoutingDecision] = routing("crm")
        fake_llm.responses[AgentResponse] = AgentResponse(
            answer="The owner is somebody else.", citations=["CRM account ACC-1002 (TechStart Ltd)"]
        )
        result = await evaluate_query(tq, build_copilot(llm=fake_llm), None)
        assert result.mentions_ok is False


class TestRunQA:
    async def test_runs_the_whole_suite_offline(
        self, fake_llm: FakeLLM, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from psiog_kendra.config import reset_settings
        from psiog_kendra.schemas import AgentResponse

        # FakeLLM's pseudo-embeddings do not reproduce nomic's score distribution, so the
        # docs agent would retrieve nothing and return an (honestly) uncited answer.
        monkeypatch.setenv("RAG_MIN_SCORE", "0.0")
        reset_settings()

        fake_llm.responses[RoutingDecision] = lambda user: RoutingDecision(
            # Route by the ground truth so the harness itself can be tested.
            domains=sorted(next(q.expected_domains for q in TEST_QUERIES if q.query in user))
        )
        fake_llm.responses[AgentResponse] = AgentResponse(
            answer=ANSWER, citations=["Databricks Job #4821"]
        )
        fake_llm.responses[SynthesisResult] = SynthesisResult(
            answer=ANSWER, citations=["Databricks Job #4821"]
        )
        fake_llm.responses[JudgeVerdict] = JudgeVerdict(grounded_claims=CLAIMS)

        report = await run_qa(llm=fake_llm)
        assert len(report.results) == 12
        assert report.routing_accuracy == 100.0
        assert report.hallucination_rate == 0.0


class TestResume:
    """Resume exists so a fix touching one query does not cost an hour of CPU re-running
    the other eleven. It is opt-in: see the warning in run_qa's docstring."""

    def _seed(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, ids: list[int]) -> None:
        rows = [
            QueryResult(
                id=i,
                query=by_id(i).query,
                expected_domains=list(by_id(i).expected_domains),
                actual_domains=list(by_id(i).expected_domains),
                routed_correctly=True,
                answer=ANSWER,
                citations=["Databricks Job #4821"],
                grounded_claim_texts=["a"],
                judged=True,
            )
            for i in ids
        ]
        path = tmp_path / "qa_report.json"
        path.write_text(json.dumps(QAReport(rows).to_dict()))
        monkeypatch.setenv("QA_REPORT_PATH", str(path))
        reset_settings()

    def test_completed_queries_are_read_back_off_disk(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        self._seed(tmp_path, monkeypatch, [1, 2])
        previous = load_previous_results()
        assert set(previous) == {1, 2}
        assert previous[1].answer == ANSWER

    async def test_resume_skips_completed_queries_and_runs_the_rest(
        self, fake_llm: FakeLLM, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        self._seed(tmp_path, monkeypatch, [1, 2])
        monkeypatch.setenv("RAG_MIN_SCORE", "0.0")
        reset_settings()
        fake_llm.responses[RoutingDecision] = lambda user: RoutingDecision(
            domains=sorted(next(q.expected_domains for q in TEST_QUERIES if q.query in user))
        )
        fake_llm.responses[AgentResponse] = AgentResponse(
            answer="fresh", citations=["Databricks Job #4821"]
        )
        fake_llm.responses[SynthesisResult] = SynthesisResult(
            answer="fresh", citations=["Databricks Job #4821"]
        )
        fake_llm.responses[JudgeVerdict] = JudgeVerdict(grounded_claims=["a"])

        report = await run_qa(llm=fake_llm, queries=TEST_QUERIES[:4], resume=True)

        assert [r.id for r in report.results] == [1, 2, 3, 4]
        # Q1 and Q2 came off disk untouched; Q3 and Q4 were actually run.
        assert report.results[0].answer == ANSWER
        assert report.results[2].answer == "fresh"

    async def test_without_resume_every_query_is_run_again(
        self, fake_llm: FakeLLM, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # The default must stay a clean run. A report whose rows were graded by different
        # code averages two different systems into one hallucination rate.
        self._seed(tmp_path, monkeypatch, [1, 2])
        monkeypatch.setenv("RAG_MIN_SCORE", "0.0")
        reset_settings()
        fake_llm.responses[RoutingDecision] = lambda user: RoutingDecision(
            domains=sorted(next(q.expected_domains for q in TEST_QUERIES if q.query in user))
        )
        fake_llm.responses[AgentResponse] = AgentResponse(
            answer="fresh", citations=["Databricks Job #4821"]
        )
        fake_llm.responses[JudgeVerdict] = JudgeVerdict(grounded_claims=["a"])

        report = await run_qa(llm=fake_llm, queries=TEST_QUERIES[:2])
        assert all(r.answer != ANSWER for r in report.results)

    async def test_rejudge_regrades_the_stored_answers_without_asking_them_again(
        self, fake_llm: FakeLLM, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Every judge bug so far changed how answers are SCORED, not how they are produced.
        # Re-running the copilot to pick one up reproduces answers we already have on disk,
        # verbatim, at five LLM calls a query. Re-judging is one.
        self._seed(tmp_path, monkeypatch, [1, 2, 3])
        fake_llm.responses[JudgeVerdict] = JudgeVerdict(
            grounded_claims=["The sales_etl pipeline succeeded"],
            ungrounded_claims=["It wrote 1284502 records"],
        )

        report = await rejudge(llm=fake_llm)

        assert len(report.results) == 3
        # The answers are untouched — only the verdicts are new.
        assert all(r.answer == ANSWER for r in report.results)
        assert report.hallucination_rate == 50.0
        # The copilot was never invoked: only the judge ran, once per stored answer.
        assert all(call["schema"] == "JudgeVerdict" for call in fake_llm.calls)
        assert len(fake_llm.calls) == 3

    async def test_rejudge_with_no_stored_answers_is_a_clear_error(
        self, fake_llm: FakeLLM, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("QA_REPORT_PATH", str(tmp_path / "absent.json"))
        reset_settings()
        with pytest.raises(SystemExit, match="no answers to re-judge"):
            await rejudge(llm=fake_llm)

    def test_a_corrupt_report_resumes_from_nothing_rather_than_crashing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        path = tmp_path / "qa_report.json"
        path.write_text("{ this is not json")
        monkeypatch.setenv("QA_REPORT_PATH", str(path))
        reset_settings()
        assert load_previous_results() == {}

    def test_no_report_yet_resumes_from_nothing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("QA_REPORT_PATH", str(tmp_path / "absent.json"))
        reset_settings()
        assert load_previous_results() == {}


class TestVerdictIsNeverThrownAway:
    """The real failure, from QA query 9. The judge's first attempt enumerated claims but
    contradicted itself on one; the retry came back empty; and a flawless four-source
    cross-domain answer was reported as 100% ungrounded. A verdict that graded nine claims
    out of ten is worth strictly more than no verdict at all."""

    async def test_a_measured_first_verdict_survives_an_empty_retry(
        self, fake_llm: FakeLLM
    ) -> None:
        contradictory = JudgeVerdict(
            grounded_claims=[
                "Yes, all quality gates passed during this deployment",
                "The last deployment date for the auth service was 2026-07-09T11:05:00Z",
                "Code coverage was 83% against an 80% threshold",
            ],
            ungrounded_claims=["All quality gates passed during this deployment"],
        )
        replies = iter([contradictory, JudgeVerdict()])  # the retry comes back empty
        fake_llm.responses[JudgeVerdict] = lambda _: next(replies)

        verdict = await JudgeAgent(fake_llm).verify(auth_response())

        assert len(fake_llm.calls) == 2
        assert verdict.is_measured is True
        assert verdict.hallucination_rate == 0.0
        # The two claims it graded coherently survive; the disputed one is set aside.
        assert verdict.total_claims == 2
        assert "UNVERIFIED" not in " ".join(verdict.ungrounded_claims)

    async def test_a_measured_first_verdict_survives_a_judge_crash_on_retry(
        self, fake_llm: FakeLLM
    ) -> None:
        contradictory = JudgeVerdict(
            grounded_claims=[
                "Yes, all quality gates passed during this deployment",
                "Code coverage was 83% against an 80% threshold",
            ],
            ungrounded_claims=["All quality gates passed during this deployment"],
        )
        replies = iter([contradictory, LLMError("judge died")])

        def next_reply(_):
            r = next(replies)
            if isinstance(r, Exception):
                raise r
            return r

        fake_llm.responses[JudgeVerdict] = next_reply

        verdict = await JudgeAgent(fake_llm).verify(auth_response())
        assert verdict.is_measured is True
        assert verdict.total_claims == 1
        assert verdict.hallucination_rate == 0.0

    async def test_a_judge_that_enumerates_nothing_twice_is_still_unverified(
        self, fake_llm: FakeLLM
    ) -> None:
        # Nothing was ever graded, so there is no verdict to keep. This must NOT read as 0%.
        fake_llm.responses[JudgeVerdict] = JudgeVerdict()
        verdict = await JudgeAgent(fake_llm).verify(auth_response())
        assert verdict.hallucination_rate == 100.0
        assert "UNVERIFIED" in verdict.ungrounded_claims[0]
        assert len(fake_llm.calls) == 2  # it was pushed once before giving up


class TestQueryTimeout:
    """A cross-domain query is 5-7 sequential LLM calls, and on local CPU inference it can
    run past 15 minutes. Without a hard stop, one stalled query hangs the whole suite."""

    async def test_a_stalled_query_is_recorded_as_timed_out_not_skipped(
        self, fake_llm: FakeLLM, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("QA_QUERY_TIMEOUT_SECONDS", "0.05")
        reset_settings()

        class Stalled:
            async def ask(self, query: str):
                await asyncio.sleep(10)  # never returns in time

        result = await evaluate_query(by_id(9), Stalled(), None)

        # Recorded, with the reason — a missing result and a failed one must not look alike.
        assert result.id == 9
        assert result.routed_correctly is False
        assert result.error is not None
        assert result.error.startswith("TIMED OUT")

    async def test_the_timeout_message_names_the_cause_and_the_fix(
        self, fake_llm: FakeLLM, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Whoever reads this report must not mistake a deployment constraint for a design
        # flaw. The message has to say why it was slow and what makes it fast.
        monkeypatch.setenv("QA_QUERY_TIMEOUT_SECONDS", "0.05")
        reset_settings()

        class Stalled:
            async def ask(self, query: str):
                await asyncio.sleep(10)

        result = await evaluate_query(by_id(9), Stalled(), None)
        assert "local CPU inference" in result.error
        assert "OpenRouter is not provisioned" in result.error
        assert "AI_MODEL_COMPLEX" in result.error

    async def test_a_fast_query_is_unaffected_by_the_timeout(
        self, fake_llm: FakeLLM, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("QA_QUERY_TIMEOUT_SECONDS", "30")
        monkeypatch.setenv("RAG_MIN_SCORE", "0.0")
        reset_settings()
        fake_llm.responses[RoutingDecision] = RoutingDecision(domains=["data-platform"])
        fake_llm.responses[AgentResponse] = AgentResponse(
            answer=ANSWER, citations=["Databricks Job #4821"]
        )
        from psiog_kendra.app import build_copilot

        result = await evaluate_query(by_id(1), build_copilot(llm=fake_llm), None)
        assert result.error is None
        assert result.routed_correctly is True

    async def test_zero_disables_the_limit(
        self, fake_llm: FakeLLM, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("QA_QUERY_TIMEOUT_SECONDS", "0")
        reset_settings()
        assert settings().query_timeout_seconds == 0.0

        class Slow:
            async def ask(self, query: str):
                await asyncio.sleep(0.01)
                return CopilotResponse(
                    answer=ANSWER,
                    citations=["Databricks Job #4821"],
                    domains_used=["data-platform"],
                )

        result = await evaluate_query(by_id(1), Slow(), None)
        assert result.error is None  # no timeout applied


class TestPhantomClaims:
    """From QA query 10. The answer was flawless — it joined the live failure to the
    runbook's fix and cited all three sources — and the judge scored it 53.85% by inventing
    seven claims it had read out of the source."""

    Q10_ANSWER = (
        "The ingestion job `ingestion_raw_events` (run #99150) failed on 2026-07-12 due to a "
        "`SchemaMismatchException`. To resolve this, quarantine the offending file and then "
        "re-run Databricks Job #4822. Following this, manually re-run job 4830 (`crm_sync`)."
    )

    async def test_an_id_the_answer_never_uttered_is_not_a_claim(self, fake_llm: FakeLLM) -> None:
        # "The job id is 4821" — the answer mentions 4822 and 4830, never 4821. Word overlap
        # alone passed it ("job" matched, so it scored exactly 0.5 and squeaked through). An
        # id cannot be paraphrased: if the answer does not say 4821, it did not claim 4821.
        fake_llm.responses[JudgeVerdict] = JudgeVerdict(
            grounded_claims=["The ingestion job (run #99150) failed"],
            ungrounded_claims=[
                "The job id is 4821",
                "The run id is 99141",
                "The run id is 99102",
            ],
        )
        response = CopilotResponse(
            answer=self.Q10_ANSWER,
            citations=["Databricks Job #4822 (ingestion_raw_events) run #99150"],
            domains_used=["data-platform", "docs"],
        )
        verdict = await JudgeAgent(fake_llm).verify(response)
        assert verdict.ungrounded_claims == []
        assert verdict.hallucination_rate == 0.0

    def test_a_field_restatement_is_not_a_claim_even_when_the_id_is_in_the_answer(
        self,
    ) -> None:
        # "The job id is 4822" is a row of the record, not an assertion. The substantive
        # claim about that job is enumerated separately and still graded.
        kept = claims_the_answer_actually_makes(
            ["The job id is 4822", "Then re-run Databricks Job #4822"], self.Q10_ANSWER
        )
        assert kept == ["Then re-run Databricks Job #4822"]

    @pytest.mark.parametrize(
        "field_claim",
        [
            "The job id is 4822",
            "The run id is 99150",
            "The branch is main",
            "The actor is priya.n",
            "The commit sha is a1f9c34",
            "The result state is FAILED",
        ],
    )
    def test_every_field_restatement_shape_is_dropped(self, field_claim: str) -> None:
        assert claims_the_answer_actually_makes([field_claim], self.Q10_ANSWER) == []

    def test_a_real_hallucination_is_still_caught(self) -> None:
        # The property that matters: none of this may hide a fabricated fact. A hallucination
        # is something the ANSWER asserted, so it is built from the answer's own words and
        # its own identifiers — it passes every filter and is still graded.
        answer = "The sales_etl job succeeded and wrote 9999999 records at 02:14 UTC."
        claims = ["The job wrote 9999999 records", "The sales_etl job succeeded"]
        assert claims_the_answer_actually_makes(claims, answer) == claims

    def test_a_fabricated_id_the_answer_did_assert_is_still_graded(self) -> None:
        # If the answer really does invent a run, the substantive claim carrying it survives.
        answer = "Job #9999 failed with a schema mismatch."
        claims = ["Job #9999 failed with a schema mismatch"]
        assert claims_the_answer_actually_makes(claims, answer) == claims

    def test_a_real_claim_quoting_a_file_path_survives(self) -> None:
        claims = ["The source file is `s3://psiog-raw/events/2026-07-12/part-0007.parquet`"]
        answer = "It failed on `s3://psiog-raw/events/2026-07-12/part-0007.parquet`."
        assert claims_the_answer_actually_makes(claims, answer) == claims
