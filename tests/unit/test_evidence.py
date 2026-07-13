"""The evidence-page generator that feeds the mid-term Evidence Pack."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from psiog_kendra.config import reset_settings, settings
from psiog_kendra.qa.evidence import (
    ARTEFACTS,
    build_evidence,
    evidence_id,
    evidence_rows,
    render_artefact,
    render_index,
    render_query,
)
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
        # One page per query that ran, plus one per artefact, plus the index.
        assert count == 1 + len(ARTEFACTS) + 1
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


class TestEvidenceIds:
    """Section 3 requires every Done/Partial deliverable to point at an Evidence ID, and the
    evaluator cross-checks that link. A page with no ID cannot support a claim."""

    def test_a_query_page_carries_its_evidence_id(self) -> None:
        page = render_query(result(qid=7))
        assert "E-07" in page

    def test_the_evidence_id_is_in_the_pasteable_header_table(self) -> None:
        page = render_query(result(qid=3))
        assert "| Evidence ID | E-03 |" in page

    def test_ids_are_zero_padded_and_sequential(self) -> None:
        assert evidence_id(1) == "E-01"
        assert evidence_id(12) == "E-12"
        assert evidence_id(16) == "E-16"


class TestArtefactPages:
    """The 12 queries prove the agents route and cite. They cannot prove the suite passes,
    what coverage is, that the index built, or that the control plane runs — and Sections 3
    and 6 ask for all four. Without these, D-01 and D-08 go in unevidenced."""

    def test_every_artefact_names_a_deliverable_and_a_command(self) -> None:
        for artefact in ARTEFACTS:
            assert artefact.deliverable.startswith("D-")
            assert artefact.command
            assert artefact.look_for

    def test_the_artefacts_cover_the_deliverables_no_query_can(self) -> None:
        covered = {a.deliverable.split(" ")[0] for a in ARTEFACTS}
        # D-01 (control plane) and D-08 (tests/coverage) are provable ONLY by an artefact:
        # no test query touches either.
        assert {"D-01", "D-08"} <= covered

    def test_an_artefact_page_carries_its_evidence_id_and_screenshot_steps(self) -> None:
        page = render_artefact(ARTEFACTS[0], 13)
        assert "E-13" in page
        assert "📸" in page
        assert ARTEFACTS[0].command in page

    def test_the_control_plane_page_says_d01_is_partial(self) -> None:
        control = next(a for a in ARTEFACTS if a.deliverable.startswith("D-01"))
        page = render_artefact(control, 16)
        # Claiming D-01 Done would fail the evaluator's consistency check: OpenRouter is not
        # provisioned. The page must say so rather than let it be claimed.
        assert "Partial" in page
        assert "OpenRouter" in page

    def test_the_index_lists_every_artefact(self) -> None:
        report = QAReport([QueryResult(**_qr())]).to_dict()
        index = render_index(report)
        for artefact in ARTEFACTS:
            assert artefact.caption in index

    def test_the_index_emits_a_section_4_1_table(self) -> None:
        report = QAReport([QueryResult(**_qr())]).to_dict()
        index = render_index(report)
        assert "Section 4.1" in index
        assert "| Evidence ID | Caption (what it proves) | Deliverable ID |" in index
        assert "| E-01 |" in index

    def test_the_index_only_lists_evidence_that_exists(self) -> None:
        # A row for a query that has not run would be a claim with no page behind it.
        report = QAReport([QueryResult(**_qr())]).to_dict()  # only Q1
        rows = evidence_rows(report)
        ids = [r[0] for r in rows]
        assert "E-01" in ids
        assert "E-02" not in ids  # Q2 has not run
        assert "E-13" in ids  # artefacts are always available to capture


class TestBuildEvidenceArtefacts:
    def test_artefact_pages_are_written_alongside_the_queries(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        report_path = tmp_path / "qa_report.json"
        report_path.write_text(json.dumps(QAReport([QueryResult(**_qr())]).to_dict()))
        monkeypatch.setenv("QA_REPORT_PATH", str(report_path))
        monkeypatch.setenv("EVIDENCE_DIR", str(tmp_path / "qa"))
        reset_settings()

        _, written = build_evidence()
        assert "q01.md" in written
        assert "e-13-qa-summary.md" in written
        assert "e-16-control-plane.md" in written

    def test_a_stale_artefact_page_is_deleted_too(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        out_dir = tmp_path / "qa"
        out_dir.mkdir()
        stale = out_dir / "e-99-removed-artefact.md"
        stale.write_text("# an artefact that no longer exists")

        report_path = tmp_path / "qa_report.json"
        report_path.write_text(json.dumps(QAReport([QueryResult(**_qr())]).to_dict()))
        monkeypatch.setenv("QA_REPORT_PATH", str(report_path))
        monkeypatch.setenv("EVIDENCE_DIR", str(out_dir))
        reset_settings()

        build_evidence()
        assert not stale.exists()
