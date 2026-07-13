"""The evidence-page generator that feeds the mid-term Evidence Pack."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from psiog_kendra.config import reset_settings, settings
from psiog_kendra.qa.evidence import build_evidence, render_index, render_query
from psiog_kendra.qa.report import QAReport, QueryResult


def result(
    qid: int = 1,
    domains: list[str] | None = None,
    *,
    correct: bool = True,
    judged: bool = True,
) -> dict:
    domains = domains or ["data-platform"]
    r = QueryResult(
        id=qid,
        query="Did yesterday's ETL pipeline for the sales data run successfully?",
        expected_domains=domains,
        actual_domains=domains if correct else ["crm"],
        routed_correctly=correct,
        answer="The sales_etl job succeeded at 02:14 UTC.",
        citations=["Databricks Job #4821 (sales_etl) run #99141"],
        grounded_claim_texts=["The sales_etl job succeeded"] if judged else [],
        ungrounded_claims=[],
        judged=judged,
    )
    return QAReport([r]).to_dict()["results"][0]


class TestRenderQuery:
    def test_carries_the_question_routing_and_citations(self) -> None:
        page = render_query(result())
        assert "Did yesterday's ETL pipeline" in page
        assert "data-platform" in page
        assert "Databricks Job #4821" in page
        assert "PASS" in page

    def test_names_the_specialist_agent_that_answered(self) -> None:
        assert "`data-agent`" in render_query(result())

    def test_tells_the_reader_how_to_screenshot_it(self) -> None:
        page = render_query(result())
        assert "How to take the screenshot" in page
        assert "make ask" in page
        assert "whole terminal window" in page
        # It must warn against screenshotting a degraded fallback run.
        assert "Do not screenshot a fallback run" in page

    def test_lists_the_grounded_claims_the_judge_found(self) -> None:
        page = render_query(result())
        assert "The sales_etl job succeeded" in page
        assert "No ungrounded claims" in page

    def test_an_unverified_answer_is_marked_not_passed_off_as_clean(self) -> None:
        # The bug this guards: a judge that enumerated nothing must not produce an evidence
        # page that reads like a clean 0%-hallucination result.
        page = render_query(result(judged=False))
        assert "UNVERIFIED" in page
        assert "NOT as a clean pass" in page

    def test_cross_domain_page_claims_cross_domain_synthesis(self) -> None:
        page = render_query(result(qid=9, domains=["data-platform", "crm"]))
        assert "Cross-Domain" in page
        assert "Cross-domain synthesis works" in page
        assert "D-07" in page

    def test_a_failed_route_is_reported_as_failed(self) -> None:
        page = render_query(result(correct=False))
        assert "FAIL" in page

    def test_maps_to_the_right_mid_term_deliverables(self) -> None:
        page = render_query(result(domains=["docs"]))
        assert "D-04" in page  # Week 7 — Docs agent + RAG
        assert "D-02" in page  # Week 5 — Coordinator routing


class TestRenderIndex:
    def test_shows_the_two_graded_numbers(self) -> None:
        report = QAReport([QueryResult(**{**_qr(), "routed_correctly": True})]).to_dict()
        index = render_index(report)
        assert "Routing accuracy" in index
        assert "Hallucination rate" in index

    def test_lists_queries_not_yet_run(self) -> None:
        report = QAReport([QueryResult(**_qr())]).to_dict()
        # Only 1 of 12 ran, so the rest must be visibly pending, not silently omitted.
        assert "_not yet run_" in render_index(report)

    def test_warns_when_answers_were_not_judged(self) -> None:
        report = QAReport([QueryResult(**{**_qr(), "judged": False})]).to_dict()
        assert "not verified by the Judge Agent" in render_index(report)


def _qr() -> dict:
    return {
        "id": 1,
        "query": "q",
        "expected_domains": ["data-platform"],
        "actual_domains": ["data-platform"],
        "routed_correctly": True,
        "answer": "a",
        "citations": ["Databricks Job #4821"],
        "grounded_claim_texts": ["c"],
        "ungrounded_claims": [],
        "judged": True,
    }


class TestBuildEvidence:
    def test_writes_one_page_per_query_plus_an_index(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        report_path = tmp_path / "qa_report.json"
        report_path.write_text(json.dumps(QAReport([QueryResult(**_qr())]).to_dict()))

        monkeypatch.setenv("QA_REPORT_PATH", str(report_path))
        monkeypatch.setenv("EVIDENCE_DIR", str(tmp_path / "qa"))
        reset_settings()

        count, written = build_evidence()
        assert count == 2
        assert "q01.md" in written and "README.md" in written
        assert (settings().evidence_dir / "q01.md").exists()

    def test_a_page_from_a_superseded_run_is_deleted(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # The bug this guards: q04.md survived from a run whose judge was later found to be
        # scoring citation labels as hallucinations. The report was regenerated with only
        # q01 in it, and the stale q04 page — carrying 16.67% from superseded code — stayed
        # in docs/qa/ and got committed. A stale page is worse than a missing one: it reads
        # as current evidence and gets pasted into the submission.
        out_dir = tmp_path / "qa"
        out_dir.mkdir()
        stale = out_dir / "q04.md"
        stale.write_text("# Q04 — stale numbers from a superseded run")

        report_path = tmp_path / "qa_report.json"
        report_path.write_text(json.dumps(QAReport([QueryResult(**_qr())]).to_dict()))
        monkeypatch.setenv("QA_REPORT_PATH", str(report_path))
        monkeypatch.setenv("EVIDENCE_DIR", str(out_dir))
        reset_settings()

        _, written = build_evidence()
        assert not stale.exists()
        assert "q04.md" not in written
        assert (out_dir / "q01.md").exists()

    def test_the_index_is_not_deleted_as_stale(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        report_path = tmp_path / "qa_report.json"
        report_path.write_text(json.dumps(QAReport([QueryResult(**_qr())]).to_dict()))
        monkeypatch.setenv("QA_REPORT_PATH", str(report_path))
        monkeypatch.setenv("EVIDENCE_DIR", str(tmp_path / "qa"))
        reset_settings()

        build_evidence()
        assert (settings().evidence_dir / "README.md").exists()

    def test_missing_report_is_a_clear_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("QA_REPORT_PATH", "/nonexistent/qa_report.json")
        reset_settings()
        with pytest.raises(SystemExit, match="run `make qa` first"):
            build_evidence()
